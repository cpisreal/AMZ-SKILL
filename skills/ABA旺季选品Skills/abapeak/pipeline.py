# -*- coding: utf-8 -*-
"""主流水线：一个方向词 → 产品机会报告。

    种子词 → ① 全量扫词 → ② 过滤噪音 → ③ 产品实体聚类 → ④ 六维度体检 → ⑤ 深挖（ASIN/品牌/类目）

每一步的口径分别落在 roots.py / cluster.py / rhythm.py / schema.py，
本文件只负责把它们串起来并汇总统计。
"""
from __future__ import annotations

import glob
import os
import re
import sys
import time
from collections import defaultdict

from . import schema
from .roots import build_pattern

WEEK_RE = re.compile(r"(\d{4})_(\d{2})_(\d{2})")


def week_of(path: str) -> str:
    m = WEEK_RE.search(os.path.basename(path))
    if not m:
        raise ValueError(f"文件名里找不到周次（期望 YYYY_MM_DD）：{path}")
    return "_".join(m.groups())


def label_of(week: str) -> str:
    return week[5:].replace("_", "/")


def list_weeks(csv_dir, pattern="US_Top_Search_Terms_Simple_Week_{week}.csv",
               week_from=None, week_to=None):
    files = sorted(glob.glob(os.path.join(os.path.expanduser(csv_dir),
                                          pattern.replace("{week}", "*"))))
    if not files:
        # 中文后台导出的文件名是 US_热门搜索词_简单_Week_YYYY_MM_DD.csv，
        # 英文 pattern 匹配不到 → 退化成「目录里所有 CSV，靠文件名里的日期认周」。
        files = sorted(glob.glob(os.path.join(os.path.expanduser(csv_dir), "*.csv")))
    out = []
    for f in files:
        try:
            w = week_of(f)
        except ValueError:
            continue
        if week_from and w < week_from:
            continue
        if week_to and w > week_to:
            continue
        out.append((w, f))
    return out


def _connect(threads=4, mem="6GB", cache_dir=None):
    import duckdb
    con = duckdb.connect()
    con.execute(f"SET threads={threads}")
    con.execute(f"SET memory_limit='{mem}'")
    if cache_dir:
        con.execute(f"SET temp_directory='{os.path.expanduser(cache_dir)}'")
    return con


def source_expr(week, csv_path, cache_dir=None):
    """有 parquet 缓存就优先用（亚秒级）。返回 (sql_from, params)。"""
    if cache_dir:
        pq = os.path.join(os.path.expanduser(cache_dir), f"{week}.parquet")
        if os.path.exists(pq):
            return "read_parquet(?)", [pq]
    lay = schema.detect_layout(csv_path)
    if lay:
        sel = ", ".join(
            (f"TRY_CAST({schema.col(pos)} AS BIGINT) AS {schema.q(name)}" if name == schema.COL_RANK
             else f"{schema.col(pos)} AS {schema.q(name)}")
            for name, pos in lay["map"].items())
        return (f"(SELECT {sel} FROM read_csv(?, skip={lay['skip']}, header=false))",
                [csv_path])
    return "read_csv_auto(?, skip=1, header=true)", [csv_path]


def build_cache(csv_dir, cache_dir, pattern="US_Top_Search_Terms_Simple_Week_{week}.csv",
                week_from=None, week_to=None, verbose=True):
    """把周报转成 parquet 缓存：只保留需要的列，体积/耗时都降一个量级。"""
    import duckdb
    os.makedirs(os.path.expanduser(cache_dir), exist_ok=True)
    con = duckdb.connect()
    con.execute("SET threads=4")
    con.execute("SET memory_limit='6GB'")
    weeks = list_weeks(csv_dir, pattern, week_from, week_to)
    made = []
    for w, f in weeks:
        dst = os.path.join(os.path.expanduser(cache_dir), f"{w}.parquet")
        if os.path.exists(dst):
            if verbose:
                print(f"  跳过（已存在）{w}", file=sys.stderr)
            continue
        cols = schema.select_list(schema.COLS_LIGHT + schema.COLS_DEEP[len(schema.COLS_LIGHT):])
        t = time.time()
        src, params = source_expr(w, f, None)
        con.execute(f"COPY (SELECT {cols} FROM {src}) "
                    f"TO '{dst}' (FORMAT PARQUET, COMPRESSION ZSTD)", params)
        made.append(dst)
        if verbose:
            print(f"  {w} → {os.path.basename(dst)}  "
                  f"{os.path.getsize(dst)/1e6:.0f}MB  {time.time()-t:.0f}s", file=sys.stderr)
    return made


