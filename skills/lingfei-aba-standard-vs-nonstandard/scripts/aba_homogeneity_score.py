#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ABA 同质度打分器 —— 判断一个搜索词的「前三名」能不能同时吃掉点击和转化。

用法:
    # 只打分指定的词（一行一个）
    python3 aba_homogeneity_score.py --aba <周报CSV> --terms terms.txt --out scored.csv

    # 打分该周排名最靠前的 N 个词（默认 2000，用于建立自己的分档清单）
    python3 aba_homogeneity_score.py --aba <周报CSV> --top 2000 --out top2000.csv

依赖：duckdb（见 SKILL.md 的「依赖」一节，用独立 venv 安装）

口径（务必先读，改动会改变结论）:
  1. 分层：按 Search Frequency Rank 切 6 层，**每层各自算大盘中位**
     （长尾 rank 是桶号不是名次，只能用来分层）
  2. rel_click = 该词前三点击份额 ÷ 该层点击份额中位     1.0 = 与大盘持平
     rel_conv  = 该词前三转化份额 ÷ 该层转化份额中位
  3. 分档看 rel_conv（区分度 AUC 0.948，远高于 rel_click 的 0.855）:
        A ≥1.5  B 0.8–1.5  C 0.3–0.8  D <0.3
  4. 陷阱区 = rel_click ≥1.0 但 rel_conv <0.8（点击集中在头部、转化不归头部）
