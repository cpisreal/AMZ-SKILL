#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统计：读取 data.json，产出词频 / 来源分布 / 评论长尾 / 主题矩阵。"""
import json
import os
import re
from collections import Counter


# 通用角度词（跨品类适用，反映决策/痛点/价格/质量四类信号）
# key 用英文，图表跨平台渲染不出方框；报告层再映射成中文。
ANGLE_KEYWORDS = {
    "Decision": ["best", "worth", "recommend", "vs", "alternative", "compare", "should i", "which"],
    "Pain": ["problem", "issue", "broken", "defect", "recall", "regret", "disappointed", "waste", "fail"],
    "Price": ["expensive", "cheap", "price", "cost", "budget", "overpriced", "worth the money", "afford"],
    "Quality": ["quality", "durable", "reliable", "premium", "lasted", "broke after", "years", "lifetime"],
}


def load(data_path):
    with open(data_path, encoding="utf-8") as f:
        return json.load(f)


def analyze(data):
    posts = data.get("posts", [])
    blob = " ".join(
        [p.get("title", "") for p in posts]
        + [p.get("selftext", "") or "" for p in posts]
        + [c["body"] for p in posts for c in (p.get("comments") or [])]
    ).lower()

    total_comments = sum(len(p.get("comments") or []) for p in posts)
    title_chars = sum(len(p.get("title") or "") for p in posts)
    body_chars = sum(len(p.get("selftext") or "") for p in posts)
    comment_chars = sum(len(c["body"]) for p in posts for c in (p.get("comments") or []))

    # subreddit 分布
    sub_dist = Counter(p.get("subreddit") for p in posts)

    # 评论长尾（分桶）
    buckets = {"0": 0, "1-5": 0, "6-15": 0, "16-30": 0, "31-60": 0, "61-100": 0}
    for p in posts:
        n = len(p.get("comments") or [])
        if n == 0:
            buckets["0"] += 1
        elif n <= 5:
            buckets["1-5"] += 1
        elif n <= 15:
            buckets["6-15"] += 1
        elif n <= 30:
            buckets["16-30"] += 1
        elif n <= 60:
            buckets["31-60"] += 1
        else:
            buckets["61-100"] += 1

    # 热度分布
    score_buckets = {"0-9": 0, "10-49": 0, "50-99": 0, "100-199": 0, "200+": 0}
    for p in posts:
        s = p.get("score") or 0
        if s < 10:
            score_buckets["0-9"] += 1
        elif s < 50:
            score_buckets["10-49"] += 1
        elif s < 100:
            score_buckets["50-99"] += 1
        elif s < 200:
            score_buckets["100-199"] += 1
        else:
            score_buckets["200+"] += 1

    # 角度词频
    angle_freq = {}
    for category, kws in ANGLE_KEYWORDS.items():
        angle_freq[category] = {kw: blob.count(kw) for kw in kws if blob.count(kw) > 0}

    # 自动高频词（Top 20，排除停用词，简单分词按空格/标点）
    stop = set("the a an and or but if then of to in on for is are was were be been being i you he she it we they my your his her its our their this that these those with without about from by as at not no so do does did can could will would should may might have has had just very really much more most some any all".split())
    words = re.findall(r"[a-z]{3,}", blob)
    freq = Counter(w for w in words if w not in stop)
    top_words = freq.most_common(25)

    return {
        "keyword": data.get("keyword"),
        "total_posts": len(posts),
        "total_comments": total_comments,
        "total_chars": title_chars + body_chars + comment_chars,
        "title_chars": title_chars,
        "body_chars": body_chars,
        "comment_chars": comment_chars,
        "subreddit_dist": dict(sub_dist.most_common()),
        "comment_buckets": buckets,
        "score_buckets": score_buckets,
        "angle_freq": angle_freq,
        "top_words": top_words,
    }


def main(data_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    data = load(data_path)
    stats = analyze(data)
    path = os.path.join(out_dir, "stats.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=1)
    print(f"  统计完成：帖子 {stats['total_posts']}，评论 {stats['total_comments']}，"
          f"字数 {stats['total_chars']:,}")
    return stats


if __name__ == "__main__":
    main("output/data.json", "output")
