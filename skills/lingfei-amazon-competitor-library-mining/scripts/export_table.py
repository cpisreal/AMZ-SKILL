#!/usr/bin/env python3
"""竞品库流水线 · 导出：把打分结果写成 Excel（两个 sheet：全量 / 直接竞品）。

用法：python3 export_table.py --scored out/competitors_scored.json --out out
"""
import argparse
import json
import os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

HEAD = ["ASIN", "同赛道相关度", "分类", "备注", "标题", "品牌", "类目",
        "价格$", "评分", "出现频次", "最好位次", "来源", "广告位"]
WIDTH = [13, 11, 11, 62, 58, 14, 34, 8, 7, 9, 9, 14, 7]


def rows_of(scored):
    out = []
    for r in scored:
        src = "/".join(sorted(set(r.get("sources") or [])))
        pos = r.get("best_pos")
        pos = "仅BSR" if (pos is None or pos >= 999) else pos
        out.append([
            r["asin"], r.get("relevance"), r.get("klass"), r.get("reason"),
            (r.get("detail_title") or r.get("title") or "")[:180],
            r.get("brand"), (r.get("category") or "")[:80],
            r.get("price"), r.get("rating"),
            r.get("n_hits"), pos, src,
            "广告" if r.get("sponsored") else "",
        ])
    return out


def write_sheet(ws, rows):
    ws.append(HEAD)
    for c in range(1, len(HEAD) + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1D4ED8")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[get_column_letter(c)].width = WIDTH[c - 1]
    for r in rows:
        ws.append(r)
    # 高相关行标浅蓝底
    for i, r in enumerate(rows, start=2):
        if (r[1] or 0) >= 7:
            for c in range(1, len(HEAD) + 1):
                ws.cell(row=i, column=c).fill = PatternFill("solid", fgColor="EFF4FF")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", default="out/competitors_scored.json")
    ap.add_argument("--out", default="out")
    a = ap.parse_args()

    d = json.load(open(a.scored, encoding="utf-8"))
    scored = d["scored"]
    own = d["target"]
    hi = [r for r in scored if (r.get("relevance") or 0) >= 7]

    wb = Workbook()
    ws = wb.active
    ws.title = "全量候选"
    write_sheet(ws, rows_of(scored))
    ws2 = wb.create_sheet("直接竞品(>=7分)")
    write_sheet(ws2, rows_of(hi))

    # 概览 sheet
    ws3 = wb.create_sheet("概览", 0)
    ws3.append(["目标产品"])
    ws3.append(["标题", own.get("title")])
    ws3.append(["品牌", own.get("brand")])
    ws3.append(["类目", own.get("category")])
    ws3.append(["价格$", own.get("price")])
    ws3.append([])
    ws3.append(["核心关键词", "、".join(d.get("keywords") or [])])
    ws3.append([])
    ws3.append(["候选总数", len(scored)])
    ws3.append(["同赛道相关度>=7", len(hi)])
    ws3.append(["高相关占比", f"{len(hi)/len(scored)*100:.1f}%"])
    from collections import Counter
    ws3.append([])
    ws3.append(["分类分布"])
    for k, v in Counter(r.get("klass") for r in scored).most_common():
        ws3.append([k, v])
    ws3.column_dimensions["A"].width = 16
    ws3.column_dimensions["B"].width = 70
    for row in ws3.iter_rows():
        for c in row:
            c.alignment = Alignment(vertical="center", wrap_text=False)

    path = os.path.join(a.out, "竞品库.xlsx")
    wb.save(path)
    print(f"→ {path}  全量 {len(scored)} 行 / 直接竞品 {len(hi)} 行")


if __name__ == "__main__":
    main()
