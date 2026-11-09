# -*- coding: utf-8 -*-
"""第 1 步：用 DuckDB 把 ABA 热搜词报告装进去。

为什么要 DuckDB：一周一个 CSV 就 270 万行、1.3–2GB，十二周 3200 万行。
Excel 打开直接死机，pandas 读也吃满内存。DuckDB 是列式数据库，本地一个文件就能跑，查 270 万行是秒级。

🔴 坑一：ABA 的 CSV 第一行不是表头，是元数据 `Reporting Range=...`，真正的表头在第二行。
        不 skip 掉这一行，整列错位、后面命中全废。
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import duckdb

from .schema import detect_columns, parse_reporting_range

STD_COLS = ["term", "rank", "asin1", "asin2", "asin3", "click1", "click2", "click3",
            "conv1", "conv2", "conv3", "week", "src_file"]


def _first_line(p: Path) -> str:
    with open(p, "r", encoding="utf-8-sig", errors="replace") as f:
        return f.readline().rstrip("\n").rstrip("\r")


def _sample_rows(p: Path, n=200) -> tuple[list[str], list[dict]]:
    """跳过第一行元数据，取表头 + 少量样本行（用于兜底列识别）"""
    with open(p, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
        f.readline()                      # ← 丢掉元数据行
        rd = csv.reader(f)
        try:
            headers = next(rd)
        except StopIteration:
            return [], []
        rows = []
        for i, r in enumerate(rd):
            if i >= n:
                break
            rows.append(dict(zip(headers, r)))
    return headers, rows


def discover(aba_dir: Path) -> list[Path]:
    files = sorted([p for p in aba_dir.rglob("*") if p.suffix.lower() in (".csv", ".txt")])
    return [p for p in files if p.stat().st_size > 0]


def load(aba_dir: Path, db_path: Path, rebuild: bool = False, verbose: bool = True) -> dict:
    files = discover(aba_dir)
    if not files:
        raise SystemExit(f"❌ 在 {aba_dir} 里没找到 ABA 的 CSV 文件（.csv / .txt）")

    con = duckdb.connect(str(db_path))
    con.execute("PRAGMA threads=4")
    if rebuild:
        con.execute("DROP TABLE IF EXISTS aba")
        con.execute("DROP TABLE IF EXISTS aba_meta")

    con.execute("""CREATE TABLE IF NOT EXISTS aba
        (term VARCHAR, rank BIGINT,
         asin1 VARCHAR, asin2 VARCHAR, asin3 VARCHAR,
         click1 VARCHAR, click2 VARCHAR, click3 VARCHAR,
         conv1  VARCHAR, conv2  VARCHAR, conv3  VARCHAR,
         week VARCHAR, src_file VARCHAR)""")
    con.execute("CREATE TABLE IF NOT EXISTS aba_meta (src_file VARCHAR, week VARCHAR, mapping VARCHAR)")

    done = {r[0] for r in con.execute("SELECT DISTINCT src_file FROM aba").fetchall()}
    report = []

    for p in files:
        if p.name in done and not rebuild:
            if verbose:
                print(f"  ⏭  {p.name} 已在库里，跳过")
            continue

        first = _first_line(p)
        start, end = parse_reporting_range(first)
        week = end or p.stem          # 用报告区间的结束日当「周」标签

        headers, sample = _sample_rows(p)
        if not headers:
            print(f"  ⚠️  {p.name} 读不出表头，跳过")
            continue
        m = detect_columns(headers, sample)
        if not m["term"] or not m["asin1"]:
            print(f"  ⚠️  {p.name} 认不出「搜索词 / ASIN」列，跳过。表头前几列：{headers[:6]}")
            continue

        def q(name):
            return '"' + name.replace('"', '""') + '"'

        def sel(key, cast):
            col = m.get(key)
            return f"CAST({q(col)} AS {cast})" if col else "CAST(NULL AS " + cast + ")"

        sql = f"""
        INSERT INTO aba
        SELECT {sel('term','VARCHAR')}   AS term,
               {sel('rank','BIGINT')}    AS rank,
               {sel('asin1','VARCHAR')}  AS asin1,
               {sel('asin2','VARCHAR')}  AS asin2,
               {sel('asin3','VARCHAR')}  AS asin3,
               CAST({sel('click1','VARCHAR')} AS VARCHAR) AS click1,
               CAST({sel('click2','VARCHAR')} AS VARCHAR) AS click2,
               CAST({sel('click3','VARCHAR')} AS VARCHAR) AS click3,
               CAST({sel('conv1','VARCHAR')}  AS VARCHAR) AS conv1,
               CAST({sel('conv2','VARCHAR')}  AS VARCHAR) AS conv2,
               CAST({sel('conv3','VARCHAR')}  AS VARCHAR) AS conv3,
               '{week}' AS week, '{p.name}' AS src_file
        FROM read_csv(?, header=true, skip=1, ignore_errors=true, sample_size=20000)
        """
        try:
            con.execute(sql, [str(p)])
        except Exception as e:                     # noqa: BLE001
            print(f"  ⚠️  {p.name} 导入失败：{str(e)[:200]}")
            continue

        n = con.execute("SELECT count(*) FROM aba WHERE src_file=?", [p.name]).fetchone()[0]
        con.execute("INSERT INTO aba_meta VALUES (?,?,?)",
                    [p.name, week, str({k: v for k, v in m.items() if v})])
        report.append({"file": p.name, "week": week, "rows": n})
        if verbose:
            print(f"  ✅ {p.name}  区间 {start}~{end}  → 周标签 {week}  {n:,} 行")

    total = con.execute("SELECT count(*) FROM aba").fetchone()[0]
    weeks = con.execute("SELECT week, count(*) FROM aba GROUP BY 1 ORDER BY 1").fetchall()
    if verbose:
        print(f"\n  📦 库内合计 {total:,} 行 / {len(weeks)} 周")
        for w, c in weeks:
            print(f"     {w}  {c:,} 行")
    info = {"db": str(db_path), "rows": total, "weeks": [w for w, _ in weeks],
            "files": report, "mapping": con.execute(
                "SELECT src_file, week, mapping FROM aba_meta").fetchall()}
    con.close()
    return info
