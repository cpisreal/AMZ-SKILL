# -*- coding: utf-8 -*-
"""口径 ④ 的"最后一公里"：把分析转成决策表 + Excel/Markdown 报告。

分析给的是**事实**（加速峰 11/08），决策要的是**动作**（10 月中必须完成到仓）。
这一层就是那张转换表 —— 每个指标都必须对应一个动作，否则这个指标无效。
"""
from __future__ import annotations

import json

from .rhythm import SHAPE_ACTION, six_dimensions, detect_turning_points

# 维度 → 决策动作（"分析的终点 = 决策的起点"）
DECISION_MAP = [
    ("加速峰（起量时间）", "加速峰前 1–2 周完成上架，加速峰当周广告开跑"),
    ("加速值（起量速度）", "急涨型猛推；慢热型养节奏、拉长投放窗"),
    ("12 周词条总量（量级）", "决定投入资源量级：量级大才值得压库存"),
    ("节奏形态", "决定备货深度：脉冲型小批量多款，缓降型可深备"),
    ("尾周占比", "决定库存风险：尾周高 → 节后还能收；尾周低 → 必须提前清"),
    ("半衰期", "决定清货节奏：半衰期 1 周 = 清货窗口极短"),
]


def build_report(scan_result, deep_result=None, top_n=20):
    """把 scan/deep 的结果合成一份可交付的报告结构。"""
    weeks = scan_result["weeks"]
    labels = [w[5:].replace("_", "/") for w in weeks]
    seq = [scan_result["week_records"][w] for w in weeks]
    market = detect_turning_points(seq, labels)

    rows = []
    for p in scan_result["products"][:top_n]:
        seq_p = [p["week_terms"].get(w, 0) for w in weeks]
        dim = six_dimensions(seq_p, labels)
        row = {
            "product": p["product"],
            "total_terms": p["total_terms"],
            "unique_terms": p["unique_terms"],
            **{k: v for k, v in dim.items() if k != "seq"},
        }
        if deep_result and p["product"] in deep_result:
            d = deep_result[p["product"]]
            row["head3_share"] = d["head3_share"]
            row["n_asins"] = d["n_asins"]
            row["top_brands"] = d["top_brands"][:3]
            row["top_asins"] = d["top_asins"][:3]
        rows.append(row)

    return {
        "label": scan_result.get("label"),
        "roots": scan_result["roots"],
        "weeks": weeks,
        "labels": labels,
        "week_records": seq,
        "market": market,
        "total_records": scan_result["total_records"],
        "unique_terms": scan_result["unique_terms"],
        "valid_terms": scan_result["valid_terms"],
        "valid_rank": scan_result["valid_rank"],
        "products": rows,
    }


