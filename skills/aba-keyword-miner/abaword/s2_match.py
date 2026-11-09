# -*- coding: utf-8 -*-
"""第 2 步：ASIN 反向命中搜索词。

正向捞词的天花板是「你只能看到自己投过的词」。ABA 报告真正值钱的地方，是每个搜索词都带了三列
「点击最多的商品 #1/#2/#3」ASIN —— 反过来把我的竞品 ASIN 丢进去，就能捞出
「整个类目里真实买家在搜、并且搜完点进了这些竞品」的词，这是你没投过也可能没见过的词。

同一条 SQL 里顺手算出口径：
  best_rank       历史最佳排名   min(rank)  —— 排名是波动的，它的涨跌本身就是选词信号
  latest_rank     最近一次排名   命中周里最新一周的 rank
  hit_asin_count  命中 ASIN 数   有多少个目标 ASIN 出现在这个词下
  click_share     点击份额       最新一周命中的那些 ASIN 的 click share 之和
"""
from __future__ import annotations

import duckdb

# 归一化后的 ASIN / 词键
KEY = "upper(trim({c}))"
TKEY = "upper(regexp_replace(trim({c}), '\\s+', ' ', 'g'))"

CLICK_NUM = ("try_cast(regexp_replace(coalesce({c},''), '[^0-9.]', '', 'g') AS DOUBLE)")
CLICK_FIX = "CASE WHEN {c} > 1.5 THEN {c}/100 ELSE {c} END"   # 12.34 → 0.1234


def _long_ck(alias="aba") -> str:
    parts = []
    for i in (1, 2, 3):
        parts.append(f"""
  SELECT {TKEY.format(c='term')} AS tkey, trim(term) AS term, week, rank, {i} AS slot,
         {KEY.format(c=f'asin{i}')} AS asin,
         {CLICK_NUM.format(c=f'click{i}')} AS cs_raw
  FROM {alias}
  WHERE asin{i} IS NOT NULL AND trim(asin{i}) <> ''""")
    return " UNION ALL ".join(parts)


def reverse_match(db_path, target_asins: list[str], min_score_note=True) -> list[dict]:
    """返回按「最近排名」升序排列的词表"""
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        vals = ",".join("(?)" for _ in target_asins)
        sql = f"""
        WITH lng AS ({_long_ck()}),
        cln AS (
          SELECT tkey, term, week, rank, slot, asin, {CLICK_FIX.format(c='cs_raw')} AS cs
          FROM lng
        ),
        tgt(asin) AS (VALUES {vals}),
        hit AS (SELECT c.* FROM cln c JOIN tgt t ON c.asin = t.asin),
        lastw AS (SELECT tkey, max(week) AS wk FROM hit GROUP BY tkey)
        SELECT any_value(h.term)                                        AS term,
               min(h.rank)                                              AS best_rank,
               max(CASE WHEN h.week = l.wk THEN h.rank END)             AS latest_rank,
               count(DISTINCT h.asin)                                   AS hit_asin_count,
               least(1.0, sum(CASE WHEN h.week = l.wk THEN h.cs ELSE 0 END)) AS click_share,
               count(DISTINCT h.week)                                   AS weeks_hit,
               string_agg(DISTINCT CASE WHEN h.week = l.wk THEN h.asin END, ',') AS matched_asins
        FROM hit h JOIN lastw l USING (tkey)
        GROUP BY h.tkey
        ORDER BY latest_rank NULLS LAST
        """
        params = [a.strip().upper() for a in target_asins]
        rows = con.execute(sql, params).fetchall()
        cols = ["term", "best_rank", "latest_rank", "hit_asin_count", "click_share",
                "weeks_hit", "matched_asins"]
        out = [dict(zip(cols, r)) for r in rows]

        stats = {
            "扫描词数": con.execute("SELECT count(DISTINCT upper(regexp_replace(trim(term),'\\s+',' ','g'))) FROM aba").fetchone()[0],
            "总行数": con.execute("SELECT count(*) FROM aba").fetchone()[0],
            "周数": con.execute("SELECT count(DISTINCT week) FROM aba").fetchone()[0],
            "命中词数": len(out),
        }
        # 未命中任何词的 ASIN（提醒用户是不是 ASIN 写错了）
        hit_asins = set()
        for r in out:
            if r["matched_asins"]:
                hit_asins.update(r["matched_asins"].split(","))
        stats["未命中的ASIN"] = sorted(set(params) - hit_asins)
    finally:
        con.close()

    if min_score_note and out:
        pass
    return out, stats
