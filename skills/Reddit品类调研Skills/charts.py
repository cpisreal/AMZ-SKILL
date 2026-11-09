#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图表：根据 stats.json 生成白底极简 + 麦肯锡风图表（跨平台，无中文字体依赖）。"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import Patch

# 白底极简色板（只实现一次）
INK, INK2, GRID = "#0B1220", "#6B7280", "#E6E9EE"
ACC, WARN, MUTE = "#12A5BE", "#C77A2A", "#B9C6CC"
FILL = "#BFE3EA"
ACC_DEEP = "#0E8FA6"

plt.rcParams["axes.unicode_minus"] = False


def setup_font():
    """尝试中文字体，找不到就返回 None（图表用英文标签，跨平台不报错）。"""
    available = {f.name for f in fm.fontManager.ttflist}
    for name in ["Hiragino Sans GB", "PingFang SC", "Microsoft YaHei", "SimHei",
                 "Noto Sans CJK SC", "Noto Sans SC", "STHeiti"]:
        if name in available:
            return name
    return None


FONT_NAME = setup_font()

# 全局生效：否则只有显式 set_fontproperties 的文本能用中文字体，
# 其余（标题、副标题、标签）走 DejaVu → 缺字变方块。
if FONT_NAME:
    plt.rcParams["font.sans-serif"] = [FONT_NAME] + [
        f for f in plt.rcParams["font.sans-serif"] if f != FONT_NAME]
    plt.rcParams["font.family"] = "sans-serif"


def _fp():
    return fm.FontProperties(family=FONT_NAME) if FONT_NAME else None


def T(zh, en):
    """有中文字体就用中文标题，否则退回英文（保证任何机器都能跑）。"""
    return zh if FONT_NAME else en


def _apply(text_obj, size, color=INK, bold=False):
    if FONT_NAME:
        text_obj.set_fontproperties(_fp())
    text_obj.set_fontsize(size)
    text_obj.set_color(color)
    if bold:
        text_obj.set_fontweight("bold")


def style_ax(ax):
    ax.set_facecolor("white")
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    for s in ["left", "bottom"]:
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, length=0, labelsize=10)


def title(ax, t, sub=None):
    ax.set_title(t, fontsize=14, color=INK, fontweight="bold", loc="left", pad=21)
    if FONT_NAME:
        ax.title.set_fontproperties(_fp())
    if sub:
        ax.text(0, 1.015, sub, transform=ax.transAxes, ha="left", va="bottom",
                fontsize=8.5, color=INK2)
        if FONT_NAME:
            for t_ in ax.texts:
                t_.set_fontproperties(_fp())


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def chart_data_scale(stats, out_dir):
    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=150)
    labels = ["posts", "comments", "search hits"]
    vals = [stats["total_posts"], stats["total_comments"],
            len(stats.get("search_hits", [])) if isinstance(stats.get("search_hits"), list) else 0]
    # search_hits 可能不在 stats 里，从 data 里取；这里用 subreddit 之外的兜底
    colors = [FILL, ACC, FILL]
    bars = ax.bar(labels, vals, color=colors, edgecolor=MUTE, linewidth=1.2, width=0.5)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + max(vals) * 0.03, f"{v:,}",
                ha="center", fontsize=13, color=INK, fontweight="bold")
    ax.set_ylim(0, max(vals) * 1.25)
    style_ax(ax)
    ax.grid(axis="y", color=GRID, linewidth=0.7, alpha=0.8)
    ax.set_axisbelow(True)
    title(ax, T("数据规模：评论才是主信号", "Data scale: comments are the main signal"),
          T(f"{stats['total_chars']:,} 字真实消费者原话",
            f"{stats['total_chars']:,} chars of real consumer voice"))
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "01_data_scale.png"), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()


def chart_subreddit(stats, out_dir):
    fig, ax = plt.subplots(figsize=(10, 4.6), dpi=150)
    dist = stats["subreddit_dist"]
    subs = list(dist.keys())[:8][::-1]
    vals = [dist[s] for s in subs][::-1]
    ypos = range(len(subs))
    ax.barh(list(ypos), vals, color=FILL, edgecolor=ACC, linewidth=1.1, height=0.55)
    for y, v in zip(ypos, vals):
        ax.text(v + max(vals) * 0.02, y, f"{v}", va="center", fontsize=11,
                color=INK, fontweight="bold")
    ax.set_yticks(list(ypos))
    ax.set_yticklabels([f"r/{s}" for s in subs], fontsize=11, color=INK)
    ax.set_xlim(0, max(vals) * 1.18)
    style_ax(ax)
    ax.grid(axis="x", color=GRID, linewidth=0.7, alpha=0.8)
    ax.set_axisbelow(True)
    title(ax, T("社区分布", "Subreddit distribution"),
          T("讨论最集中的社区", "top communities where the topic is discussed"))
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "02_subreddit.png"), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()


