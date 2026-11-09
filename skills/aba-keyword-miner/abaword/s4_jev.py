# -*- coding: utf-8 -*-
"""第 4 步：Jev 打分 + 分类，导出词表。

为什么不用生成式大模型：生成式是「一个字一个字往外蹦」，给 360 个词打分它会
① 慢（每个词排队等完整生成）② 贵（每个词走一遍完整推理）③ 会幻觉（同一个词问两次给两个答案）。
Jev 是 TypeSafe 的 System One 决策模型，不走 OpenRouter 的 chat 接口，而是 **Decisions API**：
你给一个 state（本商品的 Listing），再给一堆问题，它返回**类型化的概率答案**，结构上编不了。

它给的是「概率」不是「结论」——同样是 9 分，60% 把握和 99% 把握是两个完全不同的信号。
这个把握度，正是你批量处理几千个词时决定「哪些要人工抽验、哪些可以闭眼用」的依据。

🔴 坑三：Jev 一次别塞太多词（本文用 60 个/批作为安全值）。塞多了直接报错——不是模型笨，是你贪了。
"""
from __future__ import annotations

import json
import os
import re
import time

import requests

# ── 6 类词分类（文章口径）────────────────────────────────────────────────
CATS = {
    "category_word":    "品类词：描述产品品类的通用词，不含品牌，如 ice maker / countertop ice maker",
    "own_brand":        "自有品牌词：包含本商品自身品牌名或其拼写变体的词",
    "competitor_brand": "竞品品牌词：包含其他品牌名或型号的词",
    "attribute":        "属性规格词：描述材质、尺寸、容量、颜色、冰型、功率等具体属性的词",
    "scenario":         "场景用途词：描述使用场景或用途的词，如 for home / for party / for rv",
    "longtail":         "其他长尾：以上都不是的其余长尾词",
}
CAT_ZH = {"category_word": "品类词", "own_brand": "自有品牌词", "competitor_brand": "竞品品牌词",
          "attribute": "属性规格词", "scenario": "场景用途词", "longtail": "其他长尾"}

# 分类 → 怎么用（文章里那张表的「你会怎么用」列）
CAT_ACTION = {
    "category_word": "主力投放",
    "own_brand": "守品牌",
    "competitor_brand": "否定词 / 单独开活动打拦截",
    "attribute": "长尾拓量",
    "scenario": "长尾拓量",
    "longtail": "低优先，观察",
}

# ── 10 级相关度（score 的 criteria，从 1 到 10，每级独立判定）──────────────
LEVELS = [
    "完全无关：搜这个词的人根本不会想买本商品，属于另一个品类或另一种产品",
    "基本无关：只在极宽泛的概念上沾边，购买意图与本品类不同",
    "弱相关：同属一个大类，但产品形态明显不同（如一个是冰袋、一个是制冰机）",
    "偏弱相关：同品类，但关键属性不符（如冰型、规格、容量、电压不同），买家拿到的不是本商品",
    "中等相关：同品类且属性部分吻合，可能是本商品的替代选择之一",
    "中等偏上：同品类、核心功能吻合，买家有一定概率会选到本商品",
    "相关：明确的同品类词，买家意图与本商品吻合，可以投但要控成本",
    "强相关：精准描述本商品的品类与核心属性，是本商品该抢的词",
    "极强相关：几乎就是本商品的中文直译词，应当作为主力投放",
    "顶级相关：就是本商品自己的品牌词/型号词，或本商品最核心的品类大词，必须拿下",
]

PROVIDERS = {
    "openrouter": {"url": "https://openrouter.ai/api/alpha/decisions", "model": "typesafe/jev-1.13",
                   "key_env": "OPENROUTER_API_KEY"},
    "typesafe":   {"url": "https://api.typesafe.ai/v1/systemone", "model": "jev-latest",
                   "key_env": "TYPESAFE_API_KEY"},
}
PRICE_PER_MTOK = 0.042          # $ / 百万输入 token，输出免费


class JevError(RuntimeError):
    pass


