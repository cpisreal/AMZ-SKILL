#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
targeting-cr-forecast :: 滑动窗口转化率预测
==========================================
输入: Amazon Ads Sponsored Products targeting report (日维度, xlsx/csv)
输出: 每个 Targeting 在"下一个 x 天滑动窗口"的预估转化率(CVR)

目标定义:
    cr_x(t) = sum(orders, t-x+1..t) / sum(clicks, t-x+1..t)     # 窗口无点击时未定义(NaN)
    用 cr_x(t-1) ... cr_x(t-K) 预测 cr_x(t+1)

设计原则(来自实测结论, 不要随意改动):
  * 缺失日期补 0: 无记录 = 当天无投放 = 0 点击/0 订单; 不做插值, 不跳过
  * 允许 lag 缺口: 窗口无点击时 cr 为 NaN, GBDT 原生处理; 强制连续会丢掉大量样本
  * 默认只用 lag 特征: 实测加成交量/星期/匹配类型等上下文特征会变差
  * 强制 persistence 基线: 相邻窗口重叠 (x-1)/x, 基线 R2 天然很高
  * 时间切分验证, 绝不随机切分
  * 模型打不过基线时, 推荐列自动退回 persistence
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import warnings

warnings.filterwarnings("ignore")

try:
    import numpy as np
    import pandas as pd
except ImportError as e:  # pragma: no cover
    print(f"[FATAL] 缺少基础依赖: {e}\n请使用已安装 pandas/numpy 的 Python 解释器。", file=sys.stderr)
    raise SystemExit(3)

VERSION = "1.0.1"

# ---------------------------------------------------------------------------
# 列名模糊识别 (兼容不同导出语言/版本)
# ---------------------------------------------------------------------------
COL_PATTERNS = {
    "date":        [r"^date$", r"^day$", r"^日期$"],
    "campaign":    [r"^campaignname$", r"^campaign$", r"^广告活动名称$"],
    "adgroup":     [r"^adgroupname$", r"^adgroup$", r"^广告组名称$"],
    "targeting":   [r"^targeting$", r"^targetingexpression$", r"^keyword$", r"^keywordtext$", r"^投放$", r"^关键词$"],
    "match_type":  [r"^matchtype$", r"^match$", r"^匹配类型$"],
    "clicks":      [r"^clicks$", r"^点击量$", r"^点击$"],
    "orders":      [r"^(\d+)?daytotalorders", r"^totalorders", r"^orders$", r"^purchases$",
                    r"^conversions$", r"^(\d+)?天总订单", r"^订单$"],
    "impressions": [r"^impressions$", r"^曝光量$"],
    "spend":       [r"^spend$", r"^cost$", r"^花费$", r"^支出$"],
    "sales":       [r"^(\d+)?daytotalsales", r"^totalsales", r"^sales$", r"^销售额$"],
}

def norm(s) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", str(s).lower())

def attribution_days(colname) -> int:
    """从 '7 Day Total Orders' 里取出归因窗口天数; 取不到给一个大数"""
    m = re.search(r"(\d+)\s*day", str(colname), re.I)
    return int(m.group(1)) if m else 999

def resolve_columns(columns, overrides=None):
    """把真实列名映射到逻辑名。多重命中时, 订单/销售额优先取归因窗口更短(更完整)的那列。"""
    overrides = overrides or {}
    normed = {norm(c): c for c in columns}
    found, used = {}, set()
    for logical, pats in COL_PATTERNS.items():
        if overrides.get(logical):
            if overrides[logical] not in columns:
                raise SystemExit(f"[FATAL] 指定的列不存在: {overrides[logical]}")
            found[logical] = overrides[logical]
            used.add(overrides[logical])
            continue
        hits = [real for n, real in normed.items() if any(re.match(p, n) for p in pats)]
        if not hits:
            continue
        if logical in ("orders", "sales"):
            hits.sort(key=attribution_days)
        else:
            hits.sort(key=len)
        found[logical] = hits[0]
        used.add(hits[0])
    return found, used


