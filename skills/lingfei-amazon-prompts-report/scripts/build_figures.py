#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_figures.py — turn analysis.json into the article's figures.

Visual spec (this is the published house style, do not "improve" it):
    canvas      12 x 8 inch @ 200 dpi
    body text   10.5 pt
    chart title 15 pt
    annotation   9 pt
    footnote     8 pt
    primary     #1D4ED8     text #0B1220 / #6B7280     grid #E6E9EE
    white background, no dark "tech" theme, Chinese font Hiragino Sans GB

Usage
    python3 build_figures.py --analysis out/analysis.json --out-dir figures
    python3 build_figures.py --analysis out/analysis.json --out-dir figures --only 03,04

Figures written (PNG, roughly 2200x1570 after tight bbox):
    fig01_rows_vs_prompts.png   一行不等于一条提问
    fig02_concentration.png     累计花费 / 累计销售两条曲线（提问级 + 行级）
    fig03_intent.png            各组曝光占比 vs 销售占比
    fig04_quadrant.png          曝光 x ACOS 四象限散点
    fig05_features.png          文本特征 CTR 对比全场
    fig06_quadrant_sales.png    四格各自拿走多少销售
    fig07_pipeline.png          五把刀的顺序（静态流程图）
"""

import argparse
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

PRIMARY = "#1D4ED8"
TEXT = "#0B1220"
MUTED = "#6B7280"
GRID = "#E6E9EE"
SOFT = "#BFD3F8"
WARN = "#C2410C"

BODY = 10.5
TITLE = 15
NOTE = 9
FOOT = 8

plt.rcParams.update({
    "font.sans-serif": ["Hiragino Sans GB", "Arial Unicode MS", "PingFang SC", "sans-serif"],
    "font.family": "sans-serif",
    "axes.unicode_minus": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": GRID,
    "text.color": TEXT,
    "axes.labelcolor": TEXT,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "font.size": BODY,
    "axes.titlesize": TITLE,
    "axes.labelsize": BODY,
    "xtick.labelsize": NOTE,
    "ytick.labelsize": NOTE,
})

FIGSIZE = (12, 8)
DPI = 200


def bare(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.grid(True, color=GRID, linewidth=0.8, axis="y")
    ax.set_axisbelow(True)


def footnote(fig, text):
    fig.text(0.012, 0.015, text, fontsize=FOOT, color=MUTED, ha="left")


def save(fig, out_dir, name):
    path = os.path.join(out_dir, name)
    fig.savefig(path, dpi=DPI, facecolor="white", bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print("wrote", path)


def fig_rows_vs_prompts(a, out_dir):
    h = a["health"]
    fig, ax = plt.subplots(figsize=FIGSIZE)
    labels = ["报表行数", "唯一提问", "唯一 ASIN", "唯一活动"]
    vals = [h["rows"], h["unique_prompts"], h["unique_asins"], h["unique_campaigns"]]
    bars = ax.bar(labels, vals, color=[PRIMARY, SOFT, SOFT, SOFT], width=0.55)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v * 1.02, "%d" % v, ha="center",
                va="bottom", fontsize=BODY, color=TEXT)
    ax.set_title("一行不等于一条提问：%d 行里其实只有 %d 条话" % (h["rows"], h["unique_prompts"]),
                 loc="left", pad=18, fontweight="bold")
    ax.text(0, 1.02, "每条提问平均占 %.1f 行，最多的一条占 %d 行"
            % (h["rows_per_prompt_mean"] or 0, h["rows_per_prompt_max"]),
            transform=ax.transAxes, fontsize=NOTE, color=MUTED, va="bottom")
    ax.set_ylabel("数量")
    bare(ax)
    footnote(fig, "同一句话 × 多个活动 × 多个 ASIN × 多天 = 多行。先聚合到提问，再算任何比率。")
    save(fig, out_dir, "fig01_rows_vs_prompts.png")


def fig_concentration(a, out_dir):
    fig, ax = plt.subplots(figsize=FIGSIZE)
    p = a["concentration"]["prompt"]["curve"]
    r = a["concentration"]["row"]["curve"]
    ax.plot([x["rank_share"] for x in p], [x["spend_share"] for x in p],
            color=PRIMARY, linewidth=2.2, label="累计花费（按提问）")
    ax.plot([x["rank_share"] for x in p], [x["sales_share"] for x in p],
            color=PRIMARY, linewidth=2.2, linestyle="--", label="累计销售（按提问）")
    ax.plot([x["rank_share"] for x in r], [x["spend_share"] for x in r],
            color=MUTED, linewidth=1.4, alpha=0.75, label="累计花费（按行）")
    ax.plot([x["rank_share"] for x in r], [x["sales_share"] for x in r],
            color=MUTED, linewidth=1.4, alpha=0.75, linestyle="--", label="累计销售（按行）")
    ax.plot([0, 1], [0, 1], color=GRID, linewidth=1.0)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("按花费降序排列，累计已包含的记录占比")
    ax.set_ylabel("累计占比")
    ax.set_title("两条累计线贴得越近，钱撒得越匀", loc="left", pad=18, fontweight="bold")
    ax.legend(frameon=False, fontsize=NOTE, loc="lower right")
    bare(ax)
    ax.grid(True, color=GRID, linewidth=0.8, axis="both")
    footnote(fig, "对角线 = 花费与销售完全同步。线上的开口就是「花了钱没换回销售」的部分。")
    save(fig, out_dir, "fig02_concentration.png")


def fig_intent(a, out_dir):
    groups = a["intent"]["groups"]
    names = [g["group"] for g in groups]
    imp = [g["imp_share"] * 100 for g in groups]
    sal = [g["sales_share"] * 100 for g in groups]
    idx = range(len(names))
    w = 0.38
    fig, ax = plt.subplots(figsize=FIGSIZE)
    b1 = ax.bar([i - w / 2 for i in idx], imp, width=w, color=PRIMARY, label="曝光占比")
    b2 = ax.bar([i + w / 2 for i in idx], sal, width=w, color=SOFT, label="销售占比")
    for bars in (b1, b2):
        for b in bars:
            h = b.get_height()
            ax.text(b.get_x() + b.get_width() / 2, h + 0.8, "%.1f%%" % h,
                    ha="center", va="bottom", fontsize=NOTE, color=TEXT)
    ax.set_xticks(list(idx))
    ax.set_xticklabels(names)
    ax.set_ylabel("占比（%）")
    ax.set_title("曝光占比和销售占比，哪一组对不上", loc="left", pad=18, fontweight="bold")
    ax.legend(frameon=False, fontsize=NOTE, loc="upper right")
    bare(ax)
    footnote(fig, "曝光高于销售 = 在吃流量不转化；销售高于曝光 = 有钱但没被喂量。组内样本少于 20 条只看方向。")
    save(fig, out_dir, "fig03_intent.png")


def fig_quadrant(a, out_dir, items=None):
    items = items or a.get("_items")
    if not items:
        print("skip fig04: no per-prompt items (pass --items prompts.csv)")
        return
    thr = a["quadrants"]["imp_threshold"]
    acos_t = a["quadrants"]["acos_target"] * 100
    cells = a["quadrants"]["cells"]
    fig, ax = plt.subplots(figsize=FIGSIZE)
    colors = {"高曝光·高效": PRIMARY, "高曝光·低效": WARN,
              "低曝光·高效": "#2563EB", "低曝光·低效": "#C7CBD3"}
    for cell, col in colors.items():
        pts = [i for i in items if i["cell"] == cell and i["acos"] is not None]
        if not pts:
            continue
        ax.scatter([max(i["impressions"], 0.6) for i in pts],
                   [min(i["acos"] * 100, 400) for i in pts],
                   s=18, alpha=0.65, color=col,
                   label="%s（%d 条，画出 %d）" % (cell, cells.get(cell, {}).get("n", len(pts)), len(pts)),
                   edgecolors="none")
    no_sales = sum(1 for i in items if i["acos"] is None)
    ax.axvline(thr, color=MUTED, linewidth=1.0, linestyle=":")
    ax.axhline(acos_t, color=MUTED, linewidth=1.0, linestyle=":")
    ax.set_xscale("log")
    ax.set_ylim(0, 400)
    ax.set_xlabel("曝光（对数轴）")
    ax.set_ylabel("ACOS（%，超过 400 截断）")
    ax.set_title("两条线切四格，四格四种动作", loc="left", pad=18, fontweight="bold")
    ax.text(thr * 1.1, 380, "曝光 %d" % thr, fontsize=NOTE, color=MUTED)
    ax.text(0.8, acos_t + 6, "ACOS %.0f%%" % acos_t, fontsize=NOTE, color=MUTED)
    ax.legend(frameon=False, fontsize=NOTE, loc="lower left")
    bare(ax)
    ax.grid(True, color=GRID, linewidth=0.8, axis="both")
    footnote(fig, "另有 %d 条提问一分钱销售都没有、ACOS 算不出来，未画在图上；"
                  "右下角那一大片是噪音，不值得逐条修，左上角才是能加码的地方。" % no_sales)
    save(fig, out_dir, "fig04_quadrant.png")


def fig_features(a, out_dir):
    feats = a["features"]
    base = a["health"]["ctr"] * 100 or 0
    names = [f["feature"] for f in feats][::-1]
    vals = [(f["ctr"] * 100 if f["ctr"] else 0) for f in feats][::-1]
    fig, ax = plt.subplots(figsize=FIGSIZE)
    bars = ax.barh(names, vals, color=PRIMARY, height=0.5)
    for b, v in zip(bars, vals):
        ax.text(v + max(vals) * 0.015, b.get_y() + b.get_height() / 2,
                "%.2f%%" % v, va="center", fontsize=NOTE, color=TEXT)
    ax.axvline(base, color=WARN, linewidth=1.2, linestyle="--")
    ax.text(base, len(names) - 0.35, " 全场 %.2f%%" % base, fontsize=NOTE, color=WARN)
    ax.set_xlabel("CTR（%）")
    ax.set_title("同一份表里，五类说法的点击率差好几倍", loc="left", pad=18, fontweight="bold")
    bare(ax)
    ax.grid(True, color=GRID, linewidth=0.8, axis="x")
    footnote(fig, "一条提问可以同时命中多个特征。命中少于 20 条的特征只看方向。")
    save(fig, out_dir, "fig05_features.png")


def fig_quadrant_sales(a, out_dir):
    cells = a["quadrants"]["cells"]
    names = list(cells.keys())
    vals = [cells[k]["sales_share"] * 100 for k in names]
    counts = [cells[k]["n"] for k in names]
    fig, ax = plt.subplots(figsize=FIGSIZE)
    bars = ax.bar(["%s\n%d 条" % (n, c) for n, c in zip(names, counts)], vals,
                  color=[SOFT, WARN, PRIMARY, "#C7CBD3"], width=0.5)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.5, "%.1f%%" % v,
                ha="center", va="bottom", fontsize=BODY, color=TEXT)
    ax.set_ylabel("占全场销售（%）")
    ax.set_title("哪一格在交销售，哪一格在烧钱", loc="left", pad=18, fontweight="bold")
    bare(ax)
    footnote(fig, "格子的宽度是提问条数，高度是它交回的销售。条数多、销售少的那一格不用管。")
    save(fig, out_dir, "fig06_quadrant_sales.png")


def fig_pipeline(a, out_dir):
    steps = [
        ("1 体检", "有销售行占比\n定层级"),
        ("2 集中度", "累计曲线\n找单点黑洞"),
        ("3 意图分层", "曝光 vs 销售\n找错配"),
        ("4 四象限", "曝光 × ACOS\n挑名单"),
        ("5 文本特征", "哪类字\n该改"),
    ]
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.axis("off")
    w, h, gap = 0.16, 0.34, 0.035
    x = 0.02
    for i, (t1, t2) in enumerate(steps):
        box = FancyBboxPatch((x, 0.36), w, h, boxstyle="round,pad=0.008,rounding_size=0.03",
                             linewidth=1.2, edgecolor=PRIMARY if i % 2 == 0 else SOFT,
                             facecolor="#F6F8FE" if i % 2 == 0 else "white")
        ax.add_patch(box)
        ax.text(x + w / 2, 0.36 + h - 0.07, t1, ha="center", va="center",
                fontsize=BODY, color=TEXT, fontweight="bold")
        ax.text(x + w / 2, 0.36 + h / 2 - 0.03, t2, ha="center", va="center",
                fontsize=NOTE, color=MUTED, linespacing=1.6)
        if i < len(steps) - 1:
            ax.annotate("", xy=(x + w + gap - 0.004, 0.53), xytext=(x + w + 0.004, 0.53),
                        arrowprops=dict(arrowstyle="-|>", color=MUTED, linewidth=1.2))
        x += w + gap
    ax.text(0.02, 0.24, "顺序不能乱：先判层级，再判钱集中不集中，再分层，再挑名单，最后才改字。",
            fontsize=BODY, color=TEXT)
    ax.text(0.02, 0.17, "跳过前两步直接排 ACOS，会把预算推向最差的地方。",
            fontsize=NOTE, color=WARN)
    ax.set_title("五把刀，一条链", loc="left", pad=6, fontweight="bold")
    footnote(fig, "每一刀都有固定取数、固定算法、固定判读口径。缺一步，后面的结论都不成立。")
    save(fig, out_dir, "fig07_pipeline.png")


def load_items(path):
    """Read prompts.csv into the shape fig_quadrant expects."""
    import csv
    out = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            try:
                out.append({
                    "prompt": r["prompt"],
                    "impressions": float(r["impressions"] or 0),
                    "spend": float(r["spend"] or 0),
                    "sales": float(r["sales"] or 0),
                    "ctr": float(r["ctr"]) if r["ctr"] else None,
                    "acos": float(r["acos"]) if r["acos"] else None,
                    "cell": r.get("cell", ""),
                })
            except (KeyError, ValueError):
                continue
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render the Prompts-report article figures.")
    ap.add_argument("--analysis", required=True, help="analysis.json from analyze_prompts_report.py")
    ap.add_argument("--items", help="prompts.csv from analyze_prompts_report.py (needed for fig04)")
    ap.add_argument("--out-dir", default="figures")
    ap.add_argument("--only", help="comma separated figure numbers, e.g. 02,03,05")
    args = ap.parse_args(argv)

    with open(args.analysis, "r", encoding="utf-8") as f:
        a = json.load(f)
    os.makedirs(args.out_dir, exist_ok=True)
    items = load_items(args.items) if args.items else None

    jobs = [("01", lambda: fig_rows_vs_prompts(a, args.out_dir)),
            ("02", lambda: fig_concentration(a, args.out_dir)),
            ("03", lambda: fig_intent(a, args.out_dir)),
            ("04", lambda: fig_quadrant(a, args.out_dir, items)),
            ("05", lambda: fig_features(a, args.out_dir)),
            ("06", lambda: fig_quadrant_sales(a, args.out_dir)),
            ("07", lambda: fig_pipeline(a, args.out_dir))]
    only = set(x.strip() for x in args.only.split(",")) if args.only else None
    for num, fn in jobs:
        if only and num not in only:
            continue
        fn()
    return 0


if __name__ == "__main__":
    sys.exit(main())
