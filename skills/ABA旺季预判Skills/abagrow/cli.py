"""命令行：demo / cache / all。"""
from __future__ import annotations

import argparse
import os
import sys
import time

from . import pipeline, report, schema


def _run_all(con, files, args, rules, label=None):
    t0 = time.time()
    weeks = schema.load(con, files, verbose=args.verbose)
    print(f"[1/5] 数据准备完成（{len(weeks)} 周 / {time.time()-t0:.0f}s）", flush=True)

    seeds, n_hit = pipeline.find_seeds(con, args.must, top=args.top, verbose=args.verbose)
    print(f"[2/5] 种子 ASIN：{len(seeds)} 个（命中池 {n_hit:,}）", flush=True)
    if not seeds:
        raise SystemExit("没找到种子 ASIN —— 检查 --must 品类词是否写对（要全部同时命中）")

    n_rel = pipeline.find_related(con, verbose=args.verbose)
    print(f"[3/5] 关联词：{n_rel:,} 个去重", flush=True)

    root_rows, attr_rows = pipeline.build_attributes(con, rules, weeks, verbose=args.verbose)
    print(f"[4/5] 词根归属性完成：{len(attr_rows)} 个属性 / {len(root_rows)} 个词根", flush=True)

    accel_rows = pipeline.build_accel(root_rows, attr_rows, weeks)
    print(f"[5/5] 加速度与三个时间点完成", flush=True)

    related_terms = [r[0] for r in con.execute("SELECT term FROM related ORDER BY term").fetchall()]
    labels = report.write_tables(args.out, seeds, n_hit, related_terms, weeks,
                                 root_rows, attr_rows, accel_rows)
    meta = {"label": label or rules.get("label", "品类"), "must_terms": args.must,
            "seeds": seeds, "n_asin_hit": n_hit, "n_related": n_rel}
    path = report.write_report(args.out, meta, weeks, root_rows, attr_rows, accel_rows, labels)

    print(f"\n已输出到 {os.path.abspath(args.out)}")
    for f in ("1_种子ASIN.csv", "2_关联词表.csv", "3_属性周矩阵.csv", "4_加速度表.csv", "报告.md"):
        print(f"  - {f}")
    print(f"  用时 {time.time()-t0:.0f}s")
    return path


def cmd_demo(args):
    from demo.make_demo import build_demo

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    demo_dir = os.path.join(here, "demo", "data")
    out = args.out or os.path.join(here, "demo", "out")
    build_demo(demo_dir)
    rules = pipeline.load_rules(os.path.join(here, "demo", "demo_rules.json"))
    args.must = ["winter", "coat"]
    args.top = 10
    args.out = out
    con = schema.connect(threads=args.threads)
    files = schema.week_files(demo_dir)
    return _run_all(con, files, args, rules, label="演示品类 Winter Coat")


def cmd_cache(args):
    con = schema.connect(threads=args.threads)
    files = schema.week_files(args.csv_dir, args.pattern, args.week_from, args.week_to)
    print(f"发现 {len(files)} 个周文件，开始转 parquet →", args.cache_dir, flush=True)
    schema.build_cache(con, files, args.cache_dir)
    print("完成。下次跑 all 时同时给 --csv-dir 和 --cache-dir，会自动走缓存。")


def cmd_all(args):
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rules = pipeline.load_rules(args.rules or os.path.join(here, "rules", "pajama_winter.json"))
    if not args.must:
        raise SystemExit("必须给 --must（品类词，逗号分隔，全部同时命中），如 --must christmas,pajama")
    args.must = [t.strip() for t in args.must.split(",") if t.strip()]
    con = schema.connect(threads=args.threads)
    files = schema.week_files(args.csv_dir, args.pattern, args.week_from, args.week_to)
    if args.cache_dir and os.path.isdir(args.cache_dir) and any(
            f.endswith(".parquet") for f in os.listdir(args.cache_dir)):
        print("用 parquet 缓存读", flush=True)
        files = [(w, os.path.join(args.cache_dir, f"{w}.parquet")) for w, _ in files
                 if os.path.exists(os.path.join(args.cache_dir, f"{w}.parquet"))]
        con.execute("SET preserve_insertion_order=false")
    return _run_all(con, files, args, rules, label=rules.get("label"))


def build_parser():
    p = argparse.ArgumentParser(
        prog="run.py",
        description="ABA 旺季预判 Skills —— 一个品类什么时候起量、见顶、该撤")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(s):
        s.add_argument("--threads", type=int, default=4)
        s.add_argument("--quiet", dest="verbose", action="store_false")
        s.set_defaults(verbose=True)

    s = sub.add_parser("demo", help="零依赖试跑（自动造 12 周演示数据）")
    s.add_argument("--out", default=None)
    common(s)
    s.set_defaults(func=cmd_demo)

    s = sub.add_parser("cache", help="把 CSV 转成 parquet 缓存（第 2 遍快一个量级）")
    s.add_argument("--csv-dir", required=True)
    s.add_argument("--pattern", default="US_Top_Search_Terms_Simple_Week_{week}.csv")
    s.add_argument("--cache-dir", required=True)
    s.add_argument("--week-from", default=None)
    s.add_argument("--week-to", default=None)
    common(s)
    s.set_defaults(func=cmd_cache)

    s = sub.add_parser("all", help="跑完整五步，出全部结果")
    s.add_argument("--csv-dir", required=True)
    s.add_argument("--pattern", default="US_Top_Search_Terms_Simple_Week_{week}.csv")
    s.add_argument("--must", required=True, help="品类词，逗号分隔，必须全部同时命中")
    s.add_argument("--rules", default=None)
    s.add_argument("--out", default="./out")
    s.add_argument("--top", type=int, default=10)
    s.add_argument("--cache-dir", default=None)
    s.add_argument("--week-from", default=None)
    s.add_argument("--week-to", default=None)
    common(s)
    s.set_defaults(func=cmd_all)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
