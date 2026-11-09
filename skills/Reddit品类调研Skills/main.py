#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reddit Voice Mining 入口：给一个关键词，跑完 采集 → 统计 → 图表 → 报告。

用法：
    python3 main.py "cat food" [--subreddits a,b,c] [--limit 15] [--out output]
"""
import argparse
import os
import sys


def check_proxy():
    if not (os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")):
        print("⚠️  未检测到 HTTPS_PROXY / HTTP_PROXY 环境变量。")
        print("    如果外网无法直连，请先配置代理：")
        print("      export HTTPS_PROXY=http://127.0.0.1:你的端口")
        print("      export HTTP_PROXY=http://127.0.0.1:你的端口")
        print()


def main():
    check_proxy()
    parser = argparse.ArgumentParser(description="Reddit Voice Mining：关键词 → 采集 → 统计 → 图表 → 报告")
    parser.add_argument("keyword", help="品类关键词（英文，如 'cat food'）")
    parser.add_argument("--subreddits", default="BuyItForLife,Frugal,AskReddit",
                        help="逗号分隔的相关 subreddit")
    parser.add_argument("--limit", type=int, default=15, help="每个 subreddit 拉取帖子数")
    parser.add_argument("--queries", type=int, default=5, help="行业侧搜索角度数")
    parser.add_argument("--out", default="output", help="输出目录")
    args = parser.parse_args()

    subs = [s.strip() for s in args.subreddits.split(",") if s.strip()]

    print(f"品类调研：{args.keyword}")
    print(f"  subreddits: {subs}")
    print(f"  输出目录: {args.out}")
    print()

    import collect
    import analyze
    import charts
    import report

    collect.collect(args.keyword, subs, args.limit, args.queries, args.out)
    analyze.main(os.path.join(args.out, "data.json"), args.out)
    charts.main(os.path.join(args.out, "data.json"), args.out)
    report.main(os.path.join(args.out, "data.json"), args.out)

    print()
    print("=" * 50)
    print(f"✅ 完成！报告：{args.out}/report.md")
    print(f"   图表：{args.out}/charts/")
    print(f"   原始数据：{args.out}/data.json")


if __name__ == "__main__":
    main()
