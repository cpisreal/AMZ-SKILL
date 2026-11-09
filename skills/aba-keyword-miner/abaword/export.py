# -*- coding: utf-8 -*-
"""导出 Excel 词表（就是文章里那张「搜索词 / 相关度分 / 词分类 / 最近排名 / 你会怎么用」）。"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

HEAD_FILL = PatternFill("solid", fgColor="0B2C5E")
HEAD_FONT = Font(color="FFFFFF", bold=True, size=11)
GOOD = PatternFill("solid", fgColor="E6F7EC")     # 强相关
WARN = PatternFill("solid", fgColor="FDECEC")     # 竞品品牌词
MID = PatternFill("solid", fgColor="FFF8E1")      # 中相关
THIN = Side(style="thin", color="D9E1EA")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

COLS = [
    ("搜索词", 34), ("相关度分", 10), ("词分类", 12), ("最近排名", 11),
    ("历史最佳排名", 13), ("命中ASIN数", 11), ("点击份额", 10), ("把握度", 9),
    ("你会怎么用", 22), ("命中ASIN", 16),
]


def export(rows: list[dict], out: Path, summary: dict | None = None,
           sort_by_score: bool = True) -> Path:
    data = sorted(rows, key=lambda r: (-(r.get("related_score") or 0),
                                       r.get("latest_rank") or 10 ** 9)) if sort_by_score else rows
    wb = Workbook()
    ws = wb.active
    ws.title = "词表"

    for c, (name, w) in enumerate(COLS, start=1):
        cell = ws.cell(row=1, column=c, value=name)
        cell.fill, cell.font = HEAD_FILL, HEAD_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = BORDER
        ws.column_dimensions[get_column_letter(c)].width = w
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 26

    for r, row in enumerate(data, start=2):
        vals = [row.get("term"), row.get("related_score"), row.get("category"),
                row.get("latest_rank"), row.get("best_rank"), row.get("hit_asin_count"),
                row.get("click_share"), row.get("confidence"), row.get("action"),
                row.get("matched_asins")]
        for c, v in enumerate(vals, start=1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.border = BORDER
            cell.alignment = Alignment(horizontal="left" if c in (1, 3, 9, 10) else "center",
                                       vertical="center")
        if c > 0 and isinstance(row.get("click_share"), float):
            ws.cell(row=r, column=7).number_format = "0.0%"
        if isinstance(row.get("confidence"), float):
            ws.cell(row=r, column=8).number_format = "0%"
        # 高亮
        score, cat = row.get("related_score") or 0, row.get("category_key")
        if cat == "competitor_brand":
            for c in range(1, len(COLS) + 1):
                ws.cell(row=r, column=c).fill = WARN
        elif score >= 8:
            for c in range(1, len(COLS) + 1):
                ws.cell(row=r, column=c).fill = GOOD
        elif score >= 6:
            ws.cell(row=r, column=2).fill = MID

    # ── 汇总页 ──
    ws2 = wb.create_sheet("运行摘要")
    ws2.column_dimensions["A"].width = 20
    ws2.column_dimensions["B"].width = 72
    lines = list((summary or {}).items())
    strong = [r for r in data if (r.get("related_score") or 0) >= 8]
    mid = [r for r in data if 6 <= (r.get("related_score") or 0) < 8]
    comp = [r for r in data if r.get("category_key") == "competitor_brand"]
    lowconf = [r for r in data if (r.get("confidence") or 1) < 0.6]
    lines += [
        ("词表总词数", len(data)),
        ("强相关（≥8 分）", len(strong)),
        ("中相关（6–8 分）", len(mid)),
        ("竞品品牌词（可直接做否定）", len(comp)),
        ("低把握（<60%，建议人工抽验）", len(lowconf)),
    ]
    ws2.cell(row=1, column=1, value="项目").fill = HEAD_FILL
    ws2.cell(row=1, column=1).font = HEAD_FONT
    ws2.cell(row=1, column=2, value="值").fill = HEAD_FILL
    ws2.cell(row=1, column=2).font = HEAD_FONT
    for i, (k, v) in enumerate(lines, start=2):
        ws2.cell(row=i, column=1, value=str(k)).font = Font(bold=True)
        ws2.cell(row=i, column=2, value=v if not isinstance(v, (list, dict)) else str(v))
        ws2.cell(row=i, column=1).border = BORDER
        ws2.cell(row=i, column=2).border = BORDER

    out = Path(out)
    wb.save(out)
    return out
