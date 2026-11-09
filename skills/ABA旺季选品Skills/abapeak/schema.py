# -*- coding: utf-8 -*-
"""ABA 周报的读取口径 —— 两个坑都在这里，别绕过去。

坑 1：**第一行不是表头，是 Reporting Range 元数据** → read_csv_auto 必须 `skip=1`。
      不写会得到一个叫 "Reporting Range" 的假列，且所有列名错位。

坑 2：品牌列名**单复数不一致** —— `Top Clicked Brand #1` 是单数，
      `Top Clicked Brands #2` / `#3` 是复数。写错直接 BinderException。

坑 3：单周文件 1.7–2.3 GB / ~290 万行。**必须列裁剪** —— 只 SELECT 你要的列，
      DuckDB 会跳过其余列的解析，内存和耗时都降一个量级（这就是「不 OOM」的做法）。
"""
from __future__ import annotations

# ABA「Top Search Terms」周报的列名（单复数按原样，别"顺手统一"）
COL_RANK = "Search Frequency Rank"
COL_TERM = "Search Term"
COL_PRODUCT = "Top Clicked Product #{i}: ASIN"
COL_TITLE = "Top Clicked Product #{i}: Product Title"
COL_CLICK = "Top Clicked Product #{i}: Click Share"
COL_CONV = "Top Clicked Product #{i}: Conversion Share"
COL_BRAND = {1: "Top Clicked Brand #1", 2: "Top Clicked Brands #2", 3: "Top Clicked Brands #3"}
COL_CAT = {1: "Top Clicked Category #1", 2: "Top Clicked Category #2", 3: "Top Clicked Category #3"}

# 常用列集（列裁剪的最小集合）
COLS_LIGHT = [COL_TERM, COL_RANK]
COLS_DEEP = (
    [COL_TERM]
    + [c.format(i=i) for i in (1, 2, 3) for c in (COL_PRODUCT, COL_TITLE)]
    + [COL_BRAND[i] for i in (1, 2, 3)]
    + [COL_CAT[i] for i in (1, 2)]
)


def q(ident: str) -> str:
    """把列名变成 DuckDB 的标识符（列名里有空格和 #，「必须」加双引号）。"""
    return '"' + ident.replace('"', '""') + '"'


def col(i: int) -> str:
    """read_csv(header=false) 的匿名列名：column00 / column01 …"""
    return f"column{i:02d}"


def detect_layout(path: str):
    """识别表头，返回 {"skip": 数据起始行, "map": {标准列名: 实际列位置}}。

    **中文后台导出的周报，列名被整段翻译**（Search Frequency Rank → 搜索频率排名，
    Top Clicked Product #1: Click Share → 点击量最高的商品：点击份额），
    按英文名取列会直接 BinderException。所以这里先认清实际列位置，
    再在 SQL 里把这些位置改名成标准英文列名 —— 下游代码一个字都不用改。
    认不出来（返回 None）时调用方回退到「按英文名读」。
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

    def pick(pred):
        return [i for i, h in enumerate(low) if pred(h)]

    rank = pick(lambda h: "frequency rank" in h or "排名" in h)
    term = pick(lambda h: h == "search term" or "搜索词" in h)
    asin = pick(lambda h: "asin" in h)
    title = pick(lambda h: "product title" in h or "标题" in h)
    click = pick(lambda h: "click share" in h or ("点击" in h and ("份额" in h or "占比" in h)))
    conv = pick(lambda h: "conversion" in h or "转化" in h)
    brand = pick(lambda h: "brand" in h or "品牌" in h)
    cat = pick(lambda h: "category" in h or "分类" in h)

    if not (rank and term and len(asin) >= 3 and len(click) >= 3):
        return None

    m = {COL_RANK: rank[0], COL_TERM: term[0]}
    for i in (1, 2, 3):
        m[COL_PRODUCT.format(i=i)] = asin[i - 1]
        m[COL_CLICK.format(i=i)] = click[i - 1]
        if len(title) >= i:
            m[COL_TITLE.format(i=i)] = title[i - 1]
        if len(conv) >= i:
            m[COL_CONV.format(i=i)] = conv[i - 1]
    for i in (1, 2, 3):
        if len(brand) >= i:
            m[COL_BRAND[i]] = brand[i - 1]
    for i in (1, 2):
        if len(cat) >= i:
            m[COL_CAT[i]] = cat[i - 1]
    return {"skip": skip, "map": m}


def select_list(cols) -> str:
    return ", ".join(q(c) for c in cols)


def source_sql(path: str, cols) -> tuple[str, list]:
    """返回 (SQL, 参数)。skip=1 + 列裁剪一次到位。"""
    sql = (f"SELECT {select_list(cols)}\n"
           f"FROM read_csv_auto(?, skip=1, header=true)")
    return sql, [str(path)]


TIER_HINT = """
读不动大文件时，按这个顺序降级：
  ① 先只 SELECT 你真正要的列（`--cols light` 只读 2 列）
  ② `SET threads=4` / `SET memory_limit='6GB'`（别让它吃满）
  ③ 反复跑同一批文件 → 先转 parquet 缓存一次，之后 `read_parquet()` 亚秒级
     （`run.py cache --csv-dir ... --cache-dir ...`）
"""