def chart_comments(stats, out_dir):
    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=150)
    buckets = stats["comment_buckets"]
    order = ["0", "1-5", "6-15", "16-30", "31-60", "61-100"]
    vals = [buckets[k] for k in order]
    colors = [FILL, ACC, FILL, FILL, FILL, WARN]
    bars = ax.bar(order, vals, color=colors, edgecolor=MUTE, linewidth=1.1, width=0.58)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + max(vals) * 0.02, f"{v}",
                ha="center", fontsize=12, color=INK, fontweight="bold")
    ax.set_ylim(0, max(vals) * 1.2)
    style_ax(ax)
    ax.grid(axis="y", color=GRID, linewidth=0.7, alpha=0.8)
    ax.set_axisbelow(True)
    title(ax, T("评论分布：长尾结构", "Comment distribution: long tail"),
          T("少数爆款帖承载主要信号，多数帖子很安静",
            "few viral posts carry most signal; most posts are quiet"))
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "03_comments.png"), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()


def chart_keywords(stats, out_dir):
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=150)
    angle = stats["angle_freq"]
    cats = ["Decision", "Pain", "Price", "Quality"]
    # 每类取最高的 2 个词
    items = []
    for cat in cats:
        d = angle.get(cat, {})
        top2 = sorted(d.items(), key=lambda x: -x[1])[:2]
        for kw, n in top2:
            items.append((f"{cat} · {kw}", n))
    items.sort(key=lambda x: x[1])
    names = [i[0] for i in items]
    vals = [i[1] for i in items]
    ypos = range(len(names))
    ax.barh(list(ypos), vals, color=FILL, edgecolor=ACC, linewidth=1.0, height=0.6)
    for y, v in zip(ypos, vals):
        ax.text(v + max(vals) * 0.02, y, f"{v}", va="center", fontsize=10.5,
                color=INK, fontweight="bold")
    ax.set_yticks(list(ypos))
    ax.set_yticklabels(names, fontsize=10, color=INK)
    ax.set_xlim(0, max(vals) * 1.25)
    style_ax(ax)
    ax.grid(axis="x", color=GRID, linewidth=0.7, alpha=0.8)
    ax.set_axisbelow(True)
    title(ax, T("按角度的关键词信号", "Keyword signals by angle"),
          T("决策 / 痛点 / 价格 / 质量 —— 讨论集中在哪",
            "decision / pain / price / quality — where the discussion concentrates"))
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "04_keywords.png"), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()


def chart_score(stats, out_dir):
    fig, ax = plt.subplots(figsize=(10, 4.6), dpi=150)
    buckets = stats["score_buckets"]
    order = ["0-9", "10-49", "50-99", "100-199", "200+"]
    vals = [buckets[k] for k in order]
    colors = [FILL, FILL, FILL, ACC, WARN]
    bars = ax.bar(order, vals, color=colors, edgecolor=MUTE, linewidth=1.1, width=0.55)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + max(vals) * 0.02, f"{v}",
                ha="center", fontsize=12, color=INK, fontweight="bold")
    ax.set_ylim(0, max(vals) * 1.25)
    style_ax(ax)
    ax.grid(axis="y", color=GRID, linewidth=0.7, alpha=0.8)
    ax.set_axisbelow(True)
    title(ax, T("热度分布：爆款是少数", "Score distribution: viral posts are rare"),
          T("多数帖子热度低，少数承载最深信号",
            "most posts are low-score; a few carry the deepest signal"))
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "05_score.png"), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()


def main(data_path, out_dir):
    data = load(data_path)
    stats = load(os.path.join(out_dir, "stats.json"))
    stats["search_hits"] = data.get("search_results", [])
    charts_dir = os.path.join(out_dir, "charts")
    os.makedirs(charts_dir, exist_ok=True)
    chart_data_scale(stats, charts_dir)
    chart_subreddit(stats, charts_dir)
    chart_comments(stats, charts_dir)
    chart_keywords(stats, charts_dir)
    chart_score(stats, charts_dir)
    print(f"  图表完成：{len(os.listdir(charts_dir))} 张 → {charts_dir}")


if __name__ == "__main__":
    main("output/data.json", "output")