"""
import argparse
import csv
import os
import statistics
import sys

try:
    import duckdb
except ImportError:
    sys.exit("缺少依赖 duckdb，请按 SKILL.md 的依赖一节在独立环境安装后再运行")

LAYERS = [(0, 1000, "rank<1k"), (1000, 5000, "1k-5k"), (5000, 20000, "5k-20k"),
          (20000, 100000, "20k-100k"), (100000, 500000, "100k-500k"),
          (500000, 10 ** 12, ">500k")]

# ── 表头识别：英文原版 / 中文界面下载的周报都要能读 ────────────────────────
# 中文导出把列名整段翻译了（"Search Frequency Rank" → "搜索频率排名"，
# "Top Clicked Product #1: Click Share" → "点击量最高的商品：点击份额"），
# 所以不能按名字取列。这里改用「位置」：两版商品块结构一致，
# 每个商品固定占 4 列 = ASIN → 标题 → 点击份额 → 转化份额，
# 只要定位到 ASIN 列，点击/转化份额就在 +2 / +3 位。
def _read_head_rows(path, n=3):
    last = None
    for enc in ("utf-8-sig", "gb18030", "utf-16"):
        try:
            with open(path, encoding=enc, newline="") as f:
                rd = csv.reader(f)
                rows = []
                for _ in range(n):
                    try:
                        rows.append(next(rd))
                    except StopIteration:
                        break
            if rows:
                return rows, enc
        except (UnicodeDecodeError, UnicodeError) as e:
            last = e
        except OSError:
            raise
    sys.exit(f"读不了这个文件的表头（编码不支持）：{last}")


def detect_layout(path):
    """返回 dict: skip(数据起始行), rank, term, shares=[(cs_idx,cv_idx)x3]"""
    rows, enc = _read_head_rows(path)
    # 表头 = 前几行里列数最多的那行（第 0 行是 Reporting Range 元数据，列很少）
    hi = max(range(len(rows)), key=lambda i: len(rows[i]))
    head = [c.strip() for c in rows[hi]]

    def find(pred):
        for i, h in enumerate(head):
            if pred(h):
                return i
        return None

    rank = find(lambda h: "search frequency rank" in h.lower() or "排名" in h)
    term = find(lambda h: h.lower() == "search term" or "搜索词" in h)

    # 商品块起点：所有含 ASIN 的列（#1→#3 按出现顺序）
    asin = [i for i, h in enumerate(head) if "asin" in h.lower()]
    shares = []
    for b in asin:
        cs, cv = b + 2, b + 3
        if cv < len(head) and ("份额" in head[cs] or "share" in head[cs].lower()) \
                and ("转化" in head[cv] or "conversion" in head[cv].lower()):
            shares.append((cs, cv))
    shares = shares[:3]

    if rank is None or term is None or len(shares) < 3:
        sys.exit(
            "表头识别失败：找不到 排名/搜索词/商品点击份额/商品转化份额 这几列。\n"
            f"  文件：{path}\n  编码：{enc}\n  识别到的表头（{len(head)} 列）：\n    "
            + " | ".join(f"[{i}]{h}" for i, h in enumerate(head))
            + "\n  支持：英文原版周报（US_Top_Search_Terms_Simple_Week_*.csv）"
              " 与中文界面周报（US_热门搜索词_简单_Week_*.csv）"
        )
    return {"skip": hi + 1, "rank": rank, "term": term, "shares": shares, "enc": enc,
            "header": head}


def _ph(i):
    """DuckDB 对无表头 CSV 的匿名列名是零填充的 column00/column01…（至少两位）。"""
    return f"column{i:02d}"


def _num(i):
    """份额列的容错数值化：有的导出是 9.3%，有的是 9.3，去掉 % 和千分位再转。"""
    c = _ph(i)
    return f"TRY_CAST(replace(replace(trim({c}), '%', ''), ',', '') AS DOUBLE)"


def build_cols(layout):
    r = layout["rank"]
    parts = [f'TRY_CAST({_ph(r)} AS BIGINT) rk']
    for n, (cs, _) in enumerate(layout["shares"], 1):
        parts.append(f'{_num(cs)} cs{n}')
    for n, (_, cv) in enumerate(layout["shares"], 1):
        parts.append(f'{_num(cv)} cv{n}')
    return ",\n  ".join(parts)


def layer_of(rk):
    for lo, hi, lab in LAYERS:
        if lo <= rk < hi:
            return lab
    return None


def band(rel_conv):
    if rel_conv is None:
        return ""
    if rel_conv >= 1.5:
        return "A 转化强垄断"
    if rel_conv >= 0.8:
        return "B 跟得上大盘"
    if rel_conv >= 0.3:
        return "C 转化偏散"
    return "D 转化不归头部"


def quadrant(rc, rv):
    if rc is None or rv is None:
        return ""
    x = "点击高" if rc >= 1.0 else "点击低"
    y = "转化高" if rv >= 1.0 else "转化低"
    return f"{x}·{y}"


def action_of(rc, rv):
    if rc is None or rv is None:
        return ""
    if rv >= 1.5 and rc >= 1.0:
        return "抢前三（回报明确）"
    if rc >= 1.0 and rv < 0.8:
        return "陷阱区：别为自然位溢价，降预算"
    if rv >= 0.8:
        return "可打，控 ACoS"
    if rv >= 0.3:
        return "只买直接订单"
    return "只买直接订单（转化不归头部）"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aba", required=True, help="ABA 周报原始 CSV（US_Top_Search_Terms_Simple_Week_*.csv）")
    ap.add_argument("--terms", default="", help="要打分的词表（一行一个）；不给则用 --top")
    ap.add_argument("--top", type=int, default=2000, help="按排名取前 N 个词（默认 2000）")
    ap.add_argument("--out", default="scored.csv")
    a = ap.parse_args()

    if not os.path.exists(a.aba):
        sys.exit(f"找不到文件：{a.aba}")

    con = duckdb.connect()
    con.execute("PRAGMA threads=4")
    lay = detect_layout(a.aba)
    print(f"表头：{lay['enc']}，{len(lay['header'])} 列，数据从第 {lay['skip'] + 1} 行开始"
          f"（排名列[{lay['rank']}]、搜索词列[{lay['term']}]）")
    _p = str(a.aba).replace("'", "''")
    src = f"read_csv_auto('{_p}', skip={lay['skip']}, header=false, all_varchar=true)"
    COLS = build_cols(lay)
    term_col = f'lower(trim({_ph(lay["term"])}))'

    # ── 1) 分层基线：每层的点击/转化份额中位（用该周全量词算）
    print("正在计算分层基线 ...")
    base = {}
    for lo, hi, lab in LAYERS:
        row = con.execute(f"""
          WITH t AS (SELECT {COLS} FROM {src})
          SELECT count(*),
            median(coalesce(cs1,0)+coalesce(cs2,0)+coalesce(cs3,0)),
            median(coalesce(cv1,0)+coalesce(cv2,0)+coalesce(cv3,0))
          FROM t WHERE rk >= {lo} AND rk < {hi}
        """).fetchone()
        if row and row[0]:
            base[lab] = {"n": int(row[0]), "cs50": float(row[1]), "cv50": float(row[2])}
    for lab, v in base.items():
        print(f"  {lab:12} n={v['n']:>9,}  点击中位 {v['cs50']:5.2f}%  转化中位 {v['cv50']:5.2f}%")

    # ── 2) 取词
    if a.terms:
        terms = [l.strip().lower() for l in open(a.terms, encoding="utf-8") if l.strip()]
        ph = ",".join("?" * len(terms))
        q = f"""WITH t AS (SELECT {term_col} term, {COLS} FROM {src})
                SELECT * FROM t WHERE term IN ({ph})"""
        rows = con.execute(q, terms).fetchall()
    else:
        q = f"""WITH t AS (SELECT {term_col} term, {COLS} FROM {src})
                SELECT * FROM t WHERE rk IS NOT NULL ORDER BY rk LIMIT {a.top}"""
        rows = con.execute(q).fetchall()

    out = []
    for term, rk, cs1, cs2, cs3, cv1, cv2, cv3 in rows:
        if rk is None:
            continue
        lay = layer_of(rk)
        if lay not in base:
            continue
        cs = [x for x in (cs1, cs2, cs3) if x is not None]
        cv = [x for x in (cv1, cv2, cv3) if x is not None]
        if len(cs) < 2:
            continue
        tc = round(sum(cs), 2)
        tv = round(sum(cv), 2) if cv else None
        rc = round(tc / base[lay]["cs50"], 3) if base[lay]["cs50"] else None
        rv = round(tv / base[lay]["cv50"], 3) if (tv is not None and base[lay]["cv50"]) else None
        out.append({"term": term, "rank": rk, "layer": lay,
                    "top3_click": tc, "top3_conv": tv,
                    "rel_click": rc, "rel_conv": rv,
                    "head_share_click": round(tc / 3, 2),
                    "head_share_conv": round(tv / 3, 2) if tv is not None else "",
                    "band": band(rv), "quadrant": quadrant(rc, rv),
                    "action": action_of(rc, rv)})

    if not out:
        sys.exit("没有可打分的词（检查词表拼写或文件是否读对）")

    cols = list(out[0].keys())
    with open(a.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(out)

    # ── 3) 汇总
    from collections import Counter
    cnt = Counter(r["band"] for r in out)
    print(f"\n打分完成：{len(out)} 个词 → {a.out}")
    for k in ("A 转化强垄断", "B 跟得上大盘", "C 转化偏散", "D 转化不归头部"):
        if cnt[k]:
            print(f"  {k:14} {cnt[k]:>5} 个")
    qc = Counter(r["quadrant"] for r in out if r["quadrant"])
    print("  四象限：", dict(qc))
    med = statistics.median([r["rel_conv"] for r in out if r["rel_conv"] is not None])
    print(f"  rel_conv 中位：{med:.3f}（<0.3 视为转化不归头部）")


if __name__ == "__main__":
    main()
