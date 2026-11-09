#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""离线自检：不需要联网、不需要 key。

跑通「示例数据 → 统计 → 图表 → 报告」，并核对文章口径（250 帖 / 1,785 评论 / 81 万字）。
退出码 0 = 全部通过；1 = 有失败项。

    python 自检.py
"""
import glob
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

OK = 0
FAIL = 0


def check(name, cond, extra=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} {extra}")


def read(f):
    with open(os.path.join(HERE, f), encoding="utf-8") as fh:
        return fh.read()


print("=" * 60)
print("Reddit 品类调研 Skills · 离线自检")
print("=" * 60)

print("\n[1] 示例数据完整性")
data = json.loads(read("demo/data.json"))
posts = data["posts"]
check("示例数据可解析", isinstance(posts, list) and len(posts) > 0)
check("帖子数 = 250（与文章一致）", len(posts) == 250, f"实际 {len(posts)}")
n_cmt = sum(len(p.get("comments") or []) for p in posts)
check("评论数 = 1,785（与文章一致）", n_cmt == 1785, f"实际 {n_cmt}")
n_title = sum(len(p.get("title") or "") for p in posts)
n_body = sum(len(p.get("selftext") or "") for p in posts)
n_body_c = sum(len(c["body"]) for p in posts for c in (p.get("comments") or []))
total = n_title + n_body + n_body_c
check("总字数 = 810,652（标题+正文+评论，与文章 81 万字一致）", total == 810652, f"实际 {total:,}")

print("\n[2] 防静默失败（文章里踩过的坑）")
check("采集脚本内建「结果数量自检」", "帖子为 0" in read("collect.py"))
check("采集脚本内建代理提示", "HTTPS_PROXY" in read("collect.py"))

print("\n[3] 统计 / 图表 / 报告链路（真跑，不 mock）")
import shutil
import tempfile

out = tempfile.mkdtemp(prefix="reddit_selfcheck_")
import analyze  # noqa: E402
import charts  # noqa: E402
import report  # noqa: E402

stats = analyze.main(os.path.join(HERE, "demo", "data.json"), out)
need = ("total_posts", "total_comments", "total_chars", "title_chars",
        "subreddit_dist", "comment_buckets", "score_buckets", "angle_freq", "top_words")
check("统计字段完整", all(k in stats for k in need),
      str([k for k in need if k not in stats]))
check("社区分布 = 4 个社区", len(stats["subreddit_dist"]) == 4,
      str(list(stats["subreddit_dist"])))
check("评论长尾分桶合计 = 250", sum(stats["comment_buckets"].values()) == 250)
check("热度分桶合计 = 250", sum(stats["score_buckets"].values()) == 250)
check("高频词 Top 25", len(stats["top_words"]) == 25)
import warnings
with warnings.catch_warnings(record=True) as _rec:
    warnings.simplefilter("always")
    charts.main(os.path.join(HERE, "demo", "data.json"), out)
_missing = [str(w.message) for w in _rec if "missing from font" in str(w.message)]
check("中文渲染零缺字告警（字体真生效）", not _missing, f"{len(_missing)} 条缺字")
pngs = sorted(glob.glob(os.path.join(out, "charts", "*.png")))
check("图表生成 5 张", len(pngs) == 5, f"实际 {len(pngs)}")
check("每张图非空（>5KB）", all(os.path.getsize(p) > 5000 for p in pngs))
report.main(os.path.join(HERE, "demo", "data.json"), out)
md = open(os.path.join(out, "report.md"), encoding="utf-8").read()
for kw in ("数据规模", "社区分布", "评论长尾", "数据局限"):
    check(f"报告含「{kw}」章节", kw in md)

print("\n[4] 图表排版验收（主标题 ↔ 副标题墨迹净间距 ≥ 8px）")


def _dilate(m, r):
    o = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return o


def _gap(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(int)
    top = int(a.shape[0] * 0.30)
    dark = np.abs(a - np.array([11, 18, 32])).sum(2) < 90
    gray = np.abs(a - np.array([107, 114, 128])).sum(2) < 90
    gray = gray & ~_dilate(dark, 3)

    def band(mask):
        prof = mask[:top].sum(1)
        if prof.max() == 0:
            return None
        rows = np.where(prof > max(3, prof.max() * 0.10))[0]
        out = []
        for y in rows:
            if out and y - out[-1][1] <= 1:
                out[-1][1] = y
            else:
                out.append([y, y])
        return out

    d, g = band(dark), band(gray)
    if not d or not g:
        return None
    tb = max(d, key=lambda x: x[1] - x[0])
    below = [b for b in g if b[0] > tb[1]]
    return None if not below else min(below, key=lambda x: x[0])[0] - tb[1]


for p in pngs:
    g = _gap(p)
    check(f"{os.path.basename(p)} 行距 {g}px", g is None or g >= 8)

print("\n[5] 随包示例成品")
check("示例报告存在", os.path.exists(os.path.join(HERE, "demo", "成品_示例报告.md")))
check("示例图 5 张", len(glob.glob(os.path.join(HERE, "demo", "charts", "*.png"))) == 5)
check("示例统计存在", os.path.exists(os.path.join(HERE, "demo", "成品_stats.json")))

print("\n[6] 隐私自检（公开交付件必须全脱敏）")
src = "".join(read(f) for f in ("collect.py", "analyze.py", "charts.py",
                                "report.py", "main.py", "run.py"))
bad = [t for t in ("127.0.0.1:78", "xiaolingfei", "/Users/", "FEISHU_APP", "sk-", "open.feishu.cn")
       if t in src]
check("源码无代理端口/用户名/绝对路径/密钥/内部接口", not bad, str(bad))

shutil.rmtree(out, ignore_errors=True)
print("\n" + "=" * 60)
print(f"结果：{OK} 项通过，{FAIL} 项失败")
print("=" * 60)
sys.exit(1 if FAIL else 0)
