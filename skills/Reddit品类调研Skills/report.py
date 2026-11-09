#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""报告：根据 stats.json 生成 markdown 数据报告。"""
import json
import os


def render(stats):
    kw = stats.get("keyword", "")
    lines = []
    lines.append(f"# 品类调研数据报告：{kw}")
    lines.append("")
    lines.append(f"> 采集时间：{stats.get('collected_at', '')}  ")
    lines.append("> 本报告由 Reddit Voice Mining 自动生成，数据为 Reddit 公开讨论 + 零注册搜索。")
    lines.append("")
    lines.append("## 一、数据规模")
    lines.append("")
    lines.append("| 维度 | 数量 |")
    lines.append("|---|---|")
    lines.append(f"| 帖子 | {stats['total_posts']} |")
    lines.append(f"| 评论 | {stats['total_comments']} |")
    lines.append(f"| 总字数 | {stats['total_chars']:,} |")
    lines.append(f"| 其中评论字数 | {stats['comment_chars']:,} |")
    lines.append("")
    lines.append("## 二、社区分布")
    lines.append("")
    lines.append("| 社区 | 帖子数 |")
    lines.append("|---|---|")
    for s, c in stats["subreddit_dist"].items():
        lines.append(f"| r/{s} | {c} |")
    lines.append("")
    lines.append("## 三、评论长尾")
    lines.append("")
    lines.append("| 每帖评论数 | 帖子数 |")
    lines.append("|---|---|")
    for k, v in stats["comment_buckets"].items():
        lines.append(f"| {k} | {v} |")
    lines.append("")
    lines.append("> 解读：多数帖子是冷门帖（0–5 条评论），少数爆款帖贡献了最深的信号。")
    lines.append("")
    _cat_cn = {"Decision": "决策", "Pain": "痛点", "Price": "价格", "Quality": "质量"}
    lines.append("## 四、词频信号（按角度）")
    lines.append("")
    for cat, d in stats["angle_freq"].items():
        if not d:
            continue
        top = sorted(d.items(), key=lambda x: -x[1])[:5]
        s = "、".join(f"{k}（{v}）" for k, v in top)
        lines.append(f"- **{_cat_cn.get(cat, cat)}**：{s}")
    lines.append("")
    lines.append("## 五、高频词 Top 25")
    lines.append("")
    for w, n in stats["top_words"]:
        lines.append(f"- {w}：{n}")
    lines.append("")
    lines.append("## 六、数据局限（诚实标注）")
    lines.append("")
    lines.append("- 词频反映「被讨论的热度」，不等于真实的市场规模或发病率。")
    lines.append("- 样本来自 Reddit 若干社区，偏向「更关注该品类的活跃用户」，不代表全体消费者。")
    lines.append("- 数据为公开讨论快照，可能有时效性。")
    lines.append("")
    lines.append("## 下一步建议")
    lines.append("")
    lines.append("数据包已就绪。可用任意 LLM 对 `data.json` 做进一步提炼（痛点聚类、")
    lines.append("需求分层、结构性张力、机会矩阵），产出洞察报告。")
    lines.append("")
    return "\n".join(lines)


def main(data_path, out_dir):
    stats = load(os.path.join(out_dir, "stats.json"))
    stats["collected_at"] = load(data_path).get("collected_at", "")
    md = render(stats)
    path = os.path.join(out_dir, "report.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"  报告完成：{path}")


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    main("output/data.json", "output")
