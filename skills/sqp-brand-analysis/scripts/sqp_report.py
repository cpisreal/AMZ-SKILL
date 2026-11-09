#!/usr/bin/env python3
"""
SQP Brand Analysis Report Generator
=====================================
Reads Amazon Search Query Performance (SQP) Brand View weekly CSV exports
and generates:
  - 6 CSV files (structured data for each analysis module)
  - 1 PNG chart   (Top-5 stable terms trend)
  - 1 Markdown report (sqp_report.md, all data tables embedded)

Usage
-----
  python sqp_report.py --input "path/to/SQP/*.csv" --output "./sqp_output/"
  python sqp_report.py --input file_wk1.csv file_wk2.csv --output "./sqp_output/"

Requirements
------------
  pip install pandas matplotlib
"""

import re
import sys
import math
import glob
import argparse
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime

import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.font_manager as fm

# ══════════════════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════════════════

COL_Q       = "Search Query"
COL_IMP_B   = "Impressions: Brand Count"
COL_CLK_B   = "Clicks: Brand Count"
COL_CART_B  = "Cart Adds: Brand Count"
COL_PUR_B   = "Purchases: Brand Count"
COL_IMP_T   = "Impressions: Total Count"
COL_CLK_T   = "Clicks: Total Count"
COL_CART_T  = "Cart Adds: Total Count"
COL_PUR_T   = "Purchases: Total Count"
COL_PUR_RATE   = "Purchases: Purchase Rate %"
COL_IMP_BSHARE = "Impressions: Brand Share %"
COL_PUR_BSHARE = "Purchases: Brand Share %"

ALL_BRAND  = [COL_IMP_B, COL_CLK_B, COL_CART_B, COL_PUR_B]
ALL_TOTAL  = [COL_IMP_T, COL_CLK_T, COL_CART_T, COL_PUR_T]
EXTRA_COLS = [COL_PUR_RATE, COL_IMP_BSHARE, COL_PUR_BSHARE]

PCT_COLS = {
    COL_IMP_B:  "pct_brand_imp",
    COL_CLK_B:  "pct_brand_clk",
    COL_CART_B: "pct_brand_cart",
    COL_PUR_B:  "pct_brand_pur",
}

METRICS = [
    ("曝光", COL_IMP_B,  COL_IMP_T),
    ("点击", COL_CLK_B,  COL_CLK_T),
    ("加购", COL_CART_B, COL_CART_T),
    ("购买", COL_PUR_B,  COL_PUR_T),
]

WEEK_PATTERN = re.compile(r"Week_(\d{4})_(\d{2})_(\d{2})\.csv$", re.I)
TOP_N        = 10
TOP_N_WEEKLY = 25


# ══════════════════════════════════════════════════════════════════════════
# Data Loading & Enrichment
# ══════════════════════════════════════════════════════════════════════════

def week_end_from_path(path: Path) -> Optional[str]:
    m = WEEK_PATTERN.search(path.name)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


# ── 中文后台导出的表头 → 标准英文列名（按归一化后的表头精确匹配）──────────
def _norm_header(h: str) -> str:
    """归一化表头：全角冒号→半角、去冒号两侧空格、压缩多余空格、去掉 % 前空格。"""
    h = str(h).strip().replace("：", ":").replace(":", ":")
    h = re.sub(r"\s+", " ", h)
    h = re.sub(r"\s*:\s*", ":", h)
    return re.sub(r"\s*%\s*", "%", h)

CN_HEADER_MAP = {
    _norm_header(k): v for k, v in {
        "搜索查询":                 COL_Q,
        "搜索查询量":               "Search Query Volume",
        "曝光:曝光总量":            COL_IMP_T,
        "曝光:曝光品牌数量":        COL_IMP_B,
        "曝光:品牌曝光占比%":       COL_IMP_BSHARE,
        "点击量:总次数":            COL_CLK_T,
        "点击量:点击的品牌数":      COL_CLK_B,
        "购物车添加:总数":          COL_CART_T,
        "加入购物车:涉及品牌数":    COL_CART_B,
        "购买:下单总数":            COL_PUR_T,
        "购买次数:品牌数量":        COL_PUR_B,
        "购买次数:品牌份额%":       COL_PUR_BSHARE,
        "下单成交:成交转化率%":     COL_PUR_RATE,
    }.items()
}


