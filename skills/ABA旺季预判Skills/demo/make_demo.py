#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自造 12 周演示数据：零依赖试跑用，故意埋了四个坑。

埋的坑：
1. `womens winter coat` 这类词含 "mens" 子串 —— 只有用「空格包裹」的词根匹配
   才不会把女士词误判成男士词（对应 README 坑四）。
2. `gift` 属性整季为 0 —— 演示「零需求属性直接砍掉」。
3. `ski` 场景早衰（峰值在第 3 周，之后一路掉）。
4. `wool` 材质慢衰减（尾周还有峰值的 85%）。

同时还验证两件事：
- CSV 第一行是元数据（不 skip=1 会整列错位）；
- ABA 的 21 列里只有 5 列会被用到（列裁剪）。
"""
from __future__ import annotations

import os

WEEKS = ["2025_10_18", "2025_10_25", "2025_11_01", "2025_11_08", "2025_11_15", "2025_11_22",
         "2025_11_29", "2025_12_06", "2025_12_13", "2025_12_20", "2025_12_27", "2026_01_03"]

HEADER = ["Search Frequency Rank", "Search Term",
          "Top Clicked Brand #1", "Top Clicked Brands #2", "Top Clicked Brands #3",
          "Top Clicked Category #1", "Top Clicked Category #2", "Top Clicked Category #3",
          "Top Clicked Product #1: ASIN", "Top Clicked Product #1: Product Title",
          "Top Clicked Product #1: Click Share", "Top Clicked Product #1: Conversion Share",
          "Top Clicked Product #2: ASIN", "Top Clicked Product #2: Product Title",
          "Top Clicked Product #2: Click Share", "Top Clicked Product #2: Conversion Share",
          "Top Clicked Product #3: ASIN", "Top Clicked Product #3: Product Title",
          "Top Clicked Product #3: Click Share", "Top Clicked Product #3: Conversion Share",
          "Reporting Date"]

# 每个词根一条 12 周词量曲线（演示用，手写）
CURVES = {
    # 主款式：中后期见顶
    "puffer":   [12, 46, 128, 268, 392, 438, 482, 506, 512, 421, 176, 58],
    "parka":    [8, 30, 86, 190, 288, 330, 372, 396, 402, 330, 140, 46],
    "long":     [6, 24, 70, 160, 240, 282, 316, 340, 348, 286, 120, 40],
    "hooded":   [5, 20, 58, 132, 200, 236, 268, 288, 294, 240, 100, 34],
    # 人群
    "womens":   [10, 38, 104, 214, 316, 356, 392, 418, 424, 348, 146, 48],
    "men":      [3, 9, 22, 44, 62, 72, 80, 88, 90, 74, 30, 10],
    "kids":     [7, 26, 72, 150, 222, 252, 280, 300, 306, 250, 104, 34],
    "baby":     [3, 12, 34, 70, 104, 118, 130, 140, 142, 116, 48, 16],
    # 材质：慢衰减（尾周还很高）
    "wool":     [10, 30, 70, 122, 180, 218, 258, 280, 292, 288, 276, 250],
    "down":     [8, 26, 62, 110, 160, 194, 230, 250, 260, 256, 240, 210],
    "fleece":   [4, 14, 34, 62, 90, 108, 128, 140, 144, 132, 96, 60],
    # 场景：早衰（第 3 周见顶后一路掉）
    "ski":      [22, 74, 168, 210, 148, 92, 54, 30, 16, 9, 4, 2],
    "travel":   [6, 20, 48, 88, 126, 150, 172, 184, 190, 158, 70, 24],
    # 促销
    "deal":     [4, 16, 40, 78, 118, 210, 260, 190, 96, 40, 16, 6],
    "sale":     [3, 12, 30, 58, 88, 168, 214, 150, 74, 30, 12, 5],
}

# 词面模板：同一个词根展开成多个真实感的搜索词
PATTERNS = ["{w} winter coat", "winter coat {w}", "{w} coat", "{w} winter coat for women"]

ASINS = [f"B0DEMO{i:04d}" for i in range(1, 13)]


def _terms_for(root: str, week_i: int) -> list[str]:
    return [p.format(w=root) for p in PATTERNS]


def build_demo(out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    written = 0
    for wi, week in enumerate(WEEKS):
        rows, rid = [], 0
        rdate = week.replace("_", "-")
        for root, curve in CURVES.items():
            need = curve[wi]
            terms = _terms_for(root, wi)
            if need <= 0:
                continue
            for j in range(need):
                term = f"{terms[j % len(terms)]} {j // len(terms) + 1 if j >= len(terms) else ''}".strip()
                rid += 1
                # 热门词把流量分给前几个 demo ASIN，让「种子 ASIN」稳定
                a = [ASINS[(rid + k) % 4] for k in range(3)] if rid % 7 else \
                    [ASINS[(rid + k) % 10] for k in range(3)]
                rank = 100 + rid
                rows.append([rank, term,
                             "DemoBrand", "DemoBrand", "DemoBrand",
                             "Clothing", "Clothing", "Clothing",
                             a[0], f"{root} winter coat product", "0.32", "0.18",
                             a[1], f"{root} coat", "0.21", "0.11",
                             a[2], f"{root} winter item", "0.14", "0.07",
                             rdate])
        path = os.path.join(out_dir, f"US_Top_Search_Terms_Simple_Week_{week}.csv")
        with open(path, "w", encoding="utf-8", newline="") as f:
            # 坑一：第一行不是表头，是元数据
            f.write(f"Reporting Range={rdate} - {rdate}\n")
            f.write(",".join(HEADER) + "\n")
            for r in rows:
                f.write(",".join(str(x).replace(",", " ") for x in r) + "\n")
        written += 1
    print(f"  演示数据已生成：{written} 个周文件 → {os.path.abspath(out_dir)}", flush=True)
    return out_dir


if __name__ == "__main__":
    build_demo(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
