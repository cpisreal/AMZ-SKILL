#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""造一份**演示用**的 ABA 热搜词报告，用来先把流程跑通（不含任何真实数据）。

会生成：
  demo/aba/ABA_US_2026-08-07.csv     英文表头
  demo/aba/ABA_US_2026-08-14.csv     英文表头
  demo/aba/ABA_US_2026-08-21.csv     中文表头（用来验证表头自适应）
  demo/asins.txt                     3 个竞品 ASIN
  demo/listing.json                  目标 ASIN 的 Listing（跳过爬取）

真跑自己的数据时，把 --aba-dir 换成你后台下载的 ABA 报告目录即可。
"""
import json
import random
from pathlib import Path

random.seed(42)
HERE = Path(__file__).resolve().parent
ABA = HERE / "aba"
ABA.mkdir(parents=True, exist_ok=True)

TARGET = "B0DEMOTGT1"
COMPS = ["B0DEMO0001", "B0DEMO0002", "B0DEMO0003"]
OTHER = ["B0OTHER001", "B0OTHER002", "B0OTHER003", "B0OTHER004", "B0OTHER005"]

WEEKS = [
    ("2026-08-01", "2026-08-07", "20260807", False),
    ("2026-08-08", "2026-08-14", "20260814", False),
    ("2026-08-15", "2026-08-21", "20260821", True),      # 中文表头
]

# ── 词库 ──────────────────────────────────────────────────────────────
CATEGORY = ["ice maker", "countertop ice maker", "ice machine", "nugget ice maker",
            "portable ice maker", "counter top ice maker", "ice maker machine",
            "ice makers countertop", "small ice maker", "pellet ice maker",
            "clear ice maker", "ice maker for kitchen", "electric ice maker"]
OWN = ["euhomy ice maker", "euhomy countertop ice maker", "euhomy nugget ice maker",
       "euhomy ice machine"]
COMP = ["ge opal nugget ice maker", "gevi ice maker", "silonn ice maker", "ge opal 2.0",
        "oraimo ice maker", "kismile ice maker", "agptek ice maker", "northair ice maker",
        "crownful ice maker", "ecozy ice maker", "free village ice maker", "antartic star ice maker"]
ATTR = ["stainless steel ice maker", "mini ice maker countertop", "black ice maker",
        "white ice maker", "44 lb ice maker", "26 lb ice maker", "35 lb ice maker",
        "self cleaning ice maker", "ice maker with scoop", "quiet ice maker",
        "bullet ice maker", "square ice maker", "under counter ice maker", "24 inch ice maker"]
SCEN = ["ice maker for home", "ice maker for rv", "ice maker for party", "ice maker for camping",
        "ice maker for office", "ice maker for dorm", "ice maker for bar", "ice maker for boat",
        "ice maker for outdoor", "ice maker for apartment", "ice maker for rv camping"]
LONG = ["nugget ice maker countertop self cleaning", "countertop ice maker stainless steel 44lb",
        "portable ice maker for rv with scoop", "nugget ice maker for home kitchen",
        "ice maker machine countertop portable", "countertop ice maker black 26lb",
        "ice maker for home bar party", "small countertop ice maker bullet ice",
        "ice maker with self cleaning function", "countertop ice machine nugget ice"]
ALL_WORDS = CATEGORY + OWN + COMP + ATTR + SCEN + LONG

# 每个词的「基础排名」（越小越热），模拟真实分布
BASE = {}
for i, w in enumerate(CATEGORY):
    BASE[w] = 180 + i * 900
for i, w in enumerate(OWN):
    BASE[w] = 18000 + i * 3200
for i, w in enumerate(COMP):
    BASE[w] = 42000 + i * 4200
for i, w in enumerate(ATTR):
    BASE[w] = 2400 + i * 700
for i, w in enumerate(SCEN):
    BASE[w] = 1500 + i * 600
for i, w in enumerate(LONG):
    BASE[w] = 8000 + i * 1500
BASE["countertop ice maker"] = 5673
BASE["ice maker"] = 182
BASE["ge opal nugget ice maker"] = 83672
BASE["euhomy ice maker"] = 29707

# 哪些词会被「竞品 ASIN 反向命中」——模拟真实情况：热门品类词和竞品品牌词挂的是竞品 ASIN
HITMAP = {}
for w in ALL_WORDS:
    r = random.random()
    if w in CATEGORY and r < 0.75:
        HITMAP[w] = random.sample(COMPS, random.choice([1, 1, 2]))
    elif w in COMP and r < 0.65:
        HITMAP[w] = random.sample(COMPS, 1)
    elif w in ATTR and r < 0.55:
        HITMAP[w] = random.sample(COMPS, random.choice([1, 2]))
    elif w in SCEN and r < 0.5:
        HITMAP[w] = random.sample(COMPS, 1)
    elif w in LONG and r < 0.45:
        HITMAP[w] = random.sample(COMPS, 1)
    elif w in OWN:
        # 自有品牌词：正常是自己在 #1，但竞品常来 #2/#3 抢流量 → 这样才会被反向命中
        HITMAP[w] = [TARGET] if random.random() < 0.4 else [TARGET, random.choice(COMPS)]
    elif r < 0.25:
        HITMAP[w] = random.sample(OTHER, 1)

WARN = "本文档数据为演示用合成数据，不代表任何真实市场情况。"


def header(cn: bool) -> list[str]:
    if not cn:
        h = ["Search Frequency Rank", "Search Term"]
        for i in (1, 2, 3):
            h += [f"Top Clicked Product #{i}: ASIN", f"Top Clicked Product #{i}: Product Title",
                  f"Top Clicked Product #{i}: Click Share", f"Top Clicked Product #{i}: Conversion Share"]
        return h
    h = ["搜索频率排名", "搜索词"]
    for i in (1, 2, 3):
        h += [f"点击量最高的商品 #{i}: ASIN", f"点击量最高的商品 #{i}: 商品名称",
              f"点击量最高的商品 #{i}: 点击份额", f"点击量最高的商品 #{i}: 转化份额"]
    return h


def title_of(asin: str) -> str:
    m = {"B0DEMO0001": "GE Profile Opal 2.0 Nugget Ice Maker with Side Tank",
         "B0DEMO0002": "Gevi Household Countertop Nugget Ice Maker 44Lbs",
         "B0DEMO0003": "Silonn Countertop Ice Maker Machine 9 Cubes 6 Mins",
         "B0DEMOTGT1": "EUHOMY Countertop Ice Maker 26Lbs Bullet Ice"}
    return m.get(asin, f"Generic Ice Maker {asin}")


def write_week(start, end, tag, cn: bool, wk: int):
    f = ABA / f"ABA_US_{tag}.csv"
    lines = [f"Reporting Range={start} - {end}"]
    lines.append(",".join(f'"{h}"' for h in header(cn)))
    for w in ALL_WORDS:
        rank = max(1, int(BASE[w] * (1 + random.uniform(-0.12, 0.12)) * (1 - 0.03 * wk)))
        slots = HITMAP.get(w, [])
        row = [str(rank), f'"{w}"']
        for i in range(3):
            if i < len(slots):
                a = slots[i]
                share = round(random.uniform(8, 34), 2)
                row += [a, f'"{title_of(a)}"', f"{share}%", f"{round(share*0.6,2)}%"]
            else:
                row += ["", "", "", ""]
        lines.append(",".join(row))
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f, len(ALL_WORDS)


if __name__ == "__main__":
    print(WARN)
    for wk, (s, e, tag, cn) in enumerate(WEEKS):
        f, n = write_week(s, e, tag, cn, wk)
        print(f"  ✅ {f.relative_to(HERE.parent)}  {n} 词  {'中文表头' if cn else '英文表头'}")
    (HERE / "asins.txt").write_text("\n".join(COMPS) + "\n", encoding="utf-8")
    listing = {
        "asin": TARGET, "url": f"https://www.amazon.com/dp/{TARGET}",
        "title": "EUHOMY Countertop Ice Maker Machine 26Lbs in 24Hrs, 9 Bullet Ice Ready in 6 Mins, "
                 "Portable Ice Maker with Scoop and Basket, Self-Cleaning, for Home Kitchen Office Bar RV",
        "brand": "EUHOMY", "category": "Home & Kitchen > Kitchen & Dining > Small Appliances > Ice Makers",
        "bullets": [
            "Fast Ice Making in 6 Minutes: 9 bullet-shaped ice cubes ready in 6 minutes, up to 26 lbs in 24 hours.",
            "Compact & Portable: 8.7 x 12.3 x 12.6 inches, only 17.6 lbs. Fits on any countertop, easy to carry for RV and camping.",
            "Self-Cleaning Function: press the button for 5 seconds to clean the interior automatically.",
            "Two Ice Sizes & Bullet Ice: choose small or large bullet ice. Bullet ice melts slower and fits bottles and cups better.",
            "Quiet & Energy Saving: runs at under 40dB. Includes ice scoop, ice basket and removable filter.",
        ],
        "description": "EUHOMY countertop ice maker produces bullet ice in 6 minutes. Perfect for home "
                       "kitchen, office, bar, RV and party use. 26 lbs per day, self-cleaning, quiet operation.",
        "bsr": "#2,341 in Ice Makers", "price_raw": "$129.99", "currency": "US$",
    }
    (HERE / "listing.json").write_text(json.dumps(listing, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ demo/asins.txt  demo/listing.json")
    print("\n现在跑：python run.py --aba-dir ./demo/aba --asins ./demo/asins.txt "
          f"--target {TARGET} --provider mock --out ./成品_演示词表.xlsx")
