#!/usr/bin/env python3
"""竞品库流水线 · 步骤 6：用 TypeSafe Jev 对候选 ASIN 做【同赛道相关度 1-10 打分】+【6 类归类】+【备注】。

为什么用 Jev 而不是普通 LLM：
  这一步要对上百个候选逐个判「是不是同赛道」，要求**同一个候选每次问都给同一个答案**。
  生成式 LLM 逐字生成、同一输入两次可能两个答案；Jev 是决策模型，只输出「打几分 + 每级概率」，
  结构上不给它自由发挥的空间。

备注从哪来（关键设计）：
  Jev 不生成自由文本 —— 所以备注**不是模型编的**，而是由「证据」自动拼装：
  类目是否一致 / 标题命中了哪几个核心词 / 品牌是否同一 / 价格差。
  这样读者能一眼看出「凭什么这么判」，也能自己复算。

用法：
  python3 score_competitors.py --lib out/competitors_raw.json --keywords "a,b,c" \
      [--limit N] [--batch 20] [--out out]
环境变量：TYPESAFE_API_KEY（必填）、TYPESAFE_MODEL（可选，默认 jev-latest）
"""
import argparse
import json
import os
import re
import sys
import time

import httpx

URL = "https://api.typesafe.ai/v1/systemone"
RUBRIC = [str(i) for i in range(1, 11)]

CLASSES = {
    "直接竞品": "同一细分品类、同一产品形态（例如都是台面式制冰机），抢同一批搜索流量",
    "同类不同款": "同属目标类目，但产品形态/规格/类型不同（例如冰型不同、容量档位不同）",
    "同品牌家族": "与目标产品是同一品牌的其他型号或系列",
    "配件耗材": "不是整机，而是配件、滤芯、耗材、零件",
    "替代方案": "不属于该品类，但能满足同类使用需求（替代性方案）",
    "无关": "类目与用途都与目标产品无关",
}


def build_state(own: dict) -> dict:
    return {
        "target_product": {
            "title": own.get("title"),
            "brand": own.get("brand"),
            "category": own.get("category"),
            "price_usd": own.get("price"),
            "bullets": (own.get("bullets") or [])[:4],
        },
        "core_keywords": None,   # 由 main 填
    }


def build_questions(cands: list[dict]) -> dict:
    qs = {}
    for i, c in enumerate(cands):
        brief = (f"标题：{c.get('detail_title') or c.get('title')}；"
                 f"品牌：{c.get('brand') or '未知'}；"
                 f"类目：{c.get('category') or '未知'}；"
                 f"价格：{c.get('price') or '未知'}")
        qs[f"c{i}_score"] = {
            "type": "score", "criteria": RUBRIC,
            "instructions": (f"候选商品 —— {brief}。"
                             "评估它与 state.target_product 的【同赛道竞争相关度】："
                             "1=完全无关的另一个品类，10=同一细分赛道、直接抢同一批搜索流量的对位竞品。"),
        }
        qs[f"c{i}_class"] = {
            "type": "choice", "criteria": CLASSES,
            "instructions": f"候选商品 —— {brief}。判断它属于哪一类（单选）。",
        }
        qs[f"c{i}_noul"] = {
            "type": "noul",
            "instructions": (f"候选商品 —— {brief}。"
                             "断言：该商品是 state.target_product 的直接竞争对手（同赛道、抢同一批流量）。"),
        }
    return qs


def call_jev(api_key, model, state, questions, retries=3):
    last = None
    for a in range(retries):
        try:
            r = httpx.post(URL, json={"model": model, "state": state, "questions": questions},
                           headers={"Authorization": f"Bearer {api_key}"}, timeout=120)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last = e
            time.sleep(2 * (a + 1))
    raise RuntimeError(f"Jev 调用失败：{last}")


def _norm(s):
    return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())


