"""五步管线：找种子 ASIN → 反查关联词 → 词根归属性 → 加速度 + 周统计。"""
from __future__ import annotations

import json
import os


# ---------- 第二步：找种子 ASIN ----------
def find_seeds(con, must_terms, top: int = 10, table: str = "aba", verbose: bool = True):
    """品类词（必须全部命中）→ 命中的 Top Clicked ASIN → 按「被多少个去重词命中」排序取 top N。"""
    conds = " AND ".join(f"lower(term) LIKE '%{t.lower()}%'" for t in must_terms)
    con.execute(f"""CREATE OR REPLACE TABLE seeds AS
WITH hits AS (
  SELECT a AS asin, count(DISTINCT term) AS n_terms
  FROM (SELECT term, a1 AS a FROM {table} WHERE {conds}
        UNION ALL SELECT term, a2 FROM {table} WHERE {conds}
        UNION ALL SELECT term, a3 FROM {table} WHERE {conds})
  WHERE a IS NOT NULL AND a <> '' GROUP BY a)
SELECT * FROM hits ORDER BY n_terms DESC, asin LIMIT {int(top)}""")
    rows = con.execute("SELECT asin, n_terms FROM seeds").fetchall()
    n_all = con.execute(f"""SELECT count(DISTINCT a) FROM (
        SELECT a1 AS a FROM {table} WHERE {conds} UNION ALL SELECT a2 FROM {table} WHERE {conds}
        UNION ALL SELECT a3 FROM {table} WHERE {conds}) WHERE a IS NOT NULL AND a <> ''""").fetchone()[0]
    if verbose:
        print(f"  命中去重 ASIN {n_all:,} → 取前 {len(rows)} 个作种子", flush=True)
    return rows, n_all


# ---------- 第三步：反查关联词 ----------
def find_related(con, table: str = "aba", verbose: bool = True):
    """种子 ASIN 命中的全部搜索词（去重）。"""
    con.execute(f"""CREATE OR REPLACE TABLE related AS
SELECT DISTINCT term FROM (
  SELECT term FROM {table} WHERE a1 IN (SELECT asin FROM seeds)
  UNION SELECT term FROM {table} WHERE a2 IN (SELECT asin FROM seeds)
  UNION SELECT term FROM {table} WHERE a3 IN (SELECT asin FROM seeds))""")
    n = con.execute("SELECT count(*) FROM related").fetchone()[0]
    con.execute(f"""CREATE OR REPLACE TABLE related_week AS
SELECT DISTINCT term, wk FROM {table} WHERE term IN (SELECT term FROM related)""")
    if verbose:
        print(f"  关联词去重 {n:,}", flush=True)
    return n


# ---------- 词根匹配（空格包裹，防误伤） ----------
def root_condition(word: str) -> str:
    """`men` 不能直接子串匹配（会误伤 womens）→ 用空格/边界包裹的四种形态。"""
    w = word.lower()
    return (f"lower(term) LIKE '% {w} %' OR lower(term) LIKE '{w} %' "
            f"OR lower(term) LIKE '% {w}' OR lower(term) = '{w}'")


def _attr_condition(words) -> str:
    return " OR ".join(f"({root_condition(w)})" for w in words)


def _iter_roots(spec):
    """规则包里的 roots 支持两种写法：

    {"family": ["family", "families"], "men": ["men"]}   ← 词根 → 拼写变体（推荐）
    ["family", "couples", "men"]                          ← 纯清单
    """
    if isinstance(spec, dict):
        return [(k, [v] if isinstance(v, str) else list(v)) for k, v in spec.items()]
    out = []
    for w in spec:
        if isinstance(w, (list, tuple)):
            out.append((w[0], list(w)))
        else:
            out.append((w, [w]))
    return out


