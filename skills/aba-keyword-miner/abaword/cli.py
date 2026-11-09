# -*- coding: utf-8 -*-
"""ABA 自动词库 Skills —— 命令行入口：一条命令从几千万行原始数据跑到一张能用的词表。"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from . import s1_load, s2_match, s3_listing, s4_jev
from .export import export

BANNER = r"""
╭──────────────────────────────────────────────────────────────╮
│  ABA 自动词库 Skills                                          │
│  ABA 数据反向命中 ASIN  +  决策模型 Jev 打分   →   高相关词表   │
╰──────────────────────────────────────────────────────────────╯
"""


def _read_asins(v: str) -> list[str]:
    p = Path(v)
    if p.exists():
        raw = p.read_text(encoding="utf-8")
    else:
        raw = v
    out = []
    for line in raw.replace(",", "\n").splitlines():
        s = line.strip().strip('"').strip("'")
        if s and not s.startswith("#"):
            out.append(s.upper())
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="ABA 自动词库 Skills（ABA 反向命中 + Jev 打分）")
    g = ap.add_argument_group("数据")
    g.add_argument("--aba-dir", required=True, help="放 ABA 热搜词报告 CSV 的目录（可多个文件）")
    g.add_argument("--db", default="./aba.duckdb", help="DuckDB 库文件（复用可跳过重复导入）")
    g.add_argument("--rebuild", action="store_true", help="清库重建")

    g = ap.add_argument_group("选词")
    g.add_argument("--asins", required=True, help="竞品 ASIN：文件路径 或 逗号分隔")
    g.add_argument("--target", required=True, help="目标 ASIN（爬它的 Listing 当打分基准）")
    g.add_argument("--market", default="com", help="站点后缀：com / co.uk / de / co.jp …")
    g.add_argument("--proxy", default=None, help="抓 Listing 用的代理")
    g.add_argument("--listing-json", default=None, help="直接喂已抓好的 Listing JSON（跳过爬取）")
    g.add_argument("--max-words", type=int, default=0, help="最多处理多少个词（0=全部）")

    g = ap.add_argument_group("打分")
    g.add_argument("--provider", default="openrouter",
                   choices=["openrouter", "typesafe", "mock"],
                   help="openrouter=OpenRouter 的 Jev；typesafe=TypeSafe 直连；mock=无 key 试跑")
    g.add_argument("--api-key", default=None)
    g.add_argument("--batch", type=int, default=60, help="每批词数（本文用 60 作为安全值）")

    g = ap.add_argument_group("输出")
    g.add_argument("--out", default=None, help="输出 xlsx（默认 ./词表_<目标ASIN>.xlsx）")
    ap.add_argument("--json-out", default=None, help="同时存一份 JSON")
    args = ap.parse_args(argv)

    print(BANNER)
    t_all = time.time()
    steps = {}

    # ── 1 ─────────────────────────────────────────────────────────────
    print("【第 1 步】用 DuckDB 把 ABA 数据装进去")
    info = s1_load.load(Path(args.aba_dir), Path(args.db), rebuild=args.rebuild)
    steps["入库行数"] = info["rows"]
    steps["覆盖周数"] = len(info["weeks"])

    # ── 2 ─────────────────────────────────────────────────────────────
    asins = _read_asins(args.asins)
    print(f"\n【第 2 步】ASIN 反向命中搜索词（{len(asins)} 个竞品 ASIN）")
    print("   " + ", ".join(asins[:8]) + (" …" if len(asins) > 8 else ""))
    words, mstat = s2_match.reverse_match(args.db, asins)
    print(f"   扫描 {mstat['扫描词数']:,} 个词 / {mstat['周数']} 周 → 命中 {mstat['命中词数']:,} 个词")
    if mstat["未命中的ASIN"]:
        print(f"   ⚠️  这些 ASIN 一个词都没命中，检查是否写错或不在该站点：{mstat['未命中的ASIN']}")
    if not words:
        print("\n❌ 没有命中任何词。常见原因：ASIN 写错 / 报告站点不符 / ABA 文件没导入成功。")
        return 2
    if args.max_words:
        words = words[:args.max_words]
    steps.update({"竞品ASIN数": len(asins), "命中词数": len(words)})

    # ── 3 ─────────────────────────────────────────────────────────────
    print(f"\n【第 3 步】拿目标 ASIN 的 Listing 当打分基准")
    if args.listing_json:
        listing = s3_listing.load_local(Path(args.listing_json))[0]
        print(f"   ✅ 读本地 JSON：{listing.get('title', '')[:70]}")
    else:
        listing = s3_listing.fetch_listing(args.target, args.market, args.proxy)
        print(f"   ✅ {listing['title'][:70]}")
        print(f"      品牌 {listing.get('brand','?')} ｜ 类目 {listing.get('category','?')[:50]}")
        print(f"      五点 {len(listing.get('bullets',[]))} 条 ｜ 描述 {len(listing.get('description',''))} 字")
        w = s3_listing.currency_warning(listing)
        if w:
            print("   " + w)
    if not listing.get("title"):
        print("   ❌ Listing 标题为空，打分会失去基准。请检查是否被抓到验证码页。")
        return 3

    # ── 4 ─────────────────────────────────────────────────────────────
    print(f"\n【第 4 步】Jev 打分 + 分类（1–10 分 / 6 类词）")
    if args.provider == "mock":
        print("   ⚠️  当前是 mock 试跑模式：用规则近似打分，**不是 Jev**。验证流程用。")
    terms = [w["term"] for w in words]
    scored, sstat = s4_jev.score_all(terms, listing, args.provider, args.api_key, args.batch)
    by_term = {r["term"]: r for r in scored}

    rows = []
    for w in words:
        s = by_term.get(w["term"], {})
        rows.append({**w, **s})
    strong = sum(1 for r in rows if (r.get("related_score") or 0) >= 8)
    comp = sum(1 for r in rows if r.get("category_key") == "competitor_brand")
    print(f"   📊 强相关（≥8 分）{strong} 个 ｜ 竞品品牌词（可做否定）{comp} 个")
    print(f"   💰 输入 {sstat['输入token']:,} token ≈ ${sstat['估算成本USD']:.6f}")
    steps.update({"强相关≥8分": strong, "竞品品牌词": comp,
                  "Jev输入token": sstat["输入token"], "估算成本USD": sstat["估算成本USD"]})

    # ── 导出 ───────────────────────────────────────────────────────────
    out = Path(args.out) if args.out else Path(f"./词表_{args.target}.xlsx")
    summary = {**steps, "目标ASIN": args.target, "站点": args.market,
               "provider": args.provider, "每批词数": args.batch,
               "去重前词数": mstat["命中词数"], "未命中的ASIN": mstat["未命中的ASIN"]}
    export(rows, out, summary)
    print(f"\n✅ 词表已导出：{out.resolve()}")
    if args.json_out:
        Path(args.json_out).write_text(json.dumps({"rows": rows, "summary": summary},
                                                  ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"   附带 JSON：{Path(args.json_out).resolve()}")
    print(f"⏱  总耗时 {time.time()-t_all:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
