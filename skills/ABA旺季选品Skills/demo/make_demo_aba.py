#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""造一份**演示用** ABA 周报（4 周），让 `run.py demo` 零依赖跑通全流程。

刻意造出这些特征，让新用户一眼看到工具在干什么：
  * 第 1 行是 Reporting Range 元数据 —— 不 `skip=1` 就会踩坑（演示数据保留这个坑）
  * 混入 `omen decor` / `garment steamer` / `women's stockings` —— 验证**词根边界**把它们挡掉
  * 混入 `christmas tree skirt` / `-collar` / `-topper` —— 验证**子类守卫**摘出去
  * 部分词排名 > 5000 —— 验证**有效词阈值**确实过滤掉
  * 词条数按「20 → 45 → 60 → 45」起伏 —— 验证**加速度峰早于词量顶点**（本工具的招牌结论）
  * 各产品 min_intensity 不同 —— 让**形态分类**能分出好几种形态

⚠️ 演示数据是编的，只用来验证工具跑得通，不含任何真实市场结论。
"""
from __future__ import annotations

import os
import random

WEEKS = ["2025_11_01", "2025_11_08", "2025_11_15", "2025_11_22"]
# 季节强度：决定「长尾词」从哪一周开始出现（这就是旺季长尾逐步冒出来的机制）
INTENSITY = [0.30, 0.70, 1.00, 0.70]
# 三档长尾的词数 —— 固定成 20 / 35 / 24，让演示曲线稳定呈
# 「20 → 55 → 79 → 55」，即**加速度峰(11/08)早于词量顶点(11/15) 1 周**，
# 正好演示本工具的招牌结论。改这两个数组前先想清楚曲线会变成什么样。
TAIL_SIZES = [20, 35, 24]
TAIL_THRS = [0.30, 0.70, 1.00]

# 产品 → [(词, 最小排名, 出现所需强度, 峰值周下标)]
CATALOG = {
    "圣诞树": [("christmas tree", 22, 0.30, 1), ("pre lit christmas tree", 140, 0.30, 1),
            ("flocked christmas tree", 620, 0.75, 2), ("artificial christmas tree", 900, 0.75, 2),
            ("slim christmas tree", 2400, 1.00, 2), ("pencil christmas tree", 3300, 1.00, 3),
            ("mini christmas tree", 4600, 1.00, 2), ("christmas tree 7.5 ft", 6100, 1.00, 2)],
    "灯饰": [("christmas lights", 40, 0.30, 1), ("christmas lights outdoor", 240, 0.30, 1),
           ("led christmas lights", 380, 0.75, 2), ("christmas projector lights", 2600, 0.75, 2),
           ("solar christmas lights", 3100, 1.00, 3), ("christmas net lights", 4400, 1.00, 2),
           ("christmas icicle lights", 5600, 1.00, 2), ("christmas curtain lights", 7200, 1.00, 3)],
    "挂饰": [("christmas ornaments", 70, 0.30, 1), ("personalized christmas ornaments", 640, 0.30, 1),
           ("shatterproof christmas ornaments", 1900, 0.75, 2), ("wooden christmas ornaments", 2800, 0.75, 2),
           ("christmas ornament set", 4300, 1.00, 3), ("photo christmas ornaments", 6800, 1.00, 2)],
    "圣诞袜": [("christmas stockings", 88, 0.30, 2), ("personalized christmas stockings", 520, 0.30, 2),
            ("knit christmas stockings", 2200, 0.75, 3), ("christmas stockings for kids", 1200, 0.75, 2),
            ("christmas stocking holders", 760, 0.75, 3), ("christmas stocking hanger", 1500, 1.00, 3),
            ("christmas stockings for pets", 2800, 1.00, 3), ("embroidered christmas stockings", 5400, 1.00, 2)],
    "袜内填充礼物": [("christmas stocking stuffers", 150, 0.30, 2),
                ("stocking stuffers for adults", 1700, 0.75, 2),
                ("stocking stuffers for teens", 2900, 0.75, 3),
                ("stocking stuffers under 10", 4100, 1.00, 2),
                ("christmas stocking stuffers for kids", 5200, 1.00, 3)],
    "睡衣": [("christmas pajamas", 80, 0.30, 2), ("family christmas pajamas", 260, 0.30, 2),
           ("matching christmas pajamas", 880, 0.75, 2), ("christmas pajamas for women", 1900, 0.75, 3),
           ("christmas onesie pajamas", 3600, 1.00, 2), ("christmas pajamas kids", 5800, 1.00, 3)],
    "毛衣": [("christmas sweater", 150, 0.30, 2), ("ugly christmas sweater", 700, 0.30, 2),
           ("christmas sweater women", 2100, 0.75, 2), ("christmas sweatshirt", 2600, 0.75, 3),
           ("matching christmas sweaters", 4800, 1.00, 2)],
    "贺卡": [("christmas cards", 380, 0.30, 3), ("christmas cards boxed", 1400, 0.75, 3),
           ("photo christmas cards", 1800, 0.75, 3), ("christmas card holder", 3900, 1.00, 3),
           ("christmas cards personalized", 6300, 1.00, 3)],
    "包装纸袋": [("christmas wrapping paper", 950, 0.30, 3), ("christmas gift bags", 2000, 0.75, 3),
             ("christmas tissue paper", 3700, 0.75, 3), ("christmas wrapping paper rolls", 5900, 1.00, 3)],
    "礼物盒袋": [("christmas gift boxes", 1400, 0.75, 3), ("christmas gift box with lid", 4200, 1.00, 3)],
    "装饰（泛）": [("christmas decorations", 55, 0.30, 3), ("christmas decor indoor", 780, 0.30, 3),
              ("christmas window decorations", 2500, 0.75, 3), ("christmas table decorations", 3800, 0.75, 3),
              ("christmas porch decorations", 6200, 1.00, 3)],
    "礼物（泛）": [("christmas gifts", 45, 0.30, 2), ("christmas gifts for women", 96, 0.30, 2),
              ("christmas gifts for men", 480, 0.75, 2), ("christmas gift ideas", 1100, 0.75, 2),
              ("christmas gifts for mom", 3300, 1.00, 2), ("christmas gifts for teens", 4900, 1.00, 2)],
}

# 只出现在某一周的"浪潮词"（造出加速峰早于词量顶点）
WAVE_TERMS = [
    ("christmas inflatables", 2100, 0.75), ("christmas yard decorations", 2800, 0.75),
    ("christmas blow up decorations", 4600, 1.00), ("christmas outdoor decor", 3900, 1.00),
    ("christmas garland", 340, 0.75), ("christmas wreath", 200, 0.30),
    ("christmas doormat", 2400, 1.00), ("christmas tablecloth", 3100, 1.00),
    ("christmas napkins", 3600, 1.00), ("christmas mugs", 4200, 1.00),
]

# 噪音：不含词根，或含词根但是同形异义 / 子类 —— 用来验证三道闸门
NOISE = [
    ("omen decor", 2800, 0.30),          # 不含词根 → 词根边界挡掉
    ("garment steamer", 3900, 0.30),     # 不含词根
    ("women's pajamas", 3400, 0.30),     # 不含词根
    ("christmas tree skirt", 2000, 0.30),   # 子类守卫：不属于「圣诞树」
    ("christmas tree collar", 2900, 0.30),  # 子类守卫
    ("christmas tree topper", 1000, 0.30),  # 子类守卫
    ("christmas tree storage bag", 4400, 0.75),  # 子类守卫
]

COLUMNS = [
    "Search Frequency Rank", "Search Term",
    "Top Clicked Brand #1", "Top Clicked Brands #2", "Top Clicked Brands #3",
    "Top Clicked Category #1", "Top Clicked Category #2", "Top Clicked Category #3",
    "Top Clicked Product #1: ASIN", "Top Clicked Product #1: Product Title",
    "Top Clicked Product #1: Click Share", "Top Clicked Product #1: Conversion Share",
    "Top Clicked Product #2: ASIN", "Top Clicked Product #2: Product Title",
    "Top Clicked Product #2: Click Share", "Top Clicked Product #2: Conversion Share",
    "Top Clicked Product #3: ASIN", "Top Clicked Product #3: Product Title",
    "Top Clicked Product #3: Click Share", "Top Clicked Product #3: Conversion Share",
    "Reporting Date",
]

BRANDS = ["Brightown", "Dazzle Bright", "Minetom", "Hallmark", "Amscan", "Best Choice",
          "Kurt Adler", "National Tree"]
CATS = ["Home & Kitchen", "Tools & Home Improvement", "Toys & Games", "Clothing",
        "Health & Household"]


def _q(v):
    s = "" if v is None else str(v)
    return '"' + s.replace('"', '""') + '"' if ("," in s or '"' in s) else s


def build_demo(out_dir: str, seed: int = 11):
    rnd = random.Random(seed)
    os.makedirs(out_dir, exist_ok=True)

    entries = []   # (词, 最小排名, 强度阈值, 峰值周)
    ti = 0
    for prod, items in CATALOG.items():
        for term, base, thr, pk in items:
            entries.append((ti, prod, term, base, thr, pk)); ti += 1
    for term, base, thr in WAVE_TERMS:
        entries.append((ti, "装饰（泛）", term, base, thr, 2)); ti += 1
    for term, base, thr in NOISE:
        entries.append((ti, "_noise", term, base, thr, 1)); ti += 1

    # ── 确定性地把「出现强度」重分成三档（词数固定 20/35/24）──
    # 不这么做的话，每个季节各档词的数量是随机的，演示曲线会飘，
    # 「加速峰早于词量顶点」这个核心结论有时候就演示不出来。
    entries.sort(key=lambda e: (e[4], e[3], e[2]))
    reshaped = []
    k = 0
    for size, thr in zip(TAIL_SIZES, TAIL_THRS):
        for e in entries[k:k + size]:
            reshaped.append((e[0], e[1], e[2], e[3], thr, e[5]))
        k += size
    for e in entries[k:]:                       # 多出来的照旧
        reshaped.append(e)
    entries = reshaped

    written = []
    for wi, wk in enumerate(WEEKS):
        inten = INTENSITY[wi]
        rows = []
        for (idx, prod, term, base, thr, pk) in entries:
            if inten < thr:
                continue                      # 长尾还没冒出来
            # 排名随强度"变热"（数字变小），峰值周附近最热，再加大幅抖动
            dist = abs(wi - pk)
            rank = max(1, int(base * (1 + 0.45 * dist) * rnd.uniform(0.72, 1.35)))
            rows.append((rank, term, idx))
        rows.sort(key=lambda x: x[0])

        path = os.path.join(out_dir, f"ABA_demo_week_{wk}.csv")
        with open(path, "w", encoding="utf-8-sig", newline="") as fh:
            fh.write(f'"Reporting Range","{wk} - 7 days"\n')   # ← 坑：第一行不是表头
            fh.write(",".join(COLUMNS) + "\n")
            for rank, term, idx in rows:
                b = BRANDS[idx % len(BRANDS)]
                c = CATS[idx % len(CATS)]
                asins = [f"B0DEMO{idx:03d}{k}" for k in (1, 2, 3)]
                rnd.shuffle(asins)
                row = [rank, term, b, BRANDS[(idx + 1) % len(BRANDS)],
                       BRANDS[(idx + 2) % len(BRANDS)], c,
                       CATS[(idx + 1) % len(CATS)], CATS[(idx + 2) % len(CATS)]]
                for k, a in enumerate(asins):
                    row += [a, f"{b} {term.title()} Model {k+1}",
                            f"{20 + k * 5}.50%", f"{10 + k * 4}.25%"]
                row += [wk]
                fh.write(",".join(_q(v) for v in row) + "\n")
        written.append(path)
    return written


if __name__ == "__main__":
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "aba")
    for p in build_demo(d):
        print("生成", p)