# ---------- 第四步：词根归属性 ----------
def build_attributes(con, rules: dict, weeks, verbose: bool = True):
    """返回 (词根级 rows, 属性级 rows)。

    词根级：每个词根一条周序列（看 christmas / holiday / gift 这类单根份量）
    属性级：该属性下任意词根命中的去重词数（一个词可同时命中多个属性）
    """
    attrs = rules["attributes"]
    root_rows, attr_rows = [], []

    for attr, spec in attrs.items():
        variants_map = _iter_roots(spec)
        if not variants_map:
            continue
        for root_name, variants in variants_map:
            cond = " OR ".join(f"({root_condition(v)})" for v in variants)
            d = dict(con.execute(f"""SELECT wk, count(DISTINCT term) FROM related_week
                WHERE {cond} GROUP BY wk""").fetchall())
            total = con.execute(f"SELECT count(DISTINCT term) FROM related WHERE {cond}").fetchone()[0]
            root_rows.append({"attr": attr, "root": root_name, "total": int(total),
                              "weekly": [int(d.get(x, 0)) for x in weeks]})
        all_words = [v for _, vs in variants_map for v in vs]
        cond = _attr_condition(all_words)
        d = dict(con.execute(f"""SELECT wk, count(DISTINCT term) FROM related_week
            WHERE {cond} GROUP BY wk""").fetchall())
        total = con.execute(f"SELECT count(DISTINCT term) FROM related WHERE {cond}").fetchone()[0]
        attr_rows.append({"attr": attr, "total": int(total),
                          "weekly": [int(d.get(x, 0)) for x in weeks]})

    parts = []
    for attr, spec in attrs.items():
        all_words = [v for _, vs in _iter_roots(spec) for v in vs]
        if not all_words:
            continue
        parts.append(f"SELECT DISTINCT term, '{attr}' AS attr FROM related WHERE {_attr_condition(all_words)}")
    if parts:
        con.execute("CREATE OR REPLACE TABLE term_attr AS " + " UNION ".join(parts))

    if verbose:
        for r in attr_rows:
            print(f"  {r['attr']:6s} 整季={r['total']:5d} {r['weekly']}", flush=True)
    return root_rows, attr_rows


# ---------- 第五步：加速度 + 三个时间点 ----------
def accel_of(seq):
    """一阶差分：本周 − 上周。第一周没有「上周」，所以长度 = len(seq)-1。"""
    return [seq[i] - seq[i - 1] for i in range(1, len(seq))]


def turning_points(seq, weeks):
    """三个时间点：进场=加速度峰、加码=词量峰、撤退=加速度最低（断崖）。"""
    if not seq or len(seq) < 2:
        return {}
    diffs = accel_of(seq)
    i_acc = max(range(len(diffs)), key=lambda i: (diffs[i], -i)) + 1
    i_peak = max(range(len(seq)), key=lambda i: (seq[i], -i))
    i_drop = min(range(len(diffs)), key=lambda i: (diffs[i], i)) + 1
    return {
        "进场点": weeks[i_acc], "进场点词量": seq[i_acc], "进场点加速度": diffs[i_acc - 1],
        "加码点": weeks[i_peak], "加码点词量": seq[i_peak],
        "加码点加速度": diffs[i_peak - 1] if i_peak else None,
        "撤退点": weeks[i_drop], "撤退点词量": seq[i_drop], "撤退点加速度": diffs[i_drop - 1],
    }


def classify(seq, weeks):
    """形态：早衰 / 慢衰减 / 同步 / 零需求。判据基于峰值周位置与尾周占比。"""
    peak = max(seq) if seq else 0
    if peak == 0:
        return "零需求"
    i_peak = seq.index(peak)
    tail_pct = seq[-1] / peak * 100 if peak else 0.0
    if i_peak <= max(1, len(seq) // 3) and tail_pct < 25:
        return "早衰"
    if tail_pct >= 60:
        return "慢衰减"
    return "同步"


def build_accel(root_rows, attr_rows, weeks):
    out = []
    for kind, rows in (("词根", root_rows), ("属性", attr_rows)):
        for row in rows:
            seq = row["weekly"]
            out.append({"kind": kind, **row, "accel": accel_of(seq),
                        "points": turning_points(seq, weeks),
                        "shape": classify(seq, weeks)})
    return out


def load_rules(path: str) -> dict:
    if not os.path.exists(path):
        raise SystemExit(f"规则包不存在：{path}")
    with open(path, encoding="utf-8") as f:
        rules = json.load(f)
    rules.setdefault("attributes", {})
    if not rules["attributes"]:
        raise SystemExit("规则包里 attributes 为空，先在 rules/ 里配好属性词根")
    return rules