# ---------------------------------------------------------------------------
# 读取
# ---------------------------------------------------------------------------
def read_table(path, sheet=None, nrows=None):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".csv", ".txt", ".tsv"):
        sep = "\t" if ext == ".tsv" else ","
        last = None
        for enc in ("utf-8-sig", "utf-8", "gbk", "latin-1"):
            try:
                return pd.read_csv(path, sep=sep, encoding=enc, nrows=nrows)
            except UnicodeDecodeError as e:
                last = e
        raise SystemExit(f"[FATAL] 无法解码 CSV: {last}")
    if ext in (".xls", ".xlsb"):
        raise SystemExit(f"[FATAL] 不支持 {ext}。请导出为 .xlsx 或 .csv 后重试。")
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        raise SystemExit("[FATAL] 读取 xlsx 需要 openpyxl: pip install openpyxl")
    if sheet is not None:
        return pd.read_excel(path, sheet_name=sheet, nrows=nrows)
    # 未指定 sheet: 选第一个含所需列的
    xl = pd.ExcelFile(path)
    best = None
    for name in xl.sheet_names:
        head = xl.parse(name, nrows=5)
        cols, _ = resolve_columns(list(head.columns))
        score = sum(k in cols for k in ("date", "clicks", "orders"))
        if score == 3:
            best = name
            break
        if best is None and score >= 2:
            best = name
    if best is None:
        best = xl.sheet_names[0]
    return xl.parse(best, nrows=nrows)


# ---------------------------------------------------------------------------
# 面板与特征
# ---------------------------------------------------------------------------
def build_panel(df, cols, level, window):
    """返回 (cr, clicks_roll, orders_roll, days, meta) — 均为 rows=Date, cols=key"""
    keycols = {"campaign": [cols.get("campaign")],
               "adgroup":  [cols.get("campaign"), cols.get("adgroup")],
               "targeting": [cols.get("campaign"), cols.get("adgroup"), cols.get("targeting"), cols.get("match_type")]}[level]
    if any(c is None for c in keycols):
        raise SystemExit(f"[FATAL] --key-level {level} 需要这些列, 但报表里缺失: "
                         f"{[c for c in keycols if c is None]}。已识别: {cols}")
    d = df.copy()
    d["__key__"] = d[keycols].astype(str).agg("||".join, axis=1)
    d["__date__"] = pd.to_datetime(d[cols["date"]], errors="coerce")
    bad = int(d["__date__"].isna().sum())
    d = d[d["__date__"].notna()]
    if d.empty:
        raise SystemExit("[FATAL] 日期列全部无法解析。")

    for c, name in ((cols["clicks"], "clicks"), (cols["orders"], "orders")):
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0.0)

    meta = d.drop_duplicates("__key__").set_index("__key__")[keycols].copy()
    meta.columns = ["campaign", "adgroup", "targeting", "match_type"][: len(keycols)]

    days = pd.date_range(d["__date__"].min(), d["__date__"].max(), freq="D")
    def pivot(c):
        return (d.pivot_table(index="__date__", columns="__key__", values=c, aggfunc="sum")
                  .reindex(index=days).fillna(0.0))
    clicks, orders = pivot(cols["clicks"]), pivot(cols["orders"])
    c_roll = clicks.rolling(window, min_periods=window).sum()
    o_roll = orders.rolling(window, min_periods=window).sum()
    cr = o_roll.div(c_roll.where(c_roll > 0))

    # 同 key 口径的花费/销售额聚合, 用于覆盖率报告 (必须复用同一个 __key__)
    agg_map = {k: cols[k] for k in ("spend", "sales") if cols.get(k)}
    agg = None
    if agg_map:
        for c in agg_map.values():
            d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0.0)
        agg = d.groupby("__key__")[list(agg_map.values())].sum()
        agg.columns = list(agg_map.keys())
    return cr, c_roll, o_roll, days, meta, bad, agg


def build_samples(cr, K):
    """长表样本: y = cr(t), 特征 = cr(t-1..t-K)"""
    feats = {f"cr_lag{k}": cr.shift(k) for k in range(1, K + 1)}
    X = pd.DataFrame({n: f.stack(dropna=False) for n, f in feats.items()})
    X.index.names = ["Date", "key"]
    X["y"] = cr.stack(dropna=False)
    return X[X["y"].notna()].reset_index()