def make_reason(c, own, keywords, cls):
    """备注 = 证据拼装（不生成）。"""
    title = _norm(c.get("detail_title") or c.get("title"))
    cat = c.get("category") or ""
    owncat = own.get("category") or ""
    own_last = owncat.split(">")[-1].strip() if owncat else ""
    cat_last = cat.split(">")[-1].strip() if cat else ""

    hits = [k for k in keywords if _norm(k) and _norm(k) in title]
    ev = []
    if cat_last:
        ev.append(f"类目「{cat_last}」" + ("与目标一致" if cat_last == own_last else f"与目标的「{own_last}」不同"))
    if hits:
        ev.append("标题命中核心词 " + "、".join(f"「{h}」" for h in hits[:3]))
    b, ob = (c.get("brand") or "").strip(), (own.get("brand") or "").strip()
    if b and ob:
        ev.append("品牌相同" if b.lower() == ob.lower() else f"品牌不同（{b} vs {ob}）")
    p, op = c.get("price"), own.get("price")
    if p and op:
        ev.append(f"价格 ${p} vs 目标 ${op}")
    ev_txt = "；".join(ev) if ev else "仅有标题信息"

    tail = {
        "直接竞品": "→ 抢同一批搜索流量，是最该盯的对位竞品",
        "同类不同款": "→ 有流量重叠，但不是直接对位，可作第二梯队观察",
        "同品牌家族": "→ 同品牌不同型号，内部抢位风险大于外部竞争",
        "配件耗材": "→ 不承接同类整机搜索流量",
        "替代方案": "→ 满足同类需求但品类不同，属替代而非竞品",
        "无关": "→ 不构成竞争",
    }.get(cls, "")
    return (ev_txt + " " + tail).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lib", required=True, help="competitors_raw.json")
    ap.add_argument("--keywords", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--batch", type=int, default=20)
    ap.add_argument("--out", default="out")
    a = ap.parse_args()

    api_key = os.environ.get("TYPESAFE_API_KEY")
    if not api_key:
        raise SystemExit("缺少环境变量 TYPESAFE_API_KEY")
    model = os.environ.get("TYPESAFE_MODEL", "jev-latest")
    keywords = [k.strip() for k in a.keywords.split(",") if k.strip()]

    d = json.load(open(a.lib, encoding="utf-8"))
    own, cands = d["stats"]["own"], d["competitors"]
    if a.limit:
        cands = cands[:a.limit]

    state = build_state(own)
    state["core_keywords"] = keywords

    out = []
    for start in range(0, len(cands), a.batch):
        chunk = cands[start:start + a.batch]
        resp = call_jev(api_key, model, state, build_questions(chunk))
        ans = resp["answers"]
        for i, c in enumerate(chunk):
            sa, ca, na = ans.get(f"c{i}_score", {}), ans.get(f"c{i}_class", {}), ans.get(f"c{i}_noul", {})
            probs = {int(k): v for k, v in (sa.get("probabilities") or {}).items()}
            idx = sa.get("score")
            if idx is None and probs:
                idx = sum(k * v for k, v in probs.items())
            score10 = round(idx + 1, 1) if idx is not None else None
            p_high = round(sum(v for k, v in probs.items() if k >= 7), 3)
            cls = ca.get("choice")
            out.append({
                **{k: c.get(k) for k in
                   ("asin", "detail_title", "title", "brand", "category", "price",
                    "rating", "n_hits", "best_pos", "sources", "keywords",
                    "sponsored", "enriched", "bullets")},
                "relevance": score10,
                "p_high": p_high,
                "klass": cls,
                "p_direct": round(na.get("noul"), 3) if na.get("noul") is not None else None,
                "confidence": sa.get("confidence"),
                "reason": make_reason(c, own, keywords, cls),
            })
        print(f"  已打分 {min(start + a.batch, len(cands))}/{len(cands)}", file=sys.stderr)

    out.sort(key=lambda r: (-(r["relevance"] or 0), r["best_pos"]))
    json.dump({"target": own, "keywords": keywords, "scored": out},
              open(os.path.join(a.out, "competitors_scored.json"), "w"),
              ensure_ascii=False, indent=1)

    n = len(out)
    hi = [r for r in out if (r["relevance"] or 0) >= 7]
    mid = [r for r in out if 5 <= (r["relevance"] or 0) < 7]
    lo = [r for r in out if (r["relevance"] or 0) < 5]
    print(f"\n=== 打分完成 {n} 个候选 ===")
    print(f"  高相关(>=7): {len(hi)} ({len(hi)/n*100:.1f}%)")
    print(f"  中相关(5-7): {len(mid)} ({len(mid)/n*100:.1f}%)")
    print(f"  低相关(<5):  {len(lo)} ({len(lo)/n*100:.1f}%)")
    from collections import Counter
    print("  分类分布:", dict(Counter(r["klass"] for r in out)))
    print(f"  反证条件（高相关占比<10%则『自动筛查』不成立）: "
          f"{'❌ 不成立' if len(hi)/n < 0.1 else '✅ 成立'}")
    print(f"→ {a.out}/competitors_scored.json")


if __name__ == "__main__":
    main()
