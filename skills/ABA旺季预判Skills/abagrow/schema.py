"""数据准备：把 ABA 热搜词周报 CSV 读进 DuckDB，只留 5 列。

两个必须知道的口径：
1. ABA 导出的 CSV **第一行不是表头**，是一行 `Reporting Range=...` 元数据 → 读的时候 skip=1。
2. 20 GB 的文件不要整列读进来 → 用 DuckDB 的列裁剪，只 SELECT 需要的那 5 列。
"""
from __future__ import annotations

import os
import re

WEEK_RE = re.compile(r"(\d{4})_(\d{2})_(\d{2})")

# ABA Top Search Terms 周报的全部列（显式声明，避免 DuckDB 自动 sniff 失败）
COLMAP = """{'Search Frequency Rank': 'INTEGER', 'Search Term': 'VARCHAR',
 'Top Clicked Brand #1': 'VARCHAR', 'Top Clicked Brands #2': 'VARCHAR', 'Top Clicked Brands #3': 'VARCHAR',
 'Top Clicked Category #1': 'VARCHAR', 'Top Clicked Category #2': 'VARCHAR', 'Top Clicked Category #3': 'VARCHAR',
 'Top Clicked Product #1: ASIN': 'VARCHAR', 'Top Clicked Product #1: Product Title': 'VARCHAR',
 'Top Clicked Product #1: Click Share': 'VARCHAR', 'Top Clicked Product #1: Conversion Share': 'VARCHAR',
 'Top Clicked Product #2: ASIN': 'VARCHAR', 'Top Clicked Product #2: Product Title': 'VARCHAR',
 'Top Clicked Product #2: Click Share': 'VARCHAR', 'Top Clicked Product #2: Conversion Share': 'VARCHAR',
 'Top Clicked Product #3: ASIN': 'VARCHAR', 'Top Clicked Product #3: Product Title': 'VARCHAR',
 'Top Clicked Product #3: Click Share': 'VARCHAR', 'Top Clicked Product #3: Conversion Share': 'VARCHAR',
 'Reporting Date': 'VARCHAR'}"""


def week_files(csv_dir: str, pattern: str = "US_Top_Search_Terms_Simple_Week_{week}.csv",
               week_from: str | None = None, week_to: str | None = None):
    """返回 [(week, path)]，按周升序。week 形如 2025_11_08。"""
    if not os.path.isdir(csv_dir):
        raise SystemExit(f"找不到目录：{csv_dir}")
    out = []
    for name in sorted(os.listdir(csv_dir)):
        if not name.lower().endswith(".csv"):
            continue
        m = WEEK_RE.search(name)
        if not m:
            continue
        week = "_".join(m.groups())
        if week_from and week < week_from:
            continue
        if week_to and week > week_to:
            continue
        out.append((week, os.path.join(csv_dir, name)))
    out.sort()
    if not out:
        raise SystemExit(f"目录里没找到带 YYYY_MM_DD 的 CSV：{csv_dir}")
    return out


def label_of(week: str) -> str:
    """2025_11_08 → 11/08"""
    parts = week.split("_")
    return f"{parts[1]}/{parts[2]}" if len(parts) == 3 else week


def connect(threads: int = 4, memory: str = "6GB", temp_dir: str | None = None):
    import duckdb

    con = duckdb.connect()
    con.execute(f"PRAGMA threads={int(threads)}")
    con.execute("SET preserve_insertion_order=false")
    con.execute(f"SET memory_limit='{memory}'")
    if temp_dir:
        os.makedirs(temp_dir, exist_ok=True)
        con.execute(f"SET temp_directory='{temp_dir}'")
    return con


def _ph(i: int) -> str:
    """read_csv(header=false) 的匿名列名：column00 / column01 …"""
    return f"column{i:02d}"


def detect_layout(path: str):
    """识别表头 → {"skip": 数据起始行, "rank"/"term"/"a1".."a3": 实际列位置}。

    中文后台导出的周报列名被整段翻译（搜索频率排名 / 点击量第1的商品：ASIN），
    按英文名读会 BinderException。这里先认位置，再在 SQL 里改名成 rank/term/a1..a3。
    认不出来返回 None（调用方回退到原来的英文读法）。
    """
    import csv
    head, skip = None, 1
    for enc in ("utf-8-sig", "gb18030", "utf-16"):
        try:
            with open(path, encoding=enc, newline="") as f:
                rd = csv.reader(f)
                rows = []
                for _ in range(3):
                    try:
                        rows.append(next(rd))
                    except StopIteration:
                        break
            if rows and any(rows):
                hi = max(range(len(rows)), key=lambda i: len(rows[i]))
                head, skip = [h.strip() for h in rows[hi]], hi + 1
                break
        except (UnicodeDecodeError, UnicodeError):
            continue
    if not head:
        return None
    low = [h.lower() for h in head]
    rank = [i for i, h in enumerate(low) if "frequency rank" in h or "排名" in h]
    term = [i for i, h in enumerate(low) if h == "search term" or "搜索词" in h]
    asin = [i for i, h in enumerate(low) if "asin" in h]
    if not (rank and term and len(asin) >= 3):
        return None
    out = {"skip": skip, "rank": rank[0], "term": term[0]}
    for n in (1, 2, 3):
        out[f"a{n}"] = asin[n - 1]
    return out


def _select(week: str, path: str) -> str:
    if path.lower().endswith(".parquet"):
        return f"""SELECT rank, term, a1, a2, a3, '{week}' AS wk FROM read_parquet('{path}')"""
    lay = detect_layout(path)
    if lay:
        return f"""SELECT TRY_CAST({_ph(lay['rank'])} AS INTEGER) AS rank,
      {_ph(lay['term'])} AS term,
      {_ph(lay['a1'])} AS a1, {_ph(lay['a2'])} AS a2, {_ph(lay['a3'])} AS a3,
      '{week}' AS wk
      FROM read_csv('{path}', skip={lay['skip']}, header=false)"""
    return f"""SELECT "Search Frequency Rank" AS rank, "Search Term" AS term,
      "Top Clicked Product #1: ASIN" AS a1, "Top Clicked Product #2: ASIN" AS a2,
      "Top Clicked Product #3: ASIN" AS a3, '{week}' AS wk
      FROM read_csv('{path}', header=true, skip=1, columns={COLMAP}, ignore_errors=true)"""


def load(con, files, verbose: bool = True) -> list[str]:
    """把周文件读成一张 aba 表（rank, term, a1, a2, a3, wk），返回周列表。"""
    parts, weeks = [], []
    for week, path in files:
        parts.append(_select(week, path))
        weeks.append(week)
        if verbose:
            print(f"  读入 {week}", flush=True)
    con.execute("CREATE OR REPLACE TABLE aba AS " + " UNION ALL ".join(parts))
    if verbose:
        n = con.execute("SELECT count(*) FROM aba").fetchone()[0]
        print(f"  合计 {n:,} 行 / {len(weeks)} 周", flush=True)
    return weeks


def build_cache(con, files, cache_dir: str, verbose: bool = True) -> list[tuple[str, str]]:
    """把每周转成 parquet 缓存；返回可供 load() 使用的 [(week, parquet_path)]。"""
    os.makedirs(cache_dir, exist_ok=True)
    out = []
    for week, path in files:
        pq = os.path.join(cache_dir, f"{week}.parquet")
        con.execute(f"COPY ({_select(week, path)}) TO '{pq}' (FORMAT PARQUET)")
        out.append((week, pq))
        if verbose:
            print(f"  缓存 {week} → {os.path.basename(pq)}", flush=True)
    return out
