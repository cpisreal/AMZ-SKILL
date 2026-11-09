#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_alerts.py — 三条硬告警规则的机读判定器（A1 / A2 / A3）

只读 state/today.json，输出告警列表 JSON。不做阶段判定、不生成文案，
文案由模型按 SKILL.md「⑥ 三条硬告警规则」的格式填写。

规则（与 SKILL.md 保持一致，改一处必须改另一处）：
    A1  7 天内任一城 tmin_f <= 32.0°F      跌破冰点（0°C），需求拐点
    A2  7 天内任一城 tmin_f <= 20.0°F      严寒
    A3  某城 delta_f <= -5.0°F             急剧降温，加热护肩直接起量信号
    A1 与 A2 同时命中时合并，以 A2 为主；A3 独立成条。

用法：
    python check_alerts.py                       # 读 state/today.json
    python check_alerts.py --in state/today.json --out state/alerts.json
"""

import argparse
import html
import json
import os
import sys

FREEZING_F = 32.0   # A1：冰点（0°C）
SEVERE_F = 20.0     # A2：严寒
DROP_F = -5.0       # A3：单城 7 天最低温较昨日跌 >= 5°F
# Anchorage 权重最低、常年最冷，按 SKILL.md 不参与美国本土起量判定，
# 故 A1/A2 只扫「本土 11 城」，锚地单独作为基线参考输出，避免常年误报。
BASELINE_ONLY = {"Anchorage"}


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def city_min(city):
    """返回该城 7 天最低温及其日期；无有效数据返回 (None, None)。"""
    days = [d for d in (city.get("days") or []) if d.get("tmin_f") is not None]
    if not days:
        return None, None
    coldest = min(days, key=lambda d: d["tmin_f"])
    return round(float(coldest["tmin_f"]), 1), coldest["date"]


def evaluate(data):
    ok = [c for c in data.get("cities", []) if "error" not in c]
    changes = data.get("changes") or {}
    baseline = changes.get("baseline_date")

    # ---- A1 / A2：扫描本土 11 城 7 天最低温（排除 Anchorage 基线城）----
    freezing, severe, baseline_only = [], [], []
    for c in ok:
        tmin, day = city_min(c)
        if tmin is None:
            continue
        row = {"city": c["city"], "state": c.get("state"), "date": day, "tmin_f": tmin}
        if c["city"] in BASELINE_ONLY:
            baseline_only.append(row)
            continue
        if tmin <= SEVERE_F:
            severe.append(row)
        elif tmin <= FREEZING_F:
            freezing.append(row)

    severe.sort(key=lambda x: x["tmin_f"])
    freezing.sort(key=lambda x: x["tmin_f"])

    alerts = []

    # ---- A3：急剧降温（无基线时跳过，严禁编造 delta）----
    a3_fired = False
    if baseline is None:
        a3_status = "skipped_no_baseline"
    else:
        drops = [d for d in (changes.get("tmin_drops") or []) if d.get("delta_f") is not None]
        drops = [d for d in drops if d["delta_f"] <= DROP_F]
        drops.sort(key=lambda x: x["delta_f"])
        if drops:
            a3_fired = True
            a3_status = "fired"
            worst = drops[0]
            alerts.append({
                "code": "A3",
                "severity": 3,
                "title": "急降告警",
                "city": worst["city"],
                "state": worst.get("state"),
                "delta_f": round(float(worst["delta_f"]), 1),
                "tmin_prev_f": worst.get("tmin_prev_f"),
                "tmin_now_f": worst.get("tmin_now_f"),
                "others": [
                    {"city": d["city"], "delta_f": round(float(d["delta_f"]), 1)} for d in drops[1:]
                ],
                "takes_p0": True,
            })
        else:
            a3_status = "not_fired"

    # ---- A2 优先；A1 与 A2 同日命中时合并进 A2 ----
    if severe:
        alerts.append({
            "code": "A2",
            "severity": 2,
            "title": "严寒告警",
            "city": severe[0]["city"],
            "state": severe[0]["state"],
            "date": severe[0]["date"],
            "tmin_f": severe[0]["tmin_f"],
            "cities": severe,
            "absorbed_a1": [x["city"] for x in freezing],
        })
    elif freezing:
        alerts.append({
            "code": "A1",
            "severity": 1,
            "title": "冰点告警",
            "city": freezing[0]["city"],
            "state": freezing[0]["state"],
            "date": freezing[0]["date"],
            "tmin_f": freezing[0]["tmin_f"],
            "cities": freezing,
        })

    return {
        "source_date": data.get("date"),
        "baseline_date": baseline,
        "thresholds": {"a1_freezing_f": FREEZING_F, "a2_severe_f": SEVERE_F, "a3_drop_f": DROP_F},
        "a1_status": "fired" if freezing or severe else "not_fired",
        "a2_status": "fired" if severe else "not_fired",
        "a3_status": a3_status,
        "a3_takes_p0": a3_fired,
        "baseline_only": baseline_only,
        "alerts": alerts,
        "alert_count": len(alerts),
        "summary_line": "今日 A1/A2/A3 均未触发" if not alerts else f"命中 {len(alerts)} 条告警：" + "、".join(a["code"] for a in alerts),
    }


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default=os.path.join(here, "..", "state", "today.json"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    src = os.path.abspath(args.src)
    if not os.path.isfile(src):
        print(f"[error] 未找到 {src}，请先运行 fetch_uk_snow.py", file=sys.stderr)
        return 2

    result = evaluate(load(src))
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