# ---------------------------------------------------------------------------
# 模型
# ---------------------------------------------------------------------------
def get_model(kind, seed=0):
    if kind in ("auto", "gbdt"):
        try:
            import lightgbm as lgb
            return ("lightgbm", lgb.LGBMRegressor(
                n_estimators=400, learning_rate=0.05, num_leaves=31, min_child_samples=30,
                subsample=0.8, subsample_freq=1, colsample_bytree=0.8, random_state=seed, verbose=-1))
        except ImportError:
            pass
        try:
            from sklearn.ensemble import HistGradientBoostingRegressor
            return ("histgb", HistGradientBoostingRegressor(
                max_iter=400, learning_rate=0.05, max_leaf_nodes=31, l2_regularization=1.0, random_state=seed))
        except ImportError:
            pass
        return ("ridge", None)          # numpy 兜底
    if kind == "persistence":
        return ("persistence", None)
    raise SystemExit(f"[FATAL] 未知 --model: {kind}")


class RidgeFallback:
    """无 sklearn/lightgbm 时的兜底: NaN 视为 0 (窗口无点击 = 无订单)。"""
    def __init__(self, alpha=1.0):
        self.alpha = alpha
    def fit(self, X, y):
        A = np.nan_to_num(np.asarray(X, float), nan=0.0)
        A = np.column_stack([np.ones(len(A)), A])
        n = A.shape[1]
        R = self.alpha * np.eye(n); R[0, 0] = 0
        self.w = np.linalg.solve(A.T @ A + R, A.T @ np.asarray(y, float))
        return self
    def predict(self, X):
        A = np.nan_to_num(np.asarray(X, float), nan=0.0)
        return np.column_stack([np.ones(len(A)), A]) @ self.w


