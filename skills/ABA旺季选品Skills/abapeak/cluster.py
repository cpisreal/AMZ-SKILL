# -*- coding: utf-8 -*-
"""口径 ③ ⑥：产品实体聚类 + 子类语义甄别。

一个方向词扫出来的是**词**，不是**产品**。必须把词归到产品实体上，否则
「christmas stocking」和「christmas stocking stuffers」会被当成同一个东西 ——
而后者其实是个独立产品（袜内填充礼物），机会完全不同。

三条必须遵守的规则：

1. **子类守卫（subclass_guards）排在父类之前**
   否则 `christmas tree skirt` 被 `tree` 吃掉，变成"圣诞树"的一部分。
   树裙和树是两种生意（一个软一个硬、一个能卷起来一个不能）。

2. **同形异义必须显式剔除（ambiguity）**
   `stockings` 在英文里同时是"圣诞袜"和"女性丝袜"。不剔除的话，
   AB 站的常青款丝袜会把圣诞袜的量级灌爆 —— 这是 ABA 词分析的通病，
   **任何种子词都要过一遍人工甄别**，不存在全自动的正确规则。

3. **产品按规则表顺序匹配，首个命中生效**
   所以表里"越具体的越靠前"。

规则存在 JSON 规则包里（`rules/*.json`），换季节只换规则包，不动代码。
"""
from __future__ import annotations

import json
from pathlib import Path

RULES_DIR = Path(__file__).resolve().parent / "rules"


class Classifier:
    def __init__(self, pack: dict):
        self.pack = pack
        self.name = pack.get("name", "generic")
        self.label = pack.get("label", self.name)
        self.guards = [g.lower() for g in pack.get("subclass_guards", [])]
        self.ambiguity = [a.lower() for a in pack.get("ambiguity", [])]
        self.products = [(p["name"], [k.lower() for k in p["match"]]) for p in pack["products"]]
        # 任何注释字段（以 _ 开头）都允许存在，方便规则包自解释
        self.notes = {k: v for k, v in pack.items() if k.startswith("_")}

    def __call__(self, term: str):
        tl = (term or "").lower()
        if not tl:
            return None
        for g in self.guards:                      # ① 子类守卫
            if g in tl:
                return None
        for a in self.ambiguity:                   # ② 同形异义
            if a in tl:
                return None
        for name, keys in self.products:           # ③ 首个命中
            if any(k in tl for k in keys):
                return name
        return None

    def subclasses_of(self, terms, parent: str):
        """子类下钻：把落在 parent 里的词，按规则包给的子类关键词再分一层。

        返回 {子类名: [词...]}，未命中的归到「其他」。
        """
        keys = []
        for p in self.pack["products"]:
            if p["name"] == parent:
                keys = [k.lower() for k in p.get("subclasses", [])]
                break
        buckets = {}
        for t in terms:
            tl = t.lower()
            hit = next((k for k in keys if k in tl), "其他")
            buckets.setdefault(hit, []).append(t)
        return dict(sorted(buckets.items(), key=lambda kv: -len(kv[1])))


def load_pack(name_or_path) -> dict:
    """按名字加载内置规则包，或直接传 JSON 路径。"""
    p = Path(name_or_path)
    if not p.exists():
        p = RULES_DIR / f"{name_or_path}.json"
    if not p.exists():
        avail = sorted(x.stem for x in RULES_DIR.glob("*.json"))
        raise FileNotFoundError(f"规则包不存在：{name_or_path}｜内置可选：{avail}")
    return json.loads(p.read_text(encoding="utf-8"))


def classifier_for(name_or_path) -> Classifier:
    return Classifier(load_pack(name_or_path))


def available_packs():
    return sorted(x.stem for x in RULES_DIR.glob("*.json"))


def new_pack(template="generic") -> str:
    """给用户看"怎么加一个新季节"的最小骨架。"""
    pack = load_pack(template)
    return json.dumps(pack, ensure_ascii=False, indent=2)