def load_sq_csv(path: Path) -> pd.DataFrame:
    """Load one SQP CSV (skip Amazon's first metadata row)."""
    df = pd.read_csv(path, skiprows=1, low_memory=False)
    df.columns = [CN_HEADER_MAP.get(_norm_header(c), c) for c in df.columns]
    wk = week_end_from_path(path)
    if wk is None:
        raise ValueError(
            f"Cannot parse week-end date from filename: {path.name}\n"
            "Expected pattern: ...Week_YYYY_MM_DD.csv"
        )
    df["week_end_label"] = wk
    df["source_file"]    = path.name
    for c in ALL_BRAND + ALL_TOTAL:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    for c in EXTRA_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Add per-week brand portfolio share columns (% of brand weekly total)."""
    parts = []
    for _, chunk in df.groupby("week_end_label", sort=True):
        out = chunk.copy()
        for b_col, pct_col in PCT_COLS.items():
            total = out[b_col].sum()
            out[pct_col] = (out[b_col] / total * 100).round(3) if total > 0 else 0.0
        parts.append(out)
    return pd.concat(parts, ignore_index=True)


# ══════════════════════════════════════════════════════════════════════════
# WoW Helpers
# ══════════════════════════════════════════════════════════════════════════

def wow_rate(curr: float, prev: float) -> Optional[float]:
    return (curr - prev) / prev if prev != 0 else None


def judgment(b_rate: Optional[float], m_rate: Optional[float]) -> str:
    """Return Chinese direction label comparing brand WoW vs market WoW."""
    def _na(x): return x is None or (isinstance(x, float) and math.isnan(x))
    if _na(b_rate): return "品牌上周无数据"
    if _na(m_rate):
        if b_rate > 0.01:  return "大盘上周为零；品牌上涨"
        if b_rate < -0.01: return "大盘上周为零；品牌下跌"
        return "大盘上周为零；品牌持平"
    b_up, m_up = b_rate >= 0, m_rate >= 0
    if b_up and m_up:
        if abs(m_rate) < 0.005: return "大盘近乎持平，品牌上涨"
        r = b_rate / m_rate
        return "↑↑ 比大盘涨得快" if r > 1.5 else ("↑ 与大盘同步上涨" if r >= 0.7 else "↑↓ 比大盘涨得慢")
    if not b_up and not m_up:
        if abs(m_rate) < 0.005: return "大盘近乎持平，品牌下跌"
        r = b_rate / m_rate
        return "↓↓ 比大盘跌得快" if r > 1.5 else ("↓ 与大盘同步下跌" if r >= 0.7 else "↓↑ 比大盘跌得慢")
    if b_up and not m_up: return "⚡ 逆势上涨（大盘跌，品牌涨）"
    return "⚠ 逆势下跌（大盘涨，品牌跌）"


def merge_wow(
    prev: pd.DataFrame, curr: pd.DataFrame, b_col: str, t_col: str
) -> pd.DataFrame:
    p = prev.set_index(COL_Q)[[b_col, t_col]].rename(
        columns={b_col: "b_prev", t_col: "t_prev"})
    c = curr.set_index(COL_Q)[[b_col, t_col]].rename(
        columns={b_col: "b_curr", t_col: "t_curr"})
    m = c.join(p, how="inner").reset_index()
    m["b_wow_abs"]  = m["b_curr"] - m["b_prev"]
    m["b_wow_rate"] = m.apply(lambda r: wow_rate(r["b_curr"], r["b_prev"]), axis=1)
    m["t_wow_rate"] = m.apply(lambda r: wow_rate(r["t_curr"], r["t_prev"]), axis=1)
    def _rel(r):
        bw, tw = r["b_wow_rate"], r["t_wow_rate"]
        if bw is None or tw is None or tw == 0: return None
        if isinstance(bw, float) and math.isnan(bw): return None
        if isinstance(tw, float) and math.isnan(tw): return None
        return bw / tw
    m["relative"] = m.apply(_rel, axis=1)
    m["判断"]      = m.apply(lambda r: judgment(r["b_wow_rate"], r["t_wow_rate"]), axis=1)
    return m


# ══════════════════════════════════════════════════════════════════════════
# Analysis Modules  →  each returns a DataFrame
# ══════════════════════════════════════════════════════════════════════════

def compute_portfolio(df: pd.DataFrame) -> pd.DataFrame:
    keep = (
        ["week_end_label", COL_Q]
        + ALL_BRAND
        + list(PCT_COLS.values())
        + ALL_TOTAL
    )
    return df[[c for c in keep if c in df.columns]].copy()


def compute_high_conv(df: pd.DataFrame) -> pd.DataFrame:
    """Terms where Purchase Rate % / Brand Impression Share % >= 1."""
    results = []
    for wk, chunk in df.groupby("week_end_label", sort=True):
        c = chunk.copy()
        valid = c[COL_IMP_BSHARE].notna() & (c[COL_IMP_BSHARE] > 0)
        c["conv_ratio"] = None
        c.loc[valid, "conv_ratio"] = (
            c.loc[valid, COL_PUR_RATE] / c.loc[valid, COL_IMP_BSHARE]
        ).round(3)
        results.append(c[c["conv_ratio"] >= 1].copy())
    if not results:
        return pd.DataFrame()
    out = pd.concat(results, ignore_index=True)
    keep = ["week_end_label", COL_Q, "conv_ratio",
            COL_PUR_RATE, COL_IMP_BSHARE, COL_PUR_BSHARE] + ALL_BRAND
    return out[[c for c in keep if c in out.columns]]


def compute_wow_new_dropped(df: pd.DataFrame) -> pd.DataFrame:
    weeks = sorted(df["week_end_label"].unique())
    rows = []
    for i in range(len(weeks) - 1):
        pw, cw = weeks[i], weeks[i + 1]
        prev_t = set(df[df["week_end_label"] == pw][COL_Q])
        curr_t = set(df[df["week_end_label"] == cw][COL_Q])
        for t in sorted(curr_t - prev_t):
            rows.append({"prev_week": pw, "curr_week": cw, "status": "新入列", COL_Q: t})
        for t in sorted(prev_t - curr_t):
            rows.append({"prev_week": pw, "curr_week": cw, "status": "跌出列", COL_Q: t})
    return pd.DataFrame(rows)


def compute_wow_self_drops(df: pd.DataFrame) -> pd.DataFrame:
    weeks = sorted(df["week_end_label"].unique())
    rows = []
    for i in range(len(weeks) - 1):
        pw, cw = weeks[i], weeks[i + 1]
        prev = df[df["week_end_label"] == pw]
        curr = df[df["week_end_label"] == cw]
        for label, b_col, t_col in METRICS:
            m = merge_wow(prev, curr, b_col, t_col)
            for _, row in m.nsmallest(TOP_N, "b_wow_abs").iterrows():
                rows.append({
                    "prev_week": pw, "curr_week": cw, "metric": label,
                    COL_Q: row[COL_Q],
                    "b_prev": row["b_prev"], "b_curr": row["b_curr"],
                    "b_wow_abs": row["b_wow_abs"],
                    "b_wow_rate": row["b_wow_rate"],
                })
    return pd.DataFrame(rows)


def compute_wow_market_dev(df: pd.DataFrame) -> pd.DataFrame:
    weeks = sorted(df["week_end_label"].unique())
    rows = []
    for i in range(len(weeks) - 1):
        pw, cw = weeks[i], weeks[i + 1]
        prev = df[df["week_end_label"] == pw]
        curr = df[df["week_end_label"] == cw]
        for label, b_col, t_col in METRICS:
            m = merge_wow(prev, curr, b_col, t_col)
            valid = m.dropna(subset=["b_wow_rate", "t_wow_rate"]).copy()
            valid["deviation"] = (valid["b_wow_rate"] - valid["t_wow_rate"]).abs()
            for _, row in valid.nlargest(TOP_N, "deviation").iterrows():
                rows.append({
                    "prev_week": pw, "curr_week": cw, "metric": label,
                    COL_Q: row[COL_Q],
                    "b_curr": row["b_curr"], "b_prev": row["b_prev"],
                    "b_wow_rate": row["b_wow_rate"],
                    "t_wow_rate": row["t_wow_rate"],
                    "relative": row["relative"],
                    "判断": row["判断"],
                })
    return pd.DataFrame(rows)


def compute_top5(df: pd.DataFrame):
    """Top 5 terms: most weeks + highest avg brand impression share."""
    def _bshare(g):
        safe = g[COL_IMP_T].replace(0, float("nan"))
        return (g[COL_IMP_B] / safe * 100).mean()

    try:
        stats = (
            df.groupby(COL_Q, sort=False)
            .apply(
                lambda g: pd.Series({
                    "week_count":      g["week_end_label"].nunique(),
                    "avg_brand_share": _bshare(g),
                    "avg_imp_b":       g[COL_IMP_B].mean(),
                }),
                include_groups=False,
            )
            .reset_index()
        )
    except TypeError:
        stats = (
            df.groupby(COL_Q, sort=False)
            .apply(lambda g: pd.Series({
                "week_count":      g["week_end_label"].nunique(),
                "avg_brand_share": _bshare(g),
                "avg_imp_b":       g[COL_IMP_B].mean(),
            }))
            .reset_index()
        )
        if COL_Q in stats.columns[1:]:
            stats = stats.loc[:, ~stats.columns.duplicated()]

    max_wks  = int(stats["week_count"].max())
    top5     = (
        stats[stats["week_count"] == max_wks]
        .nlargest(5, "avg_brand_share")
        .reset_index(drop=True)
    )
    top5_terms = top5[COL_Q].tolist()

    detail_cols = (
        [COL_Q, "week_end_label"]
        + ALL_TOTAL + ALL_BRAND
    )
    detail = (
        df[df[COL_Q].isin(top5_terms)]
        [[c for c in detail_cols if c in df.columns]]
        .sort_values([COL_Q, "week_end_label"])
        .copy()
    )
    safe = detail[COL_IMP_T].replace(0, float("nan"))
    detail["brand_imp_share_%"] = (detail[COL_IMP_B] / safe * 100).round(3)

    return top5_terms, detail, top5


# ══════════════════════════════════════════════════════════════════════════
# Chart
# ══════════════════════════════════════════════════════════════════════════

def setup_font():
    available = {f.name for f in fm.fontManager.ttflist}
    for fn in ["PingFang HK", "STHeiti", "Heiti TC", "Arial Unicode MS", "SimHei"]:
        if fn in available:
            matplotlib.rcParams["font.family"] = fn
            break
    matplotlib.rcParams["axes.unicode_minus"] = False


def make_top5_chart(df: pd.DataFrame, top5_terms: List[str], out_path: Path):
    if not top5_terms:
        return
    setup_font()
    COLORS = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B2"]
    n = len(top5_terms)
    fig, axes = plt.subplots(n, 2, figsize=(15, 4.5 * n))
    if n == 1:
        axes = [axes]
    fig.suptitle(
        f"Top {n} 高频 & 高品牌占比搜索词 ｜ 趋势分析\n"
        "左：大盘总曝光量（柱+线）  右：品牌曝光占比 % = 品牌曝光 ÷ 大盘曝光",
        fontsize=13, y=1.01,
    )
    for i, term in enumerate(top5_terms):
        t = df[df[COL_Q] == term].sort_values("week_end_label").reset_index(drop=True)
        x_lbl  = t["week_end_label"].tolist()
        x_pos  = list(range(len(x_lbl)))
        y_mkt  = t[COL_IMP_T]
        safe   = t[COL_IMP_T].replace(0, float("nan"))
        y_bsh  = (t[COL_IMP_B] / safe * 100).round(3)
        color  = COLORS[i % len(COLORS)]

        ax_l = axes[i][0]
        ax_l.bar(x_pos, y_mkt, color=color, alpha=0.65, width=0.55)
        ax_l.plot(x_pos, y_mkt, color=color, marker="o", linewidth=2)
        for xi, yi in zip(x_pos, y_mkt):
            ax_l.annotate(f"{int(yi):,}", (xi, yi),
                          textcoords="offset points", xytext=(0, 6),
                          ha="center", fontsize=8)
        ax_l.set_title(f"[{i+1}] {term[:48]}\n大盘总曝光量", fontsize=9)
        ax_l.set_xticks(x_pos)
        ax_l.set_xticklabels(x_lbl, rotation=25, ha="right", fontsize=8)
        ax_l.set_ylabel("大盘曝光量", fontsize=9)
        ax_l.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
        ax_l.set_ylim(0, y_mkt.max() * 1.25)
        ax_l.grid(axis="y", linestyle="--", alpha=0.4)

        ax_r = axes[i][1]
        ax_r.plot(x_pos, y_bsh, color=color, marker="o", linewidth=2.5)
        ax_r.fill_between(x_pos, y_bsh, alpha=0.15, color=color)
        for xi, yi in zip(x_pos, y_bsh):
            if not (isinstance(yi, float) and math.isnan(yi)):
                ax_r.annotate(f"{yi:.2f}%", (xi, yi),
                              textcoords="offset points", xytext=(0, 7),
                              ha="center", fontsize=9, fontweight="bold", color=color)
        ax_r.set_title(f"[{i+1}] {term[:48]}\n品牌曝光占比 %", fontsize=9)
        ax_r.set_xticks(x_pos)
        ax_r.set_xticklabels(x_lbl, rotation=25, ha="right", fontsize=8)
        ax_r.set_ylabel("品牌曝光占比 %", fontsize=9)
        ax_r.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda v, _: f"{v:.1f}%"))
        y_max = y_bsh.dropna().max() if not y_bsh.dropna().empty else 1
        ax_r.set_ylim(0, max(y_max * 1.35, 1))
        ax_r.grid(axis="y", linestyle="--", alpha=0.4)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ Chart → {out_path.name}")


# ══════════════════════════════════════════════════════════════════════════
# Markdown Report
# ══════════════════════════════════════════════════════════════════════════

def _df_to_md(df: pd.DataFrame, max_rows: int = 60) -> str:
    """Render DataFrame as a plain markdown table (no tabulate dependency)."""
    if df is None or df.empty:
        return "_（无数据）_"
    d = df.head(max_rows).copy().reset_index(drop=True)
    for col in d.select_dtypes(include="float").columns:
        d[col] = d[col].apply(
            lambda x: f"{x:.3f}" if pd.notna(x) else "—"
        )
    d = d.infer_objects(copy=False).fillna("—").astype(str)
    cols = list(d.columns)
    sep  = "| " + " | ".join("---" for _ in cols) + " |"
    hdr  = "| " + " | ".join(cols) + " |"
    body = "\n".join(
        "| " + " | ".join(str(v) for v in row) + " |"
        for _, row in d.iterrows()
    )
    return "\n".join([hdr, sep, body])


def _fmt_rate(x) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    return f"{x * 100:+.1f}%"


def _fmt_rel(x) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    return f"{x:.2f}x"


def build_markdown(
    df, weeks, portfolio, high_conv, wow_nd, wow_self, wow_mkt,
    top5_terms, top5_detail, top5_stats, source_files,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = []

    # ── Cover ─────────────────────────────────────────────────────────────
    lines += [
        "# SQP 品牌搜索词分析报告",
        "",
        f"> **生成时间**：{now}",
        f"> **分析周次**：{weeks[0]} → {weeks[-1]}（共 {len(weeks)} 周）",
        f"> **数据来源**：{chr(10).join('> - ' + f for f in source_files)}",
        "",
        "## 目录",
        "1. [每周品牌数据快照](#一每周品牌数据快照)",
        "2. [每周转化能力高于类目的词](#二每周转化能力高于类目的词)",
        "3. [周对周：新入列 & 跌出列](#三周对周新入列--跌出列)",
        "4. [周对周：和自己比（品牌减少最多）](#四周对周和自己比品牌减少最多)",
        "5. [周对周：和大盘比（偏离最大）](#五周对周和大盘比偏离最大)",
        "6. [全周期 Top 5 高价值词](#六全周期-top-5-高价值词)",
        "",
        "---",
        "",
    ]

    # ── Section 1: Weekly Portfolio ───────────────────────────────────────
    lines += [
        "## 一、每周品牌数据快照",
        "",
        "| 列名 | 含义 |",
        "|---|---|",
        "| `pct_brand_imp` | 该词品牌曝光 ÷ 当周品牌总曝光 × 100% |",
        "| `pct_brand_clk` | 该词品牌点击 ÷ 当周品牌总点击 × 100% |",
        "| `pct_brand_cart` | 该词品牌加购 ÷ 当周品牌总加购 × 100% |",
        "| `pct_brand_pur` | 该词品牌购买 ÷ 当周品牌总购买 × 100% |",
        "",
    ]
    for wk in weeks:
        chunk = df[df["week_end_label"] == wk]
        tot   = "  ".join(
            f"**{lbl}**={int(chunk[b].sum()):,}" for lbl, b, _ in METRICS
        )
        lines += [f"### 周结束 {wk}", "", f"品牌总量：{tot}", ""]
        sub = portfolio[portfolio["week_end_label"] == wk]
        sub = sub.nlargest(TOP_N_WEEKLY, COL_IMP_B)
        cols_show = [COL_Q, COL_IMP_B, "pct_brand_imp",
                     COL_CLK_B, "pct_brand_clk",
                     COL_CART_B, "pct_brand_cart",
                     COL_PUR_B,  "pct_brand_pur"]
        sub = sub[[c for c in cols_show if c in sub.columns]].copy()
        sub.columns = (
            ["搜索词", "品牌曝光", "曝光占比%",
             "品牌点击", "点击占比%",
             "品牌加购", "加购占比%",
             "品牌购买", "购买占比%"][:len(sub.columns)]
        )
        lines += [_df_to_md(sub, max_rows=TOP_N_WEEKLY), "", ""]

    lines += ["---", ""]

    # ── Section 2: High Conversion ────────────────────────────────────────
    lines += [
        "## 二、每周转化能力高于类目的词",
        "",
        "> **筛选**：`Purchases: Purchase Rate %` ÷ `Impressions: Brand Share %` ≥ 1  ",
        "> 表示该词在类目层面购买转化率 ≥ 品牌在该词的曝光占比 → **高潜力、值得加大投放的词**",
        "",
    ]
    for wk in weeks:
        sub = (
            high_conv[high_conv["week_end_label"] == wk]
            if not high_conv.empty else pd.DataFrame()
        )
        lines += [f"### 周结束 {wk}（{len(sub)} 个词）", ""]
        if sub.empty:
            lines += ["_（无符合条件的词）_", ""]
        else:
            d = sub.drop(columns=["week_end_label"], errors="ignore").copy()
            d = d.rename(columns={
                COL_Q: "搜索词", "conv_ratio": "购买率/曝光占比",
                COL_PUR_RATE: "类目购买率%", COL_IMP_BSHARE: "品牌曝光占比%",
                COL_PUR_BSHARE: "品牌购买占比%",
                COL_IMP_B: "品牌曝光", COL_CLK_B: "品牌点击",
                COL_CART_B: "品牌加购", COL_PUR_B: "品牌购买",
            })
            lines += [_df_to_md(d.reset_index(drop=True), max_rows=50), ""]

    lines += ["---", ""]

    # ── Section 3: WoW New / Dropped ──────────────────────────────────────
    lines += ["## 三、周对周：新入列 & 跌出列", ""]
    for i in range(len(weeks) - 1):
        pw, cw = weeks[i], weeks[i + 1]
        lines += [f"### {pw} → {cw}", ""]
        for status in ["新入列", "跌出列"]:
            sub = (
                wow_nd[
                    (wow_nd["prev_week"] == pw) &
                    (wow_nd["curr_week"] == cw) &
                    (wow_nd["status"] == status)
                ] if not wow_nd.empty else pd.DataFrame()
            )
            lines += [f"#### {status}（{len(sub)} 个词）", ""]
            if sub.empty:
                lines += ["_（无）_", ""]
            else:
                lines += [_df_to_md(sub[[COL_Q]].rename(columns={COL_Q: "搜索词"})
                                    .reset_index(drop=True), max_rows=30), ""]

    lines += ["---", ""]

    # ── Section 4: WoW Self Comparison ───────────────────────────────────
    lines += [
        "## 四、周对周：【和自己比】品牌各指标减少最多 Top 10",
        "",
    ]
    for i in range(len(weeks) - 1):
        pw, cw = weeks[i], weeks[i + 1]
        lines += [f"### {pw} → {cw}", ""]
        for label, _, _ in METRICS:
            sub = (
                wow_self[
                    (wow_self["prev_week"] == pw) &
                    (wow_self["curr_week"] == cw) &
                    (wow_self["metric"] == label)
                ] if not wow_self.empty else pd.DataFrame()
            )
            lines += [f"#### 品牌{label}减少最多 Top {TOP_N}", ""]
            if sub.empty:
                lines += ["_（无数据）_", ""]
            else:
                d = sub[[COL_Q, "b_prev", "b_curr", "b_wow_abs", "b_wow_rate"]].copy()
                d["b_wow_rate"] = d["b_wow_rate"].apply(_fmt_rate)
                d.columns = ["搜索词", f"上周品牌{label}",
                             f"本周品牌{label}", f"{label}绝对变化", f"{label}变化率"]
                lines += [_df_to_md(d.reset_index(drop=True)), ""]

    lines += ["---", ""]

    # ── Section 5: WoW Market Comparison ────────────────────────────────
    lines += [
        "## 五、周对周：【和大盘比】品牌波动偏离大盘最大 Top 10",
        "",
        "> **排序依据**：`|品牌WoW率 - 大盘WoW率|` 最大  ",
        "> **相对变化比** = 品牌WoW率 ÷ 大盘WoW率",
        "",
    ]
    for i in range(len(weeks) - 1):
        pw, cw = weeks[i], weeks[i + 1]
        lines += [f"### {pw} → {cw}", ""]
        for label, _, _ in METRICS:
            sub = (
                wow_mkt[
                    (wow_mkt["prev_week"] == pw) &
                    (wow_mkt["curr_week"] == cw) &
                    (wow_mkt["metric"] == label)
                ] if not wow_mkt.empty else pd.DataFrame()
            )
            lines += [f"#### {label}：偏离大盘 Top {TOP_N}", ""]
            if sub.empty:
                lines += ["_（无数据）_", ""]
            else:
                d = sub[
                    [COL_Q, "b_curr", "b_prev", "b_wow_rate", "t_wow_rate", "relative", "判断"]
                ].copy()
                d["b_wow_rate"] = d["b_wow_rate"].apply(_fmt_rate)
                d["t_wow_rate"] = d["t_wow_rate"].apply(_fmt_rate)
                d["relative"]   = d["relative"].apply(_fmt_rel)
                d.columns = ["搜索词", f"本周品牌{label}", f"上周品牌{label}",
                             f"品牌{label}WoW", f"大盘{label}WoW",
                             "品牌/大盘变化比", "判断"]
                lines += [_df_to_md(d.reset_index(drop=True)), ""]

    lines += ["---", ""]

    # ── Section 6: Top 5 Stable Terms ────────────────────────────────────
    lines += [
        "## 六、全周期 Top 5 高价值词",
        "",
        "**筛选**：出现周数最多 → 平均品牌曝光占比最高 → 取 Top 5",
        "",
    ]
    if top5_stats is not None and not top5_stats.empty:
        st = top5_stats[[COL_Q, "week_count", "avg_brand_share", "avg_imp_b"]].copy()
        st.columns = ["搜索词", "出现周数", "平均品牌曝光占比%", "平均品牌曝光量"]
        lines += ["### 词汇总览", "", _df_to_md(st), ""]

    lines += ["### 逐周明细", ""]
    if top5_detail is not None and not top5_detail.empty:
        d = top5_detail.rename(columns={
            COL_Q: "搜索词", "week_end_label": "周",
            COL_IMP_T: "大盘曝光", COL_IMP_B: "品牌曝光",
            "brand_imp_share_%": "品牌曝光占比%",
            COL_CLK_T: "大盘点击", COL_CLK_B: "品牌点击",
            COL_CART_T: "大盘加购", COL_CART_B: "品牌加购",
            COL_PUR_T: "大盘购买", COL_PUR_B: "品牌购买",
        })
        lines += [_df_to_md(d, max_rows=100), ""]

    lines += [
        "---",
        "",
        f"_报告由 `sqp_report.py` 自动生成 @ {now}_",
    ]
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════

def resolve_inputs(raw: List[str]) -> List[Path]:
    """Expand globs, accept directories, single files, or lists."""
    paths = []
    for r in raw:
        files: List[Path] = []
        for g in glob.glob(r):          # glob 命中目录时只收它里面的 csv，不把目录本身当文件
            p = Path(g)
            if p.is_dir():
                files.extend(sorted(p.glob("*.csv")))
            else:
                files.append(p)
        if files:
            paths.extend(files)
        elif Path(r).is_dir():
            paths.extend(sorted(Path(r).glob("*.csv")))
        elif Path(r).is_file():
            paths.append(Path(r))
        else:
            print(f"  ⚠ No match for: {r}", file=sys.stderr)
    return sorted(set(paths))


def main():
    parser = argparse.ArgumentParser(
        description="SQP Brand Analysis Report Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input", nargs="+", required=True,
        help='CSV files, glob pattern, or directory. '
             'E.g. --input "sqp/*.csv"  or  --input wk1.csv wk2.csv',
    )
    parser.add_argument(
        "--output", default="./sqp_output",
        help="Output directory (default: ./sqp_output)",
    )
    args = parser.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load ----------------------------------------------------------------
    input_paths = resolve_inputs(args.input)
    if not input_paths:
        print("Error: no CSV files found. Check --input path.", file=sys.stderr)
        sys.exit(1)

    print(f"Loading {len(input_paths)} file(s)…")
    for p in input_paths:
        print(f"  {p.name}")

    df    = enrich(pd.concat([load_sq_csv(p) for p in input_paths], ignore_index=True))
    weeks = sorted(df["week_end_label"].unique())

    print(f"\nWeeks found: {weeks}")
    if len(weeks) < 2:
        print("⚠  Only 1 week detected. WoW sections will be empty.")

    # Run analyses --------------------------------------------------------
    print("\nRunning analyses…")
    portfolio    = compute_portfolio(df)
    high_conv    = compute_high_conv(df)
    wow_nd       = compute_wow_new_dropped(df)
    wow_self     = compute_wow_self_drops(df)
    wow_mkt      = compute_wow_market_dev(df)
    top5_terms, top5_detail, top5_stats = compute_top5(df)

    # Save CSVs -----------------------------------------------------------
    print("\nSaving CSVs…")
    saves = {
        "weekly_brand_portfolio.csv": portfolio,
        "high_conv_terms.csv":        high_conv,
        "wow_new_dropped.csv":        wow_nd,
        "wow_self_drops.csv":         wow_self,
        "wow_market_deviation.csv":   wow_mkt,
        "top5_stable_terms.csv":      top5_detail,
    }
    for fname, data in saves.items():
        path = out_dir / fname
        data.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"  ✓ {fname}  ({len(data)} rows)")

    # Save chart ----------------------------------------------------------
    print("\nGenerating chart…")
    make_top5_chart(df, top5_terms, out_dir / "sqp_top5_trend.png")

    # Save markdown -------------------------------------------------------
    print("\nBuilding markdown report…")
    md = build_markdown(
        df=df, weeks=weeks,
        portfolio=portfolio,
        high_conv=high_conv,
        wow_nd=wow_nd,
        wow_self=wow_self,
        wow_mkt=wow_mkt,
        top5_terms=top5_terms,
        top5_detail=top5_detail,
        top5_stats=top5_stats,
        source_files=[p.name for p in input_paths],
    )
    md_path = out_dir / "sqp_report.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"  ✓ sqp_report.md  ({len(md.splitlines())} lines)")

    # Summary -------------------------------------------------------------
    print(f"\n{'='*50}")
    print(f"✅  Done!  All outputs in: {out_dir.resolve()}")
    print(f"{'='*50}")
    for fname in list(saves.keys()) + ["sqp_top5_trend.png", "sqp_report.md"]:
        size = (out_dir / fname).stat().st_size
        print(f"  {fname:<35} {size/1024:6.1f} KB")


if __name__ == "__main__":
    main()