def metrics(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    e = y - p
    ss = float(np.sum((y - y.mean()) ** 2))
    return dict(MAE=float(np.mean(np.abs(e))),
                RMSE=float(np.sqrt(np.mean(e ** 2))),
                R2=float(1 - np.sum(e ** 2) / ss) if ss > 0 else float("nan"))


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="滑动窗口转化率(CVR)预测 — Amazon Ads targeting report")
    ap.add_argument("input", nargs="?", help="报表路径 (.xlsx/.csv)")
    ap.add_argument("--window", "-w", type=int, default=7, help="滑动窗口天数 x (默认 7)")
    ap.add_argument("--lags", "-k", type=int, default=14, help="用过去多少个滚动值做特征 K (默认 14)")
    ap.add_argument("--horizon", type=int, default=1, help="向前预测几个窗口 (默认 1; >1 为递归预测, 误差会累积)")
    ap.add_argument("--key-level", choices=["targeting", "adgroup", "campaign"], default="targeting",
                    help="预测粒度 (默认 targeting = Campaign+AdGroup+Targeting+Match)")
    ap.add_argument("--min-valid", type=int, default=15, help="序列至少要有多少个可用窗口才建模 (默认 15)")
    ap.add_argument("--val-days", type=int, default=7, help="验证集天数 (默认最后 7 天)")
    ap.add_argument("--model", choices=["auto", "gbdt", "persistence"], default="auto")
    ap.add_argument("--features", choices=["lags", "lags+volume"], default="lags",
                    help="默认只用 lag (实测加成交量特征会变差)")
    ap.add_argument("--sheet", default=None, help="xlsx 的 sheet 名 (默认自动探测)")
    ap.add_argument("--date-col", default=None, help="手工指定日期列名 (自动识别失败时用)")
    ap.add_argument("--clicks-col", default=None, help="手工指定点击列名")
    ap.add_argument("--orders-col", default=None, help="手工指定订单列名 (多个归因窗口时默认取最短的那个)")
    ap.add_argument("--min-clicks-flag", type=int, default=5, help="上一窗口点击数低于此值标记 low_confidence")
    ap.add_argument("--out", "-o", default="cr_forecast_out", help="输出目录")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--check-env", action="store_true", help="只检查依赖后退出")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出摘要")
    a = ap.parse_args(argv)

    if a.check_env:
        avail = {}
        for m in ("pandas", "numpy", "openpyxl", "sklearn", "lightgbm", "prophet"):
            try:
                __import__(m); avail[m] = True
            except ImportError:
                avail[m] = False
        print(json.dumps({"python": sys.executable, "version": sys.version.split()[0],
                          "packages": avail}, indent=2, ensure_ascii=False))
        return 0
    if not a.input:
        ap.error("需要报表路径, 或用 --check-env")
    if not os.path.isfile(a.input):
        raise SystemExit(f"[FATAL] 文件不存在: {a.input}")

    os.makedirs(a.out, exist_ok=True)
    S = {"skill": "targeting-cr-forecast", "version": VERSION, "input": os.path.abspath(a.input),
         "window": a.window, "lags": a.lags, "horizon": a.horizon, "key_level": a.key_level,
         "params": {k: getattr(a, k) for k in ("min_valid", "val_days", "model", "features", "min_clicks_flag")}}

    # 1) 读取 + 列识别
    df = read_table(a.input, a.sheet)
    cols, _ = resolve_columns(list(df.columns), {"date": a.date_col, "clicks": a.clicks_col, "orders": a.orders_col})
    for need in ("date", "clicks", "orders"):
        if need not in cols:
            raise SystemExit(f"[FATAL] 缺少必需列 '{need}'。识别到: {cols}\n报表列: {list(df.columns)}")
    S["columns"] = cols
    S["rows_raw"] = int(len(df))

    # 2) 面板
    cr, c_roll, o_roll, days, meta, bad_dates, key_agg = build_panel(df, cols, a.key_level, a.window)
    S["date_range"] = [str(days[0].date()), str(days[-1].date())]
    S["days"] = int(len(days))
    S["unparsed_dates"] = bad_dates
    S["series_total"] = int(cr.shape[1])

    total_win = int(c_roll.notna().sum().sum())
    zero_win = int(((c_roll == 0) & c_roll.notna()).sum().sum())
    S["windows"] = {"total": total_win, "zero_click": zero_win,
                    "zero_click_pct": round(zero_win / total_win * 100, 2) if total_win else None}

    # 3) 筛选序列
    n_valid = (c_roll > 0).sum(axis=0)
    keep = n_valid[n_valid >= a.min_valid].index
    S["series_kept"] = int(len(keep))
    S["series_dropped"] = int(cr.shape[1] - len(keep))
    if key_agg is not None and "spend" in key_agg.columns and float(key_agg["spend"].sum()) > 0 and len(keep):
        S["spend_coverage_pct"] = round(float(key_agg["spend"].reindex(keep).sum() / key_agg["spend"].sum() * 100), 1)
    if len(keep) == 0:
        S["status"] = "insufficient_data"
        S["message"] = (f"没有序列满足 '可用窗口 >= {a.min_valid}'。"
                        f"数据跨度 {S['days']} 天, 窗口 {a.window} 天。"
                        f"建议: 降低 --min-valid、减小 --window, 或改用 --key-level campaign 提高密度。")
        _write_summary(a.out, S, a.json)
        return 0

    cr_k, c_k, o_k = cr[keep], c_roll[keep], o_roll[keep]

    # 4) 样本 + 时间切分
    smp = build_samples(cr_k, a.lags)
    if a.features == "lags+volume":
        vol = np.log1p(c_k.shift(1)).stack(dropna=False).rename("log_clicks_lag1")
        vol.index.names = ["Date", "key"]
        smp = smp.join(vol, on=["Date", "key"])
    feats = [c for c in smp.columns if c.startswith("cr_lag") or c == "log_clicks_lag1"]
    S["samples"] = int(len(smp))

    uniq = np.sort(smp["Date"].unique())
    val_from = uniq[-a.val_days] if len(uniq) > a.val_days else uniq[0]
    tr, va = smp[smp["Date"] < val_from], smp[smp["Date"] >= val_from]
    S["train_samples"], S["val_samples"] = int(len(tr)), int(len(va))
    S["val_from"] = str(pd.Timestamp(val_from).date())

    # 5) 验证: 模型 vs persistence
    val = va[va["cr_lag1"].notna()].copy()
    S["val_evaluable"] = int(len(val))
    result = {"status": "ok"}
    if len(val) >= 30 and len(tr) >= 50 and a.model != "persistence":
        mname, _ = get_model(a.model, a.seed)
        if mname == "ridge":
            mdl = RidgeFallback().fit(tr[feats], tr["y"])
        else:
            mdl = get_model(a.model, a.seed)[1].fit(tr[feats], tr["y"])
        p_model = np.asarray(mdl.predict(val[feats]), float)
        p_pers = val["cr_lag1"].to_numpy()
        mm, mp = metrics(val["y"], p_model), metrics(val["y"], p_pers)
        skill = float(1 - mm["RMSE"] ** 2 / mp["RMSE"] ** 2) if mp["RMSE"] > 0 else 0.0
        result.update(model_backend=mname, model=mm, persistence=mp, skill_vs_persistence=round(skill, 4),
                      use_model=bool(skill > 0))
    else:
        mm = mp = None
        result.update(model="skipped", reason="样本不足或 --model persistence", use_model=False)
    S["validation"] = result

    # 6) 最终拟合 (全部样本) + 递归向前预测
    use_model = result.get("use_model", False)
    fitted = None
    if use_model:
        mname = result["model_backend"]
        fitted = RidgeFallback().fit(smp[feats], smp["y"]) if mname == "ridge" \
            else get_model(a.model, a.seed)[1].fit(smp[feats], smp["y"])

    fut_dates = pd.date_range(days[-1] + pd.Timedelta(days=1), periods=a.horizon, freq="D")
    cr_ext = cr_k.reindex(cr_k.index.append(fut_dates))
    if a.features == "lags+volume":
        vol_last = c_k.iloc[-1]

    preds = {}
    y_cap = max(1.0, float(smp["y"].max()))   # CR 可 >1 (少量点击多单), 只做下界与非负约束
    for h, fd in enumerate(fut_dates, start=1):
        Xh = pd.DataFrame({f"cr_lag{k}": cr_ext.shift(k).loc[fd] for k in range(1, a.lags + 1)})
        if a.features == "lags+volume":
            Xh["log_clicks_lag1"] = np.log1p(vol_last.reindex(Xh.index).to_numpy())
        p_pers = Xh["cr_lag1"].to_numpy()
        p_model = np.asarray(fitted.predict(Xh[feats]), float) if fitted is not None else p_pers
        if fitted is not None:
            p_model = np.clip(p_model, 0.0, y_cap)
        rec = p_model if use_model else p_pers
        preds[fd] = (p_pers, p_model, rec)
        cr_ext.loc[fd] = rec                      # 递归: 预测值回填, 供下一窗口当 lag

    # 7) 组装输出
    last = days[-1]
    out = meta.reindex(keep).copy()
    out["key"] = out.index
    out["clicks_last_window"] = c_k.iloc[-1].reindex(keep).to_numpy()
    out["orders_last_window"] = o_k.iloc[-1].reindex(keep).to_numpy()
    out["cr_last_window"] = cr_k.iloc[-1].reindex(keep).to_numpy()
    out["n_valid_windows"] = n_valid.reindex(keep).to_numpy()
    for h, fd in enumerate(fut_dates, start=1):
        p_pers, p_model, rec = preds[fd]
        tag = "" if a.horizon == 1 else f"_h{h}"
        out[f"cr_pred_persistence{tag}"] = p_pers
        out[f"cr_pred_model{tag}"] = p_model
        out[f"cr_pred_recommended{tag}"] = rec
    out["source"] = "model" if use_model else "persistence"
    out["low_confidence"] = (pd.to_numeric(out["clicks_last_window"], errors="coerce") < a.min_clicks_flag)
    out["window_span"] = f"{a.window}d ending {fut_dates[0].date()}"
    out = out.sort_values("cr_pred_recommended_h1" if a.horizon > 1 else "cr_pred_recommended",
                          ascending=False)
    pred_path = os.path.join(a.out, f"predictions_{a.key_level}_w{a.window}.csv")
    out.to_csv(pred_path, index=False)

    S["output"] = pred_path
    S["predicted_series"] = int(len(out))
    S["low_confidence_pct"] = round(float(out["low_confidence"].mean() * 100), 1)
    S["recommendation_source"] = out["source"].iloc[0]
    S["target_window_end"] = str(fut_dates[0].date())
    top = out.head(10)[[c for c in ["campaign", "adgroup", "targeting", "match_type"] if c in out.columns]
                       + ["cr_last_window", "cr_pred_recommended", "clicks_last_window"]]
    S["top10"] = json.loads(top.to_json(orient="records", date_format="iso"))
    S["status"] = "ok"
    _write_summary(a.out, S, a.json)
    return 0


