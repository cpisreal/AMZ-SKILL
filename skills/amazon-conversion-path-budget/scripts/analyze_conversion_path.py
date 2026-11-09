#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
转化路径报告 → 广告预算分配分析

输入：Amazon Ads 后台导出的 Conversion Path Report（.xlsx 或 .csv）
输出：终端可读分析 + 可选 Excel 多表

零依赖外部数据：不含任何品牌/客户/账号信息，只吃你自己导出的报表。
"""
import argparse
import csv
import os
import re
import sys
from collections import defaultdict

# ---------------------------------------------------------------- 广告类型归一
# 报表里同一产品有多种写法（展示/视频/流媒体形态），归到粗粒度便于看结构。
# 想保留细分就删掉对应行，只留 "原样" 那一档。
NORM = {
    "Sponsored Products": "SP",
    "Sponsored Brands": "SB",
    "Display (Sponsored Brands)": "SB",
    "Online Video (Sponsored Brands)": "SBV",
    "Sponsored Display": "SD",
    "(Sponsored Display)": "SD",
    "Display (Sponsored Display)": "SD",
    "Display (Amazon DSP)": "DSP",
    "Online Video (Amazon DSP)": "DSP-OV",
    "Streaming TV (Amazon DSP)": "DSP-TV",
    "Amazon DSP": "DSP",
}

# 判定阈值（经验值，不是官方标准。按自己账号情况调）
TH = {
    "concentrated_top2": 0.60,      # 前 2 条路径占比超过它 → 结构高度集中
    "assist_gap": 0.15,             # 出现率 − 开场率 超过它 → 助攻型
    "companion_ratio": 5.0,         # 覆盖/销售 比值：仅作展示参考，判定用下面的 cover 门槛
    "long_chain_gap": 0.05,         # 3+触点新客占比 低于整体这么多 → 长链路偏收割
    "main_transfer": 0.10,          # A→B 组合占总额超过它 → 主要转移关系
    "assist_min_share": 0.10,       # 助攻型要求销售占比至少这么高（不然只是伴随）
    "longtail_each": 0.0005,        # 单条低于它的算长尾
}

COLS_REQUIRED = ["Conversion path", "Sales"]


# ---------------------------------------------------------------- 读表
def norm_header(h):
    return re.sub(r"[^a-z0-9]", "", str(h).lower())


def load_rows(path):
    """返回 (headers, rows)。xlsx 需要 openpyxl，csv 用标准库。"""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".csv", ".txt"):
        for enc in ("utf-8-sig", "utf-8", "gbk", "latin-1"):
            try:
                with open(path, newline="", encoding=enc) as f:
                    rd = list(csv.reader(f))
                if rd:
                    return rd[0], rd[1:]
            except UnicodeDecodeError:
                continue
        raise SystemExit("读不出这个 CSV 的编码，试试另存为 UTF-8")
    try:
        import openpyxl
    except ImportError:
        raise SystemExit("读 xlsx 需要 openpyxl：pip install openpyxl")
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    # 不用 read_only：部分报表的 <dimension> 标签不准，read_only 会把列截断
    it = ws.iter_rows(values_only=True)
    try:
        hdr = list(next(it))
    except StopIteration:
        raise SystemExit("空文件")
    return hdr, [list(r) for r in it]


def build_index(headers):
    """按归一化列名建索引；同名列保留第一个（报表里有两个 Sponsored Display frequency）"""
    idx = {}
    for i, h in enumerate(headers):
        k = norm_header(h)
        if k and k not in idx:
            idx[k] = i
    return idx


def pick(idx, *cands):
    for c in cands:
        k = norm_header(c)
        if k in idx:
            return idx[k]
    return None


def to_num(v):
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "").replace("$", "").replace("¥", "")
    if not s or s.startswith("#"):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def split_path(p):
    """把 'A > B > C > [Purchase]' 拆成 ['A','B','C']"""
    out = []
    for seg in str(p).split(">"):
        seg = re.sub(r"\[.*?\]", "", seg).strip()
        if seg:
            out.append(NORM.get(seg, seg))
    return out


# ---------------------------------------------------------------- 分析
def analyze(headers, rows):
    idx = build_index(headers)
    i_path = pick(idx, "Conversion path")
    if i_path is None:
        raise SystemExit("找不到 'Conversion path' 列，确认导的是转化路径报告")
    i_sales = pick(idx, "Sales")
    i_pur = pick(idx, "Purchases")
    i_ntb = pick(idx, "New-to-brand product sales")
    i_ntbp = pick(idx, "New-to-brand purchases")
    i_st = pick(idx, "Start Date")
    i_en = pick(idx, "End Date")
    i_cur = pick(idx, "Currency")
    missing = [n for n, v in [("Sales", i_sales)] if v is None]
    if missing:
        raise SystemExit("缺少必需列: " + ", ".join(missing))

    recs = []
    for r in rows:
        if i_path >= len(r):
            continue
        t = split_path(r[i_path])
        if not t:
            continue
        recs.append({
            "toks": t,
            "path": str(r[i_path]).strip(),
            "sales": to_num(r[i_sales]),
            "pur": to_num(r[i_pur]) if i_pur is not None else 0.0,
            "ntb": to_num(r[i_ntb]) if i_ntb is not None else 0.0,
            "ntbp": to_num(r[i_ntbp]) if i_ntbp is not None else 0.0,
            "start": str(r[i_st])[:10] if i_st is not None else "",
            "end": str(r[i_en])[:10] if i_en is not None else "",
        })
    if not recs:
        raise SystemExit("没有解析出任何路径")

    tot_s = sum(x["sales"] for x in recs) or 1.0
    tot_p = sum(x["pur"] for x in recs)
    tot_n = sum(x["ntb"] for x in recs)
    cur = ""
    if i_cur is not None:
        for r in rows:
            if i_cur < len(r) and str(r[i_cur]).strip():
                cur = str(r[i_cur]).strip().upper()
                break
    R = {"currency": cur,
         "total": {"paths": len(recs), "sales": tot_s, "pur": tot_p,
                   "ntb": tot_n, "ntb_ratio": tot_n / tot_s if tot_s else 0,
                   "aov": tot_s / tot_p if tot_p else 0}}

    # --- 集中度 ---
    order = sorted(recs, key=lambda x: -x["sales"])
    cum, marks, acc = [], {}, 0.0
    for k, x in enumerate(order, 1):
        acc += x["sales"]
        cum.append((k, acc / tot_s))
        for tgt in (0.5, 0.8):
            if tgt not in marks and acc / tot_s >= tgt:
                marks[tgt] = k
    longtail = [x for x in recs if x["sales"] / tot_s < TH["longtail_each"]]
    R["concentration"] = {
        "top1": order[0]["sales"] / tot_s,
        "top2": sum(x["sales"] for x in order[:2]) / tot_s,
        "top4": sum(x["sales"] for x in order[:4]) / tot_s,
        "n50": marks.get(0.5), "n80": marks.get(0.8),
        "longtail_n": len(longtail),
        "longtail_share": sum(x["sales"] for x in longtail) / tot_s,
        "top_paths": order[:10],
    }

    # --- 首触点 / 末触点 ---
    def by_end(which):
        g = defaultdict(lambda: [0, 0.0, 0.0, 0.0])
        for x in recs:
            k = x["toks"][0] if which == "start" else x["toks"][-1]
            g[k][0] += 1
            g[k][1] += x["sales"]
            g[k][2] += x["pur"]
            g[k][3] += x["ntb"]
        return sorted(
            [{"k": k, "n": v[0], "sales": v[1], "pur": v[2], "ntb": v[3],
              "share": v[1] / tot_s, "aov": v[1] / v[2] if v[2] else 0,
              "ntb_ratio": v[3] / v[1] if v[1] else 0}
             for k, v in g.items()], key=lambda d: -d["sales"])

    R["start_touch"] = by_end("start")
    R["end_touch"] = by_end("end")

    # --- 产品出现率 / 开场率 ---
    appear = defaultdict(lambda: [0, 0.0])
    for x in recs:
        for a in set(x["toks"]):
            appear[a][0] += 1
            appear[a][1] += x["sales"]
    startn = {d["k"]: d["n"] for d in R["start_touch"]}
    n_paths = len(recs)
    R["products"] = sorted(
        [{"k": k, "paths": v[0], "sales": v[1],
          "cover": v[0] / n_paths, "share": v[1] / tot_s, "start_share": 0.0}
         for k, v in appear.items()], key=lambda d: -d["share"])
    start_sales = {d["k"]: d["sales"] for d in R["start_touch"]}
    for p in R["products"]:
        p["start_share"] = start_sales.get(p["k"], 0.0) / tot_s
        p["assist_gap"] = p["cover"] - p["start_share"]
        p["companion"] = (p["cover"] / p["share"]) if p["share"] > 0 else 0.0

    # --- 触点数量分层 ---
    lay = defaultdict(lambda: [0, 0.0, 0.0, 0.0])
    for x in recs:
        k = min(len(x["toks"]), 5)
        lay[k][0] += 1
        lay[k][1] += x["sales"]
        lay[k][2] += x["pur"]
        lay[k][3] += x["ntb"]
    R["layers"] = [{"n_touch": k, "paths": v[0], "sales": v[1], "pur": v[2],
                    "share": v[1] / tot_s, "aov": v[1] / v[2] if v[2] else 0,
                    "ntb_ratio": v[3] / v[1] if v[1] else 0}
                   for k, v in sorted(lay.items())]
    s12 = sum(x["sales"] for x in R["layers"] if x["n_touch"] <= 2)
    n12 = sum(lay[k][3] for k in lay if k <= 2)
    s3 = sum(x["sales"] for x in R["layers"] if x["n_touch"] >= 3)
    n3 = sum(lay[k][3] for k in lay if k >= 3)
    R["layers_summary"] = {
        "short_share": s12 / tot_s, "short_ntb": n12 / s12 if s12 else 0,
        "long_share": s3 / tot_s, "long_ntb": n3 / s3 if s3 else 0,
    }

    # --- 转移关系 A→B ---
    tr = defaultdict(lambda: [0, 0.0, 0.0, 0.0])
    for x in recs:
        if len(x["toks"]) >= 2:
            k = (x["toks"][0], x["toks"][1])
            tr[k][0] += 1
            tr[k][1] += x["sales"]
            tr[k][2] += x["pur"]
            tr[k][3] += x["ntb"]
    R["transfers"] = sorted(
        [{"a": a, "b": b, "paths": v[0], "sales": v[1], "pur": v[2],
          "share": v[1] / tot_s, "aov": v[1] / v[2] if v[2] else 0,
          "ntb_ratio": v[3] / v[1] if v[1] else 0}
         for (a, b), v in tr.items()], key=lambda d: -d["sales"])

    # --- 单点路径 ---
    R["single"] = sorted([x for x in recs if len(x["toks"]) == 1],
                         key=lambda x: -x["sales"])

    R["judge"] = judge(R)
    return R


def judge(R):
    """把指标翻成可执行的判断。

    只给方向与动作，不给预算百分比 —— 每个账号的结构不同，比例得自己定。
    分类口径：
      伴随型 = 覆盖广但销售占比低（覆盖/销售比 大），是"到处都在但不是主角"；
      助攻型 = 销售占比够分量，但自己开来单少（出现在别人开场的路径里）；
      两者都不满足的，不报 —— 避免每条广告都输出一条噪音。
    """
    out = []
    c = R["concentration"]
    T = R["total"]

    if c["top2"] >= TH["concentrated_top2"]:
        out.append({"level": "high", "msg":
                    "结构高度集中：前 2 条路径占 %.1f%%，主力广告做结构性调整（砍词、改出价策略、挪预算）会直接反映到总销售。"
                    % (c["top2"] * 100),
                    "act": "主力按护栏管理，增量放到新位置，不动存量。"})

    # 单点路径的头部（常是最不能动的那条）
    if R["single"]:
        top = R["single"][0]
        share = top["sales"] / T["sales"]
        if share >= 0.15:
            out.append({"level": "high", "msg":
                        "最大的单触点路径是 %s，一条就占 %.1f%% 的销售，中间没有任何多触点协同。"
                        % (top["toks"][0], share * 100),
                        "act": "这条对应「搜到就买」的人群，任何改动先小流量验证。"})

    # 伴随型 / 助攻型
    companions, assistants = [], []
    for p in R["products"]:
        if p["share"] < 0.005:          # 千分之五以下，连伴随都算不上，直接不报
            continue
        if p["share"] >= TH["assist_min_share"] and p["assist_gap"] >= TH["assist_gap"]:
            assistants.append(p)        # 有份量、但自己开不了单 → 助攻型
        elif p["share"] < TH["assist_min_share"] and p["cover"] >= 0.15:
            companions.append(p)        # 覆盖面广、产出小 → 伴随型
        # 其余（销售占比高、自己也开场）= 主力，不报

    for p in assistants[:2]:
        out.append({"level": "mid", "msg":
                    "%s 是助攻型：出现在 %.1f%% 的路径里，自己开场只占 %.1f%%（差 %.1f 个百分点），但它参与路径的销售合计 %.1f%%。"
                    % (p["k"], p["cover"] * 100, p["start_share"] * 100,
                       p["assist_gap"] * 100, p["share"] * 100),
                    "act": "按覆盖考核，不用末次点击 ROI 判去留。"})

    if companions:
        names = "、".join("%s（覆盖 %.0f%%／销售 %.1f%%）"
                          % (p["k"], p["cover"] * 100, p["share"] * 100) for p in companions[:4])
        total_share = sum(p["share"] for p in companions)
        out.append({"level": "low", "msg":
                    "%s 是伴随型：路径覆盖很广，销售占比很低，合计只有 %.1f%%。" % (names, total_share * 100),
                    "act": "按维持给预算，不按拉动成交给。"})

    # 长链路偏收割（没有新客列时跳过）
    L = R["layers_summary"]
    if T["ntb"] > 0 and L["long_ntb"] < T["ntb_ratio"] - TH["long_chain_gap"]:
        out.append({"level": "mid", "msg":
                    "长链路偏收割：3 个触点以上的路径新客占比 %.1f%%，低于整体 %.1f%%，但它们只占 %.1f%% 的销售。"
                    % (L["long_ntb"] * 100, T["ntb_ratio"] * 100, L["long_share"] * 100),
                    "act": "拉新预算给 1–2 触点的短路径；长链路按复购指标考核。"})

    # 主要转移关系
    for t in [x for x in R["transfers"] if x["share"] >= TH["main_transfer"]][:2]:
        out.append({"level": "info", "msg":
                    "主要转移：%s → %s，%d 条路径占 %.1f%%，客单价 %.1f。"
                    % (t["a"], t["b"], t["paths"], t["share"] * 100, t["aov"]),
                    "act": "%s 跑稳后，增量预算优先给 %s。" % (t["a"], t["b"])})
    return out


# ---------------------------------------------------------------- 输出
def pct(x):
    return "%.1f%%" % (x * 100)


SYMBOL = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CNY": "¥",
          "CAD": "C$", "AUD": "A$", "MXN": "MX$", "INR": "₹", "BRL": "R$"}


def money(x, cur=""):
    """按报表币种加符号；认不出的币种只给数字，不瞎猜符号"""
    sym = SYMBOL.get((cur or "").upper(), "")
    s = format(round(x), ",")
    return (sym + s) if sym else s


def render(R, top_n=10):
    L = []
    a = L.append
    T = R["total"]
    cur = R.get("currency", "")

    def m(x):
        return money(x, cur)
    a("=" * 66)
    a("转化路径报告 · 预算分配分析")
    a("=" * 66)
    a("路径 %d 条 | 销售 %s%s | 订单 %s | 客单价 %.1f | 新客占比 %s"
      % (T["paths"], m(T["sales"]), (" " + cur) if cur else "",
         format(round(T["pur"]), ","), T["aov"], pct(T["ntb_ratio"])))

    c = R["concentration"]
    a("\n【一】集中度：钱压在几条路径上")
    a("  第 1 条 %s | 前 2 条 %s | 前 4 条 %s" % (pct(c["top1"]), pct(c["top2"]), pct(c["top4"])))
    a("  累计到 50%% 需 %s 条，到 80%% 需 %s 条" % (c["n50"], c["n80"]))
    a("  长尾（单条 < %.2f%%）%d 条，合计 %s"
      % (TH["longtail_each"] * 100, c["longtail_n"], pct(c["longtail_share"])))
    a("  前 %d 条路径：" % min(top_n, len(c["top_paths"])))
    for k, x in enumerate(c["top_paths"][:top_n], 1):
        a("    %2d. %-58s %10s %6.1f%%" % (k, " > ".join(x["toks"])[:58], m(x["sales"]), x["sales"] / T["sales"] * 100))

    a("\n【二】谁在开场（首触点）")
    for d in R["start_touch"]:
        a("  %-10s %3d 条  %10s  %5s  客单价 %.1f" % (d["k"], d["n"], m(d["sales"]), pct(d["share"]), d["aov"]))

    a("\n【三】A 跑了之后接什么（首→次转移）")
    a("  %-8s %-10s %4s %11s %7s %7s" % ("A", "→ B", "路径", "销售", "占比", "客单价"))
    for t in R["transfers"][:top_n]:
        a("  %-8s %-10s %4d %11s %7s %7.1f" % (t["a"], t["b"], t["paths"], m(t["sales"]),
                                               pct(t["share"]), t["aov"]))

    a("\n【四】触点数量分层")
    a("  %4s %5s %11s %7s %7s %8s" % ("触点", "路径", "销售", "占比", "客单价", "新客占比"))
    for d in R["layers"]:
        tag = "%d" % d["n_touch"] if d["n_touch"] < 5 else "5+"
        a("  %4s %5d %11s %7s %7.1f %8s" % (tag, d["paths"], m(d["sales"]),
                                            pct(d["share"]), d["aov"], pct(d["ntb_ratio"])))
    Ls = R["layers_summary"]
    a("  1–2 触点合计 %s 销售 / %s 新客；3+ 触点 %s 销售 / %s 新客"
      % (pct(Ls["short_share"]), pct(Ls["short_ntb"]), pct(Ls["long_share"]), pct(Ls["long_ntb"])))

    a("\n【五】各广告产品的覆盖 vs 销售")
    a("  %-10s %7s %8s %8s %8s %8s" % ("产品", "路径数", "覆盖率", "销售占比", "开场占比", "覆盖/销售"))
    for p in R["products"]:
        a("  %-10s %7d %8s %8s %8s %8.1f" % (p["k"], p["paths"], pct(p["cover"]),
                                             pct(p["share"]), pct(p["start_share"]), p["companion"]))

    a("\n【六】判断与动作")
    for j in R["judge"]:
        icon = {"high": "!!", "mid": "! ", "low": "· ", "info": "i "}.get(j["level"], "  ")
        a("  %s %s" % (icon, j["msg"]))
        a("     → %s" % j["act"])

    a("\n" + "-" * 66)
    a("阈值是经验值（脚本顶部 TH 可改）：集中度 %.0f%% / 助攻差 %.0fpt / 伴随比 %.0fx / 长链新客差 %.0fpt"
      % (TH["concentrated_top2"] * 100, TH["assist_gap"] * 100,
         TH["companion_ratio"], TH["long_chain_gap"] * 100))
    a("这是路径归因，不是因果：某广告出现在成交路径里，不等于它促成了成交。")
    return "\n".join(L)


def export_xlsx(R, out):
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment
    except ImportError:
        print("（跳过 Excel 导出：未安装 openpyxl）")
        return
    wb = openpyxl.Workbook()
    bold = Font(bold=True)

    def sheet(title, headers, rows, widths=None):
        ws = wb.create_sheet(title)
        ws.append(headers)
        for c in ws[1]:
            c.font = bold
        for r in rows:
            ws.append(r)
        for i, w in enumerate(widths or [], 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
        ws.freeze_panes = "A2"
        return ws

    wb.remove(wb.active)
    sheet("01_概览", ["指标", "数值"], [
        ["路径数", R["total"]["paths"]], ["销售额", round(R["total"]["sales"], 2)],
        ["订单数", R["total"]["pur"]], ["客单价", round(R["total"]["aov"], 2)],
        ["新客销售占比", round(R["total"]["ntb_ratio"], 4)],
        ["前1条占比", round(R["concentration"]["top1"], 4)],
        ["前2条占比", round(R["concentration"]["top2"], 4)],
        ["前4条占比", round(R["concentration"]["top4"], 4)],
        ["达到50%需条数", R["concentration"]["n50"] or ""],
        ["达到80%需条数", R["concentration"]["n80"] or ""],
        ["长尾条数", R["concentration"]["longtail_n"]],
        ["长尾合计占比", round(R["concentration"]["longtail_share"], 4)],
    ], [24, 16])

    sheet("02_首触点", ["广告产品", "路径数", "销售额", "占比", "订单", "客单价", "新客占比"],
          [[d["k"], d["n"], round(d["sales"], 2), round(d["share"], 4), d["pur"],
            round(d["aov"], 2), round(d["ntb_ratio"], 4)] for d in R["start_touch"]],
          [12, 10, 14, 10, 10, 10, 12])

    sheet("03_转移关系", ["首触点", "次触点", "路径数", "销售额", "占比", "订单", "客单价", "新客占比"],
          [[t["a"], t["b"], t["paths"], round(t["sales"], 2), round(t["share"], 4),
            t["pur"], round(t["aov"], 2), round(t["ntb_ratio"], 4)] for t in R["transfers"]],
          [12, 12, 10, 14, 10, 10, 10, 12])

    sheet("04_触点分层", ["触点数量", "路径数", "销售额", "占比", "单价", "客单价", "新客占比"],
          [[d["n_touch"], d["paths"], round(d["sales"], 2), round(d["share"], 4),
            d["pur"], round(d["aov"], 2), round(d["ntb_ratio"], 4)] for d in R["layers"]],
          [12, 10, 14, 10, 10, 10, 12])

    sheet("05_产品覆盖", ["广告产品", "路径数", "覆盖率", "销售占比", "开场占比", "覆盖销售比"],
          [[p["k"], p["paths"], round(p["cover"], 4), round(p["share"], 4),
            round(p["start_share"], 4), round(p["companion"], 2)] for p in R["products"]],
          [12, 10, 10, 12, 12, 12])

    sheet("06_单点路径", ["路径", "销售额", "占比", "订单", "客单价", "新客占比"],
          [[" > ".join(x["toks"]), round(x["sales"], 2),
            round(x["sales"] / R["total"]["sales"], 4), x["pur"],
            round(x["sales"] / x["pur"], 2) if x["pur"] else 0,
            round(x["ntb"] / x["sales"], 4) if x["sales"] else 0] for x in R["single"]],
          [46, 14, 10, 10, 10, 12])

    sheet("07_判断", ["级别", "判断", "动作"],
          [[j["level"], j["msg"], j["act"]] for j in R["judge"]], [8, 70, 50])

    wb.save(out)
    print("\n已导出：%s（7 个表）" % out)


def main():
    ap = argparse.ArgumentParser(description="转化路径报告 → 广告预算分配分析")
    ap.add_argument("file", help="转化路径报告 .xlsx 或 .csv")
    ap.add_argument("--top", type=int, default=10, help="明细显示前几条（默认 10）")
    ap.add_argument("--out", help="导出 Excel 路径，如 result.xlsx")
    a = ap.parse_args()

    hdr, rows = load_rows(a.file)
    R = analyze(hdr, rows)
    print(render(R, a.top))
    if a.out:
        export_xlsx(R, a.out)


if __name__ == "__main__":
    main()