def scan(csv_dir, pack, pattern="US_Top_Search_Terms_Simple_Week_{week}.csv",
         week_from=None, week_to=None, valid_rank=5000, threads=4, cache_dir=None,
         mode="auto", verbose=True):
    """① 扫词 ② 过滤 ③ 聚类 —— 一次遍历出全部统计。"""
    weeks_files = list_weeks(csv_dir, pattern, week_from, week_to)
    if not weeks_files:
        raise SystemExit("没找到 ABA 周报 CSV：检查 --csv-dir / --pattern / --week-from/to")

    rx = build_pattern(pack["roots"], mode)
    from .cluster import Classifier
    clf = Classifier(pack)

    con = _connect(threads, cache_dir=cache_dir)
    weeks, grand = [], {}
    valid = {}
    unique_terms = set()
    total_records = 0
    clus = defaultdict(lambda: {"week": defaultdict(int), "terms": set()})

    t0 = time.time()
    for w, f in weeks_files:
        src, params = source_expr(w, f, cache_dir)
        rows = con.execute(
            f'SELECT {schema.q(schema.COL_TERM)}, {schema.q(schema.COL_RANK)} '
            f'FROM {src} WHERE regexp_matches(lower({schema.q(schema.COL_TERM)}), ?)',
            params + [rx]).fetchall()
        weeks.append(w)
        grand[w] = len(rows)
        total_records += len(rows)
        for t, r in rows:
            unique_terms.add(t)
            try:
                r = int(r)
            except (TypeError, ValueError):
                continue
            if r <= valid_rank and (t not in valid or r < valid[t]):
                valid[t] = r
            p = clf(t)
            if p:
                clus[p]["week"][w] += 1
                clus[p]["terms"].add(t)
        if verbose:
            print(f"  {w}  {len(rows):>8,} 条  ({time.time()-t0:.0f}s)", file=sys.stderr, flush=True)

    products = []
    for name, d in clus.items():
        products.append({
            "product": name,
            "total_terms": sum(d["week"].values()),
            "unique_terms": len(d["terms"]),
            "week_terms": dict(d["week"]),
        })
    products.sort(key=lambda x: -x["total_terms"])

    return {
        "pack": pack.get("name"),
        "label": pack.get("label"),
        "roots": pack["roots"],
        "roots_mode": mode,
        "weeks": weeks,
        "week_records": grand,
        "total_records": total_records,      # 12 周记录数之和（含同词多周重复）
        "unique_terms": len(unique_terms),   # 去重词数 ← 「有效信号占比」的分母
        "valid_terms": len(valid),           # rank<=N 的去重词数
        "valid_rank": valid_rank,
        "products": products,
        "_terms": {n: sorted(d["terms"]) for n, d in clus.items()},
    }


def deep(csv_dir, pack, product=None, pattern="US_Top_Search_Terms_Simple_Week_{week}.csv",
         week_from=None, week_to=None, threads=4, cache_dir=None, top_asin=20,
         top_brand=10, top_cat=6, mode="auto", verbose=True):
    """⑤ 深挖：ASIN 反查 + 品牌格局 + 类目分布。"""
    weeks_files = list_weeks(csv_dir, pattern, week_from, week_to)
    rx = build_pattern(pack["roots"], mode)
    from .cluster import Classifier
    clf = Classifier(pack)

    con = _connect(threads, cache_dir=cache_dir)
    cols = [schema.COL_TERM] + [
        c.format(i=i) for i in (1, 2, 3) for c in (schema.COL_PRODUCT, schema.COL_TITLE)
    ] + [schema.COL_BRAND[i] for i in (1, 2, 3)] + [schema.COL_CAT[i] for i in (1, 2)]
    sel = schema.select_list(cols)

    agg = defaultdict(lambda: {"asins": defaultdict(int), "brands": defaultdict(int),
                               "cats": defaultdict(int), "titles": {}, "week": defaultdict(int),
                               "terms": set()})
    t0 = time.time()
    for w, f in weeks_files:
        src, params = source_expr(w, f, cache_dir)
        rows = con.execute(
            f"SELECT {sel} FROM {src} "
            f"WHERE regexp_matches(lower({schema.q(schema.COL_TERM)}), ?)",
            params + [rx]).fetchall()
        for row in rows:
            t = row[0]
            p = clf(t)
            if not p or (product and p != product):
                continue
            a = row[1:7]
            b = row[7:10]
            c = row[10:12]
            agg[p]["week"][w] += 1
            agg[p]["terms"].add(t)
            for i in (0, 2, 4):
                asin, title = a[i], a[i + 1]
                if asin:
                    agg[p]["asins"][asin] += 1
                    if asin not in agg[p]["titles"] and title:
                        agg[p]["titles"][asin] = str(title)[:140]
            for x in b:
                if x:
                    agg[p]["brands"][x] += 1
            for x in c:
                if x:
                    agg[p]["cats"][x] += 1
        if verbose:
            print(f"  {w} done ({time.time()-t0:.0f}s)", file=sys.stderr, flush=True)

    out = {}
    for p, d in agg.items():
        tot = sum(d["asins"].values()) or 1
        top = sorted(d["asins"].items(), key=lambda kv: -kv[1])[:top_asin]
        # 头部份额 = 前 3 个 ASIN 的点击次数 / 全部
        head3 = sum(c for _, c in sorted(d["asins"].items(), key=lambda kv: -kv[1])[:3])
        out[p] = {
            "total_terms": sum(d["week"].values()),
            "unique_terms": len(d["terms"]),
            "week_terms": dict(d["week"]),
            "top_asins": [{"asin": a, "count": c, "title": d["titles"].get(a, "")} for a, c in top],
            "top_brands": sorted(d["brands"].items(), key=lambda kv: -kv[1])[:top_brand],
            "top_cats": sorted(d["cats"].items(), key=lambda kv: -kv[1])[:top_cat],
            "head3_share": round(head3 / tot * 100, 1),
            "n_asins": len(d["asins"]),
        }
    return out