def _write_summary(outdir, S, as_json):
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(S, f, ensure_ascii=False, indent=2, default=str)
    if as_json:
        print(json.dumps(S, ensure_ascii=False, indent=2, default=str))
        return
    V = S.get("validation", {})
    print("=" * 70)
    print(f"滑动窗口转化率预测  |  窗口 x={S['window']}d  lag K={S['lags']}  粒度={S['key_level']}")
    print("=" * 70)
    print(f"报表         : {S['rows_raw']:,} 行 | {S['date_range'][0]} -> {S['date_range'][1]} ({S['days']} 天)")
    cov = S.get("spend_coverage_pct")
    print(f"序列         : {S['series_total']:,} 个, 保留 {S['series_kept']:,} 个"
          + (f" (覆盖花费 {cov}%)" if cov is not None else ""))
    w = S.get("windows", {})
    print(f"零点击窗口   : {w.get('zero_click', 0):,} / {w.get('total', 0):,} ({w.get('zero_click_pct')}%) -> CR 未定义")
    if S.get("status") == "insufficient_data":
        print(f"\n[!] {S['message']}")
        print(f"\n摘要 -> {os.path.join(outdir, 'summary.json')}")
        return
    print(f"样本         : {S['samples']:,} (训练 {S['train_samples']:,} / 验证 {S['val_samples']:,}, 验证起点 {S['val_from']})")
    if isinstance(V.get("model"), dict):
        m, p = V["model"], V["persistence"]
        print(f"\n验证集 (最后 {S['params']['val_days']} 天, n={S['val_evaluable']:,}) — 必须对照 persistence:")
        print(f"  persistence : MAE={p['MAE']:.4f}  RMSE={p['RMSE']:.4f}  R2={p['R2']:.4f}")
        print(f"  {V['model_backend']:<12s}: MAE={m['MAE']:.4f}  RMSE={m['RMSE']:.4f}  R2={m['R2']:.4f}")
        print(f"  相对基线技能: {V['skill_vs_persistence']*100:+.2f}%  ->  "
              f"{'模型胜出, 推荐列用模型' if V['use_model'] else '模型未胜出, 推荐列自动退回 persistence'}")
    else:
        print(f"\n验证         : 跳过 ({V.get('reason', 'n/a')}) -> 推荐列 = persistence")
    print(f"\n预测目标窗口 : {S['window']} 天, 结束于 {S['target_window_end']}")
    print(f"输出         : {S['output']}  ({S['predicted_series']:,} 个序列)")
    print(f"低置信度占比 : {S['low_confidence_pct']}% (上一窗口点击 < {S['params']['min_clicks_flag']})")
    print(f"推荐列来源   : {S['recommendation_source']}")
    print(f"\n[!] 提醒: 相邻窗口重叠 {S['window']-1}/{S['window']}, 该任务本质接近'抄昨天';"
          f"\n    报告效果请使用'相对基线技能', 不要用 R2 绝对值。")
    print(f"\n摘要 -> {os.path.join(outdir, 'summary.json')}")


if __name__ == "__main__":
    raise SystemExit(main())
