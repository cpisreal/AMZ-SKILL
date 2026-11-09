# -*- coding: utf-8 -*-
"""命令行入口：把 6 条口径串成一条命令。

    python run.py scan    --csv-dir ./aba --pack christmas
    python run.py rhythm  --csv-dir ./aba --pack christmas
    python run.py deep    --csv-dir ./aba --pack christmas
    python run.py report  --csv-dir ./aba --pack christmas --out 报告.xlsx
    python run.py all     --csv-dir ./aba --pack christmas --out ./out
    python run.py demo                           # 零依赖试跑
    python run.py explain --pack christmas       # 看口径实际效果
"""
from __future__ import annotations

import argparse
import os
import sys

from . import export, pipeline, roots as roots_mod
from .cluster import available_packs, classifier_for, load_pack


def _common(p):
    p.add_argument("--csv-dir", default="./aba", help="ABA 周报 CSV 所在目录")
    p.add_argument("--pattern", default="US_Top_Search_Terms_Simple_Week_{week}.csv")
    p.add_argument("--pack", default="christmas", help="规则包名或 JSON 路径")
    p.add_argument("--week-from", default=None, help="起始周 YYYY_MM_DD")
    p.add_argument("--week-to", default=None)
    p.add_argument("--valid-rank", type=int, default=5000, help="有效词阈值（默认 5000）")
    p.add_argument("--roots-mode", choices=["auto", "strict", "loose"], default="auto",
                   help="auto=长词根查左边界/短词根查两边（默认，推荐）；strict=一律两边（会剔掉 christmaslights 类连写词）；loose=不查边界，等价 LIKE，用来复现用 LIKE 算的数")
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--cache-dir", default=None, help="parquet 缓存目录（强烈建议）")
    p.add_argument("--quiet", action="store_true")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(prog="run.py", description="ABA 旺季选品分析 Skills")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("explain", help="看词根边界口径的实际效果（不读数据）")
    s.add_argument("--pack", default="christmas")
    s.add_argument("--roots", default=None, help="直接给词根，逗号分隔，覆盖规则包")

    s = sub.add_parser("packs", help="列出内置规则包")

    s = sub.add_parser("cache", help="把 CSV 转成 parquet 缓存（跑第 2 遍时快一个量级）")
    _common(s)
    s.add_argument("--out", required=True, help="缓存目录")

    for name, helptext in [("scan", "扫词 + 过滤 + 产品聚类"),
                           ("rhythm", "六维度节奏 + 加速度/词量峰"),
                           ("deep", "ASIN 反查 + 品牌 + 类目"),
                           ("report", "出报告（xlsx + markdown）"),
                           ("all", "一条命令跑完全部")]:
        s = sub.add_parser(name, help=helptext)
        _common(s)
        s.add_argument("--out", default="./out", help="输出文件或目录")
        s.add_argument("--top", type=int, default=20, help="取前 N 个产品")
        if name == "deep":
            s.add_argument("--product", default=None, help="只深挖某一个产品")

    s = sub.add_parser("demo", help="零依赖试跑（自动造样例数据）")
    s.add_argument("--out", default=None)

    a = ap.parse_args(argv)

    if a.cmd == "packs":
        print("内置规则包：")
        for n in available_packs():
            pk = load_pack(n)
            print(f"  {n:<12} {pk.get('label','')}   词根 {pk['roots']}"
                  f"   产品 {len(pk['products'])} 类")
        return 0

    if a.cmd == "explain":
        if a.roots:
            print(roots_mod.explain([x.strip() for x in a.roots.split(",") if x.strip()]))
            return 0
        pk = load_pack(a.pack)
        print(f"规则包 {pk.get('name')}（{pk.get('label')}）\n")
        print(roots_mod.explain(pk["roots"], mode="auto", samples=pk.get("_root_probes")))
        clf = classifier_for(a.pack)
        gate = roots_mod.make_matcher(pk["roots"], mode="auto")
        print(f"\n三道闸门串联抽样（顺序：词根边界 → 子类守卫 → 同形异义 → 首个命中）：")
        print(f"  {'判定':<12}{'词根闸门':<10}{'最终产品':<14}词")
        samples = pk.get("_explain_samples") or [
            "christmas tree", "christmas tree skirt", "christmas stocking",
            "christmas stocking stuffers", "christmas stockings for women",
            "thigh high stockings", "xmas ornament", "christmas lights",
            "omen decor", "garment steamer"]
        for t in samples:
            passed = gate(t)
            print(f"  {'✅ 留下' if passed else '⛔ 挡掉':<12}"
                  f"{'通过' if passed else '不通过':<10}{str(clf(t)):<14}{t}")
        print("\n" + (pk.get("_explain_note") or
                      "注意：`omen decor` 是被**词根闸门**挡掉的，不是聚类 —— "
                      "聚类只在通过词根闸门的词上运行。"))
        strictm = roots_mod.make_matcher(pk["roots"], mode="strict")
        loose = roots_mod.make_matcher(pk["roots"], mode="loose")
        compare = pk.get("_boundary_compare") or [
            "christmaslights", "christmastime", "3 ftchristmas tree",
            "boxmasters", "christmas tree"]
        print("\n三种口径对比（--roots-mode）：")
        print("  %-20s %-7s %-7s %-7s" % ("词", "auto", "strict", "loose"))
        for t in compare:
            print("  %-20s %-7s %-7s %-7s" % (
                t, "命中" if gate(t) else "挡掉",
                "命中" if strictm(t) else "挡掉", "命中" if loose(t) else "挡掉"))
        return 0

    if a.cmd == "demo":
        from demo.make_demo_aba import build_demo
        d = a.out or os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "demo", "aba")
        build_demo(d)
        a.csv_dir, a.out, a.pack = d, os.path.join(os.path.dirname(d), "out"), "christmas"
        a.pattern, a.week_from, a.week_to = "ABA_demo_week_{week}.csv", None, None
        a.valid_rank, a.threads, a.cache_dir, a.quiet, a.top = 5000, 4, None, False, 20
        a.roots_mode = "auto"
        a.cmd = "all"

    if a.cmd == "cache":
        pipeline.build_cache(a.csv_dir, a.out, a.pattern, a.week_from, a.week_to)
        print(f"\n缓存完成 → {a.out}")
        return 0

    pack = load_pack(a.pack)
    kw = dict(csv_dir=a.csv_dir, pack=pack, pattern=a.pattern,
              week_from=a.week_from, week_to=a.week_to, threads=a.threads,
              cache_dir=a.cache_dir, mode=a.roots_mode,
              verbose=not a.quiet)

    if a.cmd == "scan":
        r = pipeline.scan(valid_rank=a.valid_rank, **kw)
        print(f"\n周数 {len(r['weeks'])}｜记录 {r['total_records']:,}｜"
              f"去重词 {r['unique_terms']:,}｜有效词 {r['valid_terms']:,}｜"
              f"产品 {len(r['products'])}")
        print(f"\n{'产品':<16}{'12周词条':>10}{'去重':>8}")
        for p in r["products"][:a.top]:
            print(f"{p['product']:<16}{p['total_terms']:>10,}{p['unique_terms']:>8,}")
        export.to_json(r, a.out if a.out.endswith(".json") else a.out + ".json")
        print(f"\n已存 {a.out if a.out.endswith('.json') else a.out + '.json'}")
        return 0

    if a.cmd in ("rhythm", "report", "all"):
        sc = pipeline.scan(valid_rank=a.valid_rank, **kw)
        dr = None
        if a.cmd in ("report", "all"):
            dr = pipeline.deep(**kw, top_asin=20)
        rep = export.build_report(sc, dr, top_n=a.top)

        m = rep["market"]
        print(f"\n=== 大盘 ===")
        print(f"  记录 {rep['total_records']:,}　去重词 {rep['unique_terms']:,}　"
              f"有效词 {rep['valid_terms']:,}（{rep['valid_terms']/max(rep['unique_terms'],1)*100:.2f}%）")
        print(f"  加速度峰值 {m.get('acc_peak_week')} (+{m.get('acc_peak_v',0):,})")
        print(f"  词量顶点   {m.get('volume_peak_week')} ({m.get('volume_peak_v',0):,})")
        print(f"  → 进场信号比销量顶点早 {m.get('lead_weeks')} 周")

        from .rhythm import format_table
        print("\n=== 六维度 ===")
        print(format_table({p["product"]: p for p in rep["products"]}, rep["labels"]))

        if a.cmd == "rhythm":
            export.to_json(rep, a.out if a.out.endswith(".json") else a.out + ".json")
            print(f"\n已存 {a.out if a.out.endswith('.json') else a.out + '.json'}")
            return 0

        outdir = a.out
        if outdir.endswith((".xlsx", ".md")):
            outdir = os.path.dirname(outdir) or "."
        os.makedirs(outdir, exist_ok=True)
        stem = f"{rep['label'] or '旺季选品'}_机会报告".replace(" ", "")
        md = os.path.join(outdir, stem + ".md")
        xl = os.path.join(outdir, stem + ".xlsx")
        open(md, "w", encoding="utf-8").write(export.markdown(rep))
        export.to_xlsx(rep, xl)
        export.to_json(rep, os.path.join(outdir, stem + ".json"))
        print(f"\n已出报告：\n  {md}\n  {xl}\n  {os.path.join(outdir, stem + '.json')}")
        return 0

    if a.cmd == "deep":
        dr = pipeline.deep(**kw, product=a.product, top_asin=20)
        for p, d in sorted(dr.items(), key=lambda kv: -kv[1]["total_terms"]):
            print(f"\n【{p}】词条 {d['total_terms']:,}　ASIN {d['n_asins']}　"
                  f"头部3集中度 {d['head3_share']}%")
            print(f"  品牌：{', '.join(f'{b}({c:,})' for b, c in d['top_brands'][:5])}")
            print(f"  类目：{', '.join(f'{c}({n:,})' for c, n in d['top_cats'][:3])}")
            for x in d["top_asins"][:3]:
                print(f"    {x['asin']}  ×{x['count']:<5} {x['title'][:60]}")
        export.to_json(dr, a.out if a.out.endswith(".json") else a.out + ".json")
        print(f"\n已存 {a.out if a.out.endswith('.json') else a.out + '.json'}")
        return 0

    return 0