ATTR_VOCAB = {
    "color", "colour", "size", "sizes", "inch", "inches", "lb", "lbs", "oz", "kg", "watt",
    "stainless", "steel", "plastic", "abs", "portable", "mini", "small", "large", "xl",
    "black", "white", "silver", "red", "blue", "digital", "electric", "compact", "quiet",
    "nugget", "bullet", "square", "clear", "cube", "cubes", "pellet", "crushed",
    "under", "built", "self", "cleaning", "scoop", "basket", "filter",
    "automatic", "smart", "heavy", "duty", "energy", "saving", "fast", "quick", "double",
}
SCEN_VOCAB = {
    "for", "home", "kitchen", "party", "rv", "bar", "camping", "camp", "office", "outdoor",
    "dorm", "apartment", "travel", "boat", "garage", "restaurant", "hotel", "gift",
    "christmas", "summer", "bbq", "barbecue", "tailgating", "wedding",
}
# 常见英文词（避免把普通词误判成品牌名）
COMMON = {
    "ice", "maker", "makers", "machine", "machines", "with", "and", "the", "a", "an", "of",
    "in", "on", "to", "best", "top", "new", "buy", "price", "cheap", "review", "reviews",
    "vs", "or", "not", "no", "how", "what", "why", "large", "small", "free", "cold",
}
NUM_UNIT = re.compile(r"\d+\s*(?:lb|lbs|oz|kg|l|ml|in|inch|inches|w|watt|qt|cups?)\b", re.I)


def _rules_mock(words: list[str], listing: dict) -> dict:
    """无 key 试跑模式：用规则近似打分，只用来验证流程跑得通，**不是** Jev。

    ⚠️ API 契约：score 的返回值是 **0 起始的层级序号**（10 级 → 0~9），
       所以这里也只能产出 0~9，由上层统一 +1 换算成 1–10 分。
    """
    title = (listing.get("title") or "").lower()
    doc = " ".join([title, listing.get("brand", ""), listing.get("category", "")]
                   + listing.get("bullets", []) + [listing.get("description", "")]).lower()
    toks = {w for w in re.findall(r"[a-z0-9]+", doc) if len(w) > 1}
    brand = re.sub(r"[^a-z0-9]", "", (listing.get("brand") or "").split()[0].lower()) if listing.get("brand") else ""

    res = {}
    for i, w in enumerate(words):
        wl = w.lower()
        wt = set(re.findall(r"[a-z0-9]+", wl))
        cov = len(wt & toks) / max(len(wt), 1)
        in_title = 1.0 if wl in title else 0.0
        in_doc = 1.0 if wl in doc else 0.0

        if brand and brand in re.sub(r"[^a-z0-9]", "", wl):
            cat, cap = "own_brand", 9.0
        else:
            lead = re.findall(r"[a-z0-9]+", wl)
            lead = lead[0] if lead else ""
            unknown_lead = (lead and lead not in toks and lead not in COMMON
                            and lead not in ATTR_VOCAB and lead not in SCEN_VOCAB)
            if unknown_lead and len(wt) >= 2:
                cat, cap = "competitor_brand", 3.5            # 竞品品牌词：分数压住，用来做否定
            elif wt & SCEN_VOCAB and "for" in wt:
                cat, cap = "scenario", 9.0
            elif (wt & ATTR_VOCAB) or NUM_UNIT.search(wl):
                cat, cap = "attribute", 9.0
            elif cov >= 0.99:
                cat, cap = "category_word", 9.0
            else:
                cat, cap = "longtail", 7.0

        raw9 = round(min(cap, 9.0 * (0.75 * cov + 0.15 * in_doc + 0.10 * in_title)), 2)
        conf = round(min(0.97, 0.45 + 0.55 * abs(cov - 0.5) * 2), 2)
        res[f"kw{i:04d}_score"] = {"type": "score", "score": raw9, "confidence": conf,
                                   "probabilities": {}, "legend": {}}
        res[f"kw{i:04d}_cat"] = {"type": "choice", "choice": cat, "confidence": conf,
                                 "probabilities": {}}
    return {"answers": res, "usage": {"input_tokens": 0, "output_tokens": 0}, "mock": True}


