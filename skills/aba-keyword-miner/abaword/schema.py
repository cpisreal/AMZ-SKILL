# -*- coding: utf-8 -*-
"""ABA 热搜词报告 —— 表头自适应识别

ABA（Brand Analytics · Amazon Search Terms）报告的列名会随「卖家后台语言」和站点变化，
而且**每个 CSV 的第一行是元数据**（`Reporting Range=...`），真正的表头在第二行。
这里不写死列名，而是用「表头正则 + 取值特征」双重识别，中英文都能吃。
"""
from __future__ import annotations

import re

ASIN_RE = re.compile(r"^B0[A-Z0-9]{8}$")

# 「序号」的多种写法：#1 / 1 / 一 / ①
IDX_PATTERNS = {
    1: r"(?:#\s*1|第\s*1\s*个|_1\b|\b1\b|[①一])",
    2: r"(?:#\s*2|第\s*2\s*个|_2\b|\b2\b|[②二])",
    3: r"(?:#\s*3|第\s*3\s*个|_3\b|\b3\b|[③三])",
}
TERM_PAT = r"(?:搜索词|query|search\s*term|keyword)"
RANK_PAT = r"(?:搜索频率排名|search\s*frequency\s*rank|frequency\s*rank|排名)"
ASIN_PAT = r"(?:asin)"
SHARE_PAT = r"(?:click\s*share|点击份额|点击量份额|点击占比)"
CONV_PAT = r"(?:conversion\s*share|转化份额|转化占比)"
TITLE_PAT = r"(?:product\s*title|商品名称|商品标题|标题)"


def _norm(h: str) -> str:
    return re.sub(r"\s+", " ", str(h)).strip().lower()


def detect_columns(headers: list[str], sample_rows: list[dict] | None = None) -> dict:
    """返回 {term, rank, asin1..3, click1..3, conv1..3, title1..3} 列名映射（缺失为 None）"""
    cols = {"term": None, "rank": None}
    for i in (1, 2, 3):
        cols[f"asin{i}"] = cols[f"click{i}"] = cols[f"conv{i}"] = cols[f"title{i}"] = None

    for h in headers:
        n = _norm(h)
        # 「点击份额」要先于「ASIN」判断，避免误抢
        if cols["term"] is None and re.search(TERM_PAT, n) and not re.search(RANK_PAT, n):
            cols["term"] = h
            continue
        if cols["rank"] is None and re.search(RANK_PAT, n):
            cols["rank"] = h
            continue
        for i in (1, 2, 3):
            if not re.search(IDX_PATTERNS[i], n):
                continue
            if re.search(ASIN_PAT, n) and cols[f"asin{i}"] is None:
                cols[f"asin{i}"] = h
            elif re.search(SHARE_PAT, n) and cols[f"click{i}"] is None:
                cols[f"click{i}"] = h
            elif re.search(CONV_PAT, n) and cols[f"conv{i}"] is None:
                cols[f"conv{i}"] = h
            elif re.search(TITLE_PAT, n) and cols[f"title{i}"] is None:
                cols[f"title{i}"] = h

    # ── 兜底：表头认不出来时，用「取值像不像 ASIN」来判定 ──
    if sample_rows:
        n_rows = max(len(sample_rows), 1)
        hits = []
        for h in headers:
            vals = [str(r.get(h) or "").strip() for r in sample_rows]
            n_asin = sum(bool(ASIN_RE.match(v)) for v in vals)
            if n_asin / n_rows >= 0.30:
                hits.append(h)
        missing = [i for i in (1, 2, 3) if cols[f"asin{i}"] is None]
        for i, h in zip(missing, hits):
            cols[f"asin{i}"] = h
        # 点击份额：ASIN 列紧邻的数值列
        for i in (1, 2, 3):
            if cols[f"asin{i}"] and cols[f"click{i}"] is None:
                try:
                    j = headers.index(cols[f"asin{i}"])
                    for cand in headers[j + 1: j + 3]:
                        vals = [str(r.get(cand) or "").strip() for r in sample_rows]
                        num = sum(_is_num(v) for v in vals)
                        if num / n_rows >= 0.5 and not re.search(TITLE_PAT, _norm(cand)):
                            cols[f"click{i}"] = cand
                            break
                except ValueError:
                    pass
    return cols


def _is_num(v: str) -> bool:
    if not v:
        return False
    v = v.strip().replace("%", "").replace(",", "")
    try:
        float(v)
        return True
    except ValueError:
        return False


def parse_reporting_range(first_line: str) -> tuple[str | None, str | None]:
    """从首行元数据里取报告区间。返回 (start, end)，失败返回 (None, None)

    典型形态：Reporting Range=2026-08-01 - 2026-08-07
    也兼容：  Report Range: 08/01/2026 - 08/07/2026 / 报告范围=...
    """
    if not first_line:
        return None, None
    m = re.search(
        r"(?:reporting\s*range|report\s*range|报告范围|报告期间)\s*[=:：]\s*(.+)",
        first_line, re.I)
    body = m.group(1) if m else first_line
    dates = re.findall(r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}", body)
    if len(dates) >= 2:
        return _iso(dates[0]), _iso(dates[-1])
    if len(dates) == 1:
        return _iso(dates[0]), _iso(dates[0])
    return None, None


def _iso(d: str) -> str:
    if re.match(r"\d{4}-\d{2}-\d{2}", d):
        return d
    mm, dd, yy = d.split("/")
    return f"{yy}-{int(mm):02d}-{int(dd):02d}"
