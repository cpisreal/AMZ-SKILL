#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reddit 品类调研 Skills —— 一条命令入口。

用法：
    python run.py demo                          # 离线试跑（用自带示例数据，不联网）
    python run.py "cat food" --subreddits catfood,CatAdvice,cats,AskVet
    python run.py "air fryer" --limit 15 --out ./out
"""
import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def run_from_data(data_path, out_dir):
    """跑「统计 → 图表 → 报告」三步（不需要联网）。"""
    import analyze
    import charts
    import report
    analyze.main(data_path, out_dir)
    charts.main(data_path, out_dir)
    report.main(data_path, out_dir)


def cmd_demo(out_dir):
    """离线试跑：把自带示例数据跑完整链路，验证环境是否可用。"""
    src = os.path.join(HERE, "demo", "data.json")
    if not os.path.exists(src):
        raise SystemExit("找不到示例数据 demo/data.json")
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, "data.json")
    if os.path.abspath(dst) != os.path.abspath(src):
        shutil.copyfile(src, dst)
    print(f"[demo] 用示例数据（250 帖 / 1,785 评论 / 81 万字）跑到 {out_dir}")
    run_from_data(dst, out_dir)
    print()
    print("=" * 52)
    print(f"✅ 试跑完成：报告 {out_dir}/report.md，图表 {out_dir}/charts/")
    print("   示例成品已随包提供：demo/成品_示例报告.md + demo/charts/")


def cmd_live(args):
    """实采：联网采集 → 统计 → 图表 → 报告。"""
    if not (os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")):
        print("⚠️  未检测到 HTTPS_PROXY / HTTP_PROXY。")
        print("    外网不通时请先配置代理（本工具不含任何内置代理）：")
        print("      export HTTPS_PROXY=http://127.0.0.1:你的端口")
        print("      export HTTP_PROXY=http://127.0.0.1:你的端口")
        print()
    subs = [s.strip() for s in args.subreddits.split(",") if s.strip()]
    print(f"品类调研：{args.keyword}")
    print(f"  subreddits: {subs}")
    print(f"  输出目录: {args.out}")
    print()
    import collect
    collect.collect(args.keyword, subs, args.limit, args.queries, args.out)
    run_from_data(os.path.join(args.out, "data.json"), args.out)
    print()
    print("=" * 52)
    print(f"✅ 完成！报告 {args.out}/report.md，图表 {args.out}/charts/")
    print(f"   原始数据 {args.out}/data.json —— 可再用任意 LLM 做提炼（痛点聚类/机会矩阵）")


def main():
    p = argparse.ArgumentParser(
        description="Reddit 品类调研 Skills：一个品类词 → 消费者原话 → 统计/图表/报告")
    p.add_argument("keyword", nargs="?", help="品类关键词（英文），如 'cat food'；或写 demo")
    p.add_argument("--subreddits", default="BuyItForLife,Frugal,AskReddit",
                   help="逗号分隔的相关社区（强烈建议换成该品类自己的社区）")
    p.add_argument("--limit", type=int, default=15, help="每个社区每个查询拉取帖子数（默认 15）")
    p.add_argument("--queries", type=int, default=5, help="行业侧搜索角度数（默认 5）")
    p.add_argument("--out", default="output", help="输出目录（默认 ./output）")
    args = p.parse_args()

    if args.keyword == "demo":
        cmd_demo(args.out)
    elif not args.keyword:
        p.print_help()
        print("\n提示：先跑 `python run.py demo` 验证环境（不联网）。")
    else:
        cmd_live(args)


if __name__ == "__main__":
    main()
