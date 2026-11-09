#!/usr/bin/env python3
"""竞品库流水线 · 一键跑完 6 步（建库 → 打分 → 导出）。

用法：
  python3 run_pipeline.py --asin B0BWHZJHPL \
      --keywords "countertop ice maker,nugget ice maker,portable ice maker,bullet ice maker,ice maker machine"

需要环境变量 TYPESAFE_API_KEY（Jev 打分用）。
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(cmd):
    print("\n$", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=HERE)
    if r.returncode != 0:
        sys.exit(f"步骤失败（exit {r.returncode}）：{' '.join(cmd)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asin", required=True)
    ap.add_argument("--keywords", required=True)
    ap.add_argument("--bsr-pages", type=int, default=2)
    ap.add_argument("--search-pages", type=int, default=5)
    ap.add_argument("--enrich", type=int, default=120)
    ap.add_argument("--min-delay", type=float, default=5.0)
    ap.add_argument("--max-delay", type=float, default=8.0)
    ap.add_argument("--out", default="out")
    a = ap.parse_args()

    py = sys.executable
    run([py, "build_competitor_lib.py", "--asin", a.asin, "--keywords", a.keywords,
         "--bsr-pages", str(a.bsr_pages), "--search-pages", str(a.search_pages),
         "--enrich", str(a.enrich), "--min-delay", str(a.min_delay),
         "--max-delay", str(a.max_delay), "--out", a.out])
    run([py, "score_competitors.py", "--lib", os.path.join(a.out, "competitors_raw.json"),
         "--keywords", a.keywords, "--out", a.out])
    run([py, "export_table.py", "--scored", os.path.join(a.out, "competitors_scored.json"),
         "--out", a.out])
    print("\n✅ 全流程完成 →", os.path.join(a.out, "竞品库.xlsx"))


if __name__ == "__main__":
    main()
