#!/usr/bin/env python3
"""竞品库流水线 · 步骤 1–5：从一个自家 ASIN 出发，爬 BSR 榜 + 关键词搜索页，去重建库。

流程（对应文章里的 6 步）：
  1. 找关键词   —— 从 Listing 标题/类目出发（也可 --keywords 直接给）
  2. 拆核心词   —— 4–5 个（s--keywords 传入，或用 --auto-keywords 由 LLM 拆）
  3. 爬 BSR 榜  —— 自家 ASIN 所在的最细类目，爬前 N 页
  4. 爬竞品页面 —— 每个核心词爬前 P 页搜索结果
  5. 整理竞品库 —— 按 ASIN 去重，记录「来源 / 出现频次 / 最好位次 / 是否广告」

用法：
  python3 build_competitor_lib.py --asin B0BWHZJHPL \
      --keywords "countertop ice maker,nugget ice maker,portable ice maker,bullet ice maker,ice maker machine" \
      --bsr-pages 2 --search-pages 5 --enrich 120 --out out
"""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from urllib.parse import quote_plus

from crawl_amazon import (ThrottledSession, Blocked, parse_search, parse_bsr,
                          parse_detail, extract_bsr_node)


def log(*a):
    print(*a, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asin", required=True, help="自家产品 ASIN（输入）")
    ap.add_argument("--keywords", required=True,
                    help="4-5 个核心关键词，逗号分隔（步骤 2 的产出）")
    ap.add_argument("--bsr-pages", type=int, default=2)
    ap.add_argument("--search-pages", type=int, default=5)
    ap.add_argument("--enrich", type=int, default=120,
                    help="给前 N 个候选爬详情页（补品牌/类目/五点）；0=不补")
    ap.add_argument("--min-delay", type=float, default=5.0)
    ap.add_argument("--max-delay", type=float, default=9.0)
    ap.add_argument("--max-requests", type=int, default=400)
    ap.add_argument("--out", default="out")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    S = ThrottledSession(cache_dir=os.path.join(args.out, "pages"),
                         min_delay=args.min_delay, max_delay=args.max_delay,
                         max_requests=args.max_requests)

    stats = {"keywords": keywords, "asin": args.asin}
    pool = {}                       # asin -> record
    own_asin = args.asin.upper()

    def add(asin, **kw):
        asin = asin.upper()
        if len(asin) != 10 or asin == own_asin:
            return
        r = pool.setdefault(asin, {"asin": asin, "sources": [], "keywords": [],
                                   "best_pos": 999, "n_hits": 0, "sponsored": False,
                                   "title": None, "price": None, "rating": None})
        r["n_hits"] += 1
        r["sources"].append(kw.pop("source"))
        if kw.get("keyword"):
            r["keywords"].append(kw.pop("keyword"))
        if kw.get("pos"):
            r["best_pos"] = min(r["best_pos"], kw.pop("pos"))
        if kw.pop("sponsored", False):
            r["sponsored"] = True
        if kw.get("title") and not r["title"]:
            r["title"] = kw["title"]
        for f in ("price", "rating"):
            if kw.get(f) and not r.get(f):
                r[f] = kw[f]

    # ---------- 步骤 3：自家详情 + BSR 榜 ----------
    log(f"[1/5] 自家 Listing + BSR 节点 · {own_asin}")
    html = S.get(f"https://www.amazon.com/dp/{own_asin}", label=f"自家详情 {own_asin}")
    own = parse_detail(html)
    node = extract_bsr_node(html)
    stats["own"] = own
    stats["bsr_node"] = node
    log(f"      {own.get('brand')} | {own.get('category')} | BSR 节点={node}")

    bsr_rows = []
    if node:
        for pg in range(1, args.bsr_pages + 1):
            url = f"https://www.amazon.com/gp/bestsellers/appliances/{node}/" + (f"?pg={pg}" if pg > 1 else "")
            h = S.get(url, label=f"BSR 榜 p{pg}")
            rows = parse_bsr(h)
            log(f"      BSR p{pg} → {len(rows)} 条")
            for x in rows:
                bsr_rows.append(x)
                add(x["asin"], source="bsr", rank_text=x.get("rank_text"), title=x.get("title"))
    stats["bsr_count"] = len({x["asin"] for x in bsr_rows})

    # ---------- 步骤 4：关键词搜索页 ----------
    log(f"[2/5] 搜索页 · {len(keywords)} 词 × {args.search_pages} 页")
    serp_rows = []
    for kw in keywords:
        for pg in range(1, args.search_pages + 1):
            url = f"https://www.amazon.com/s?k={quote_plus(kw)}" + (f"&page={pg}" if pg > 1 else "")
            try:
                h = S.get(url, label=f"搜索 '{kw}' p{pg}")
            except Blocked as e:
                log(f"      ⛔ 熔断：{e}；已抓数据保留在 {args.out}/")
                _dump(args.out, pool, stats, bsr_rows, serp_rows)
                sys.exit(2)
            rows = parse_search(h)
            log(f"      '{kw}' p{pg} → {len(rows)} 条")
            for x in rows:
                serp_rows.append({**x, "keyword": kw, "page": pg})
                add(x["asin"], source="search", keyword=kw, pos=x["pos"],
                    sponsored=x["sponsored"], title=x["title"],
                    price=x["price"], rating=x["rating"])
    stats["serp_cards"] = len(serp_rows)

    # ---------- 步骤 5a：去重后的候选池 ----------
    log(f"[3/5] 去重 → 候选池 {len(pool)} 个 ASIN（原始卡片 {len(serp_rows)} + BSR {len(bsr_rows)}）")
    stats["pool_size"] = len(pool)

    # 富集优先级：出现频次高 → 最好位次靠前 → BSR 命中优先
    order = sorted(pool.values(),
                   key=lambda r: (-r["n_hits"], r["best_pos"],
                                  0 if "bsr" in r["sources"] else 1))
    to_enrich = order[:args.enrich] if args.enrich else []

    # ---------- 步骤 5b：详情补全 ----------
    log(f"[4/5] 详情补全 · 前 {len(to_enrich)} 个")
    for i, r in enumerate(to_enrich, 1):
        try:
            h = S.get(f"https://www.amazon.com/dp/{r['asin']}",
                      label=f"[{i}/{len(to_enrich)}] 详情 {r['asin']}")
        except Blocked as e:
            log(f"      ⛔ 熔断：{e}；已抓数据保留")
            break
        except Exception as e:
            log(f"      ⚠️ {r['asin']} 失败：{e}")
            continue
        d = parse_detail(h)
        r["brand"] = d.get("brand")
        r["category"] = d.get("category")
        r["bullets"] = d.get("bullets")
        r["detail_title"] = d.get("title")
        r["price"] = r.get("price") or d.get("price")
        r["rating"] = r.get("rating") or d.get("rating")
        r["enriched"] = True

    _dump(args.out, pool, stats, bsr_rows, serp_rows)
    log(f"[5/5] 完成 · 请求 {S.n} 次 / 软验证 {S.soft_hits} 次 / 缓存命中 {S.cache_hits}")


def _dump(outdir, pool, stats, bsr_rows, serp_rows):
    lib = sorted(pool.values(), key=lambda r: (-r["n_hits"], r["best_pos"]))
    json.dump({"stats": stats, "competitors": lib},
              open(os.path.join(outdir, "competitors_raw.json"), "w"),
              ensure_ascii=False, indent=1)
    json.dump(bsr_rows, open(os.path.join(outdir, "bsr_raw.json"), "w"),
              ensure_ascii=False, indent=1)
    json.dump(serp_rows, open(os.path.join(outdir, "serp_raw.json"), "w"),
              ensure_ascii=False, indent=1)
    with open(os.path.join(outdir, "competitors_raw.csv"), "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["ASIN", "标题", "品牌", "类目", "价格", "评分", "出现频次",
                    "最好位次", "来源", "命中关键词", "是否广告", "已补详情"])
        for r in lib:
            w.writerow([r["asin"], r.get("detail_title") or r.get("title"), r.get("brand"),
                        r.get("category"), r.get("price"), r.get("rating"),
                        r["n_hits"], r["best_pos"], "|".join(sorted(set(r["sources"]))),
                        "|".join(sorted(set(r["keywords"]))), r["sponsored"],
                        r.get("enriched", False)])
    print(f"  → {outdir}/competitors_raw.json  ({len(lib)} 个候选)", flush=True)


if __name__ == "__main__":
    main()