def score_batch(words: list[str], listing: dict, provider: str = "openrouter",
                api_key: str | None = None, timeout: int = 90, retries: int = 3) -> dict:
    """给一批词打分+分类。返回 {"answers": {...}, "usage": {...}}"""
    if provider == "mock":
        return _rules_mock(words, listing)

    cfg = PROVIDERS.get(provider)
    if not cfg:
        raise JevError(f"未知 provider：{provider}（可选 {list(PROVIDERS)} 或 mock）")
    key = api_key or os.environ.get(cfg["key_env"])
    if not key:
        raise JevError(
            f"没找到 {cfg['key_env']}。\n"
            f"  · 申请：{'openrouter.ai/settings/keys' if provider=='openrouter' else 'docs.typesafe.ai'}\n"
            f"  · 设好后 export {cfg['key_env']}=...  或写进 .env\n"
            f"  · 只想先验证流程跑得通：加 --provider mock")

    questions = {}
    for i, w in enumerate(words):
        questions[f"kw{i:04d}_score"] = {
            "type": "score",
            "instructions": f"搜索词「{w}」与本商品（参考上面提供的商品信息）的相关度有多高？",
            "criteria": LEVELS,
        }
        questions[f"kw{i:04d}_cat"] = {
            "type": "choice",
            "instructions": f"搜索词「{w}」属于下面哪一类？严格按定义选最贴切的一类。",
            "criteria": CATS,
        }

    payload = {"model": cfg["model"], "state": listing if isinstance(listing, dict) else str(listing),
               "questions": questions}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    last = None
    for attempt in range(retries):
        try:
            r = requests.post(cfg["url"], headers=headers, json=payload, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 500, 502, 503, 504):
                last = f"HTTP {r.status_code}"
                time.sleep(2 ** attempt * 1.5)
                continue
            raise JevError(f"Jev 返回 HTTP {r.status_code}：{r.text[:400]}")
        except requests.RequestException as e:
            last = str(e)[:200]
            time.sleep(2 ** attempt * 1.5)
    raise JevError(f"Jev 连续 {retries} 次失败：{last}")


def score_all(words: list[str], listing: dict, provider="openrouter", api_key=None,
              batch=60, verbose=True) -> tuple[list[dict], dict]:
    """分批打分。返回 (每词结果, 汇总统计)"""
    rows, usage_in = [], 0
    n_batch = (len(words) + batch - 1) // batch
    for b in range(n_batch):
        chunk = words[b * batch:(b + 1) * batch]
        if verbose:
            print(f"  ⏳ 第 {b+1}/{n_batch} 批（{len(chunk)} 个词，共 {len(chunk)*2} 个问题并行）…", end="", flush=True)
        t0 = time.time()
        resp = score_batch(chunk, listing, provider, api_key)
        dt = time.time() - t0
        ans = resp.get("answers", {})
        u = resp.get("usage") or {}
        usage_in += int(u.get("input_tokens") or 0)
        for i, w in enumerate(chunk):
            s_key, c_key = f"kw{i:04d}_score", f"kw{i:04d}_cat"
            s_ans = ans.get(s_key) or {}
            c_ans = ans.get(c_key) or {}
            raw = s_ans.get("score")
            rows.append({
                "term": w,
                "related_score": None if raw is None else round(float(raw) + 1, 1),  # 0–9 → 1–10
                "confidence": s_ans.get("confidence"),
                "category_key": c_ans.get("choice"),
                "category": CAT_ZH.get(c_ans.get("choice"), c_ans.get("choice") or ""),
                "action": CAT_ACTION.get(c_ans.get("choice"), ""),
                "cat_confidence": c_ans.get("confidence"),
            })
        if verbose:
            print(f" ✅ {dt:.1f}s" if not resp.get("mock") else f" ✅ {dt:.1f}s（mock）")
    stats = {"批次数": n_batch, "每批词数": batch, "输入token": usage_in,
             "估算成本USD": round(usage_in * PRICE_PER_MTOK / 1e6, 6), "provider": provider}
    return rows, stats