def markdown(r: dict) -> str:
    L = []
    A = L.append
    A(f"# {r['label']} · 旺季选品机会报告\n")
    A(f"**词根**：{' / '.join(r['roots'])}　**周期**：{r['labels'][0]} → {r['labels'][-1]}"
      f"（{len(r['weeks'])} 周）\n")

    A("## 一、数据规模（两个数别混）\n")
    nw = len(r["weeks"])
    A(f"| 指标 | 值 | 说明 |")
    A("|---|---:|---|")
    A(f"| {nw} 周词条记录数 | {r['total_records']:,} | 同一词多周出现会重复计 |")
    A(f"| **去重词数** | **{r['unique_terms']:,}** | ←「有效信号占比」的分母 |")
    A(f"| 有效词（排名 ≤ {r['valid_rank']}） | {r['valid_terms']:,} | 去重后的稳定头部词 |")
    A(f"| 有效信号占比 | {r['valid_terms']/max(r['unique_terms'],1)*100:.2f}% | "
      f"越低说明该方向词的噪音越多（圣诞真实案例仅 0.17%）|\n")

    m = r["market"]
    A("## 二、大盘节奏：进场看加速度，不看词量\n")
    A("| 周 | 词条数 | 环比 |")
    A("|---|---:|---:|")
    for i, (w, n) in enumerate(zip(r["labels"], r["week_records"])):
        d = f"{r['week_records'][i]-r['week_records'][i-1]:+,}" if i else "—"
        star = " ⬅ 加速度峰" if w == m.get("acc_peak_week") else (
            " ⬅ 词量顶点" if w == m.get("volume_peak_week") else "")
        A(f"| {w} | {n:,} | {d}{star} |")
    A(f"\n> **加速度峰值 {m.get('acc_peak_week')}（+{m.get('acc_peak_v',0):,}）**，"
      f"**词量顶点 {m.get('volume_peak_week')}（{m.get('volume_peak_v',0):,}）**，"
      f"进场信号比\"看起来最热\"的那周**早 {m.get('lead_weeks')} 周**。\n")
    A("备货和广告都有前置期（海运 30–40 天 + 上架 + 广告起量）。"
      "等词量见顶才决定进场，时间已经不够了。\n")

    A("## 三、产品机会清单（六维度）\n")
    A("| 产品 | 12周词条 | 去重 | 加速峰 | 加速值 | 词量峰 | 起量周数 | 半衰期 | 尾周% | 形态 |")
    A("|---|---:|---:|---|---:|---|---:|---:|---:|---|")
    for p in r["products"]:
        A(f"| {p['product']} | {p['total_terms']:,} | {p['unique_terms']:,} | "
          f"{p['acc_peak_week']} | {p['acc_peak_v']:+,} | {p['peak_week']} | "
          f"{p['ramp_weeks']} | {p['half_life']} | {p['tail_pct']:.1f} | {p['shape']} |")

    A("\n## 四、分析 → 决策：最后一公里\n")
    A("| 指标 | 对应动作 |")
    A("|---|---|")
    for k, v in DECISION_MAP:
        A(f"| {k} | {v} |")

    A("\n## 五、形态 → 备货策略\n")
    A("| 形态 | 备货/广告动作 |")
    A("|---|---|")
    for s, act in SHAPE_ACTION.items():
        names = [p["product"] for p in r["products"] if p["shape"] == s]
        if names:
            A(f"| {s} | {act}　**适用**：{'、'.join(names)} |")

    return "\n".join(L)


def to_xlsx(r: dict, path: str):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = Workbook()
    head_fill = PatternFill("solid", fgColor="051C2C")
    head_font = Font(color="FFFFFF", bold=True)

    def style(ws, ncol):
        for c in range(1, ncol + 1):
            cell = ws.cell(row=1, column=c)
            cell.fill, cell.font = head_fill, head_font
            cell.alignment = Alignment(horizontal="center")
        ws.freeze_panes = "A2"

    ws = wb.active
    ws.title = "大盘节奏"
    ws.append(["周", "词条数", "环比"])
    for i, (w, n) in enumerate(zip(r["labels"], r["week_records"])):
        ws.append([w, n, (r["week_records"][i] - r["week_records"][i - 1]) if i else None])
    style(ws, 3)

    ws = wb.create_sheet("产品机会清单")
    ws.append(["产品", "12周词条", "去重词数", "加速峰", "加速值", "词量顶点",
               "起量周数", "半衰期", "尾周占比%", "形态", "头部3占比%", "ASIN数"])
    for p in r["products"]:
        ws.append([p["product"], p["total_terms"], p["unique_terms"], p["acc_peak_week"],
                   p["acc_peak_v"], p["peak_week"], p["ramp_weeks"], p["half_life"],
                   p["tail_pct"], p["shape"], p.get("head3_share"), p.get("n_asins")])
    style(ws, 12)

    ws = wb.create_sheet("分析到决策")
    ws.append(["指标", "对应动作"])
    for k, v in DECISION_MAP:
        ws.append([k, v])
    style(ws, 2)

    wb.save(path)
    return path


def to_json(r: dict, path: str):
    json.dump(r, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return path
