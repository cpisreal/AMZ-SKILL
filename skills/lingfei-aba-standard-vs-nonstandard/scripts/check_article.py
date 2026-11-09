#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公众号成稿自检：字数 / 冒号小标题 / 数据点 / 配图 / 红线词 / 每节是否有图。

用法: python3 check_article.py <文章.md>
口径（广告类深度文）: 中文 ≥4000、冒号小标题 ≥25、百分比数据点 ≥6、每个 ## 大节至少 1 图。
"""
import re
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
lines = s.split("\n")

title = lines[0].lstrip("# ").strip()
# 正文 = 到「附送 Skills / 领取段」之前，避免把引流块算进字数
body = re.split(r"###?\s*附送\s*Skills|###?\s*领取", s)[0]
zh = len(re.findall(r"[\u4e00-\u9fff]", body))
word = zh + len(re.findall(r"[A-Za-z0-9]+(?:\.[0-9]+)?%?", body))

colon = [l for l in body.split("\n") if l.startswith("**") and "：" in l[:40]]
pcts = re.findall(r"\d[\d,\.]*\s*%", body)
imgs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", s)
h2 = [l for l in s.split("\n") if l.startswith("## ")]

print(f"标题（{len(title)} 字）：{title}")
print(f"  含问号：{'是（❌）' if ('？' in title or '?' in title) else '否 ✓'}")
print(f"中文字数（不含领取段）：{zh}   {'✓ ≥4000' if zh >= 4000 else '❌ <4000'}")
print(f"Word 口径：{word}")
print(f"一级大节：{len(h2)} 个 → {[x[3:] for x in h2]}")
print(f"冒号小标题：{len(colon)} 个 {'✓ ≥25' if len(colon) >= 25 else '❌ <25'}")
print(f"百分比数据点：{len(pcts)} 个 {'✓ ≥6' if len(pcts) >= 6 else '❌ <6'}")
print(f"配图：{len(imgs)} 张")
for i in imgs:
    print("   -", i)

bad = [w for w in ("内部竞争", "综合整理自", "参考竞品", "据外媒", "行业公开数据") if w in s]
print(f"红线词：{bad if bad else '无 ✓'}")

for sec in re.split(r"\n## ", s)[1:]:
    name = sec.split("\n")[0][:24]
    n = len(re.findall(r"!\[[^\]]*\]\(", sec))
    print(f"   {name:26} 图 {n} 张 {'✓' if n >= 1 else '⚠️ 无图'}")
