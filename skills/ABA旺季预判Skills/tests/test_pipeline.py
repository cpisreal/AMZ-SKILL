#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""不依赖任何真实数据的自检：核心口径与算法。

跑法：python tests/test_pipeline.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from abagrow import pipeline, schema  # noqa: E402

PASS, FAIL = [], []


def check(name, got, want):
    if got == want:
        PASS.append(name)
        print(f"  ✅ {name}: {got}")
    else:
        FAIL.append(name)
        print(f"  ❌ {name}: got={got!r} want={want!r}")


def test_root_condition():
    """坑四：men 不能误伤 womens。"""
    import duckdb
    con = duckdb.connect()
    con.execute("CREATE TABLE t(term VARCHAR)")
    con.executemany("INSERT INTO t VALUES (?)", [
        ("christmas pajamas for men",), ("mens christmas pajamas",),
        ("womens christmas pajamas",), ("women christmas pajamas",),
        ("christmas pajamas",), ("men",),
    ])
    got = sorted(r[0] for r in con.execute(
        f"SELECT term FROM t WHERE {pipeline.root_condition('men')}").fetchall())
    want = ["christmas pajamas for men", "men"]   # mens 不该被 men 吃掉
    check("词根 men 不吃 mens（womens/mens 都不是 men）", got, want)

    got1 = sorted(r[0] for r in con.execute(
        f"SELECT term FROM t WHERE {pipeline.root_condition('mens')}").fetchall())
    check("要覆盖 mens 就把 mens 写进变体", got1, ["mens christmas pajamas"])

    got2 = sorted(r[0] for r in con.execute(
        f"SELECT term FROM t WHERE {pipeline.root_condition('women')}").fetchall())
    check("词根 women 不命中 womens（拼写变体要单独写）", got2, ["women christmas pajamas"])
    con.close()


def test_accel():
    check("一阶差分长度 = n-1", len(pipeline.accel_of([1, 3, 6, 10])), 3)
    check("一阶差分值", pipeline.accel_of([1, 3, 6, 10]), [2, 3, 4])


def test_turning_points():
    weeks = ["w1", "w2", "w3", "w4", "w5"]
    seq = [10, 50, 90, 95, 20]          # 加速度 40,40,5,-75
    tp = pipeline.turning_points(seq, weeks)
    check("进场点 = 加速度峰（并列取最早）", tp["进场点"], "w2")
    check("加码点 = 词量峰", tp["加码点"], "w4")
    check("撤退点 = 加速度最低", tp["撤退点"], "w5")
    check("进场加速度", tp["进场点加速度"], 40)
    check("撤退加速度", tp["撤退点加速度"], -75)


def test_classify():
    weeks = [f"w{i}" for i in range(12)]
    early = [10, 90, 200, 120, 60, 30, 20, 12, 8, 5, 3, 2]
    slow = [10, 40, 90, 140, 190, 220, 250, 270, 280, 285, 282, 276]
    sync = [10, 40, 90, 140, 190, 220, 250, 270, 280, 230, 90, 20]
    zero = [0] * 12
    check("早衰型", pipeline.classify(early, weeks), "早衰")
    check("慢衰减型", pipeline.classify(slow, weeks), "慢衰减")
    check("同步型", pipeline.classify(sync, weeks), "同步")
    check("零需求型", pipeline.classify(zero, weeks), "零需求")


def test_week_files():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = os.path.join(here, "demo", "data")
    if not os.path.isdir(d):
        print("  ⏭  跳过 week_files（demo 数据还没生成，先跑 run.py demo）")
        return
    files = schema.week_files(d)
    check("周文件个数", len(files), 12)
    check("首周", files[0][0], "2025_10_18")
    check("末周", files[-1][0], "2026_01_03")
    check("label 格式", schema.label_of("2025_11_08"), "11/08")


if __name__ == "__main__":
    print("== 词根边界 =="); test_root_condition()
    print("== 加速度 =="); test_accel()
    print("== 三个时间点 =="); test_turning_points()
    print("== 属性形态 =="); test_classify()
    print("== 周文件 =="); test_week_files()
    print(f"\n通过 {len(PASS)} / 失败 {len(FAIL)}")
    if FAIL:
        print("失败项：" + "、".join(FAIL))
        sys.exit(1)
