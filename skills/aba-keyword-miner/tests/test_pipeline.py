#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端到端自测：不联网、不需要任何 key，用合成数据跑完整条流水线并断言结果。

跑：python tests/test_pipeline.py     （或 pytest tests/）
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from abaword import s1_load, s2_match, s3_listing, s4_jev  # noqa: E402
from abaword.export import export                          # noqa: E402
from abaword.schema import detect_columns, parse_reporting_range  # noqa: E402

TMP = ROOT / ".selftest"
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'✅' if cond else '❌'} {name}" + (f"  {detail}" if detail else ""))


def main():
    if TMP.exists():
        shutil.rmtree(TMP)
    TMP.mkdir()

    print("\n【0】表头自适应 + 元数据解析")
    en = ["Search Frequency Rank", "Search Term", "Top Clicked Product #1: ASIN",
          "Top Clicked Product #1: Click Share", "Top Clicked Product #1: Conversion Share"]
    cn = ["搜索频率排名", "搜索词", "点击量最高的商品 #1: ASIN",
          "点击量最高的商品 #1: 点击份额", "点击量最高的商品 #1: 转化份额"]
    me, mc = detect_columns(en), detect_columns(cn)
    check("英文表头识别", me["term"] == "Search Term" and me["asin1"].endswith("ASIN") and me["click1"],
          f"term={me['term']} asin1={me['asin1']}")
    check("中文表头识别", mc["term"] == "搜索词" and "ASIN" in mc["asin1"] and mc["click1"] == "点击量最高的商品 #1: 点击份额",
          f"term={mc['term']} click1={mc['click1']}")
    s, e = parse_reporting_range("Reporting Range=2026-08-01 - 2026-08-07")
    check("元数据区间解析", (s, e) == ("2026-08-01", "2026-08-07"), f"{s}~{e}")
    check("中文元数据解析", parse_reporting_range("报告范围=2026-08-15 - 2026-08-21")[1] == "2026-08-21")

    print("\n【1】生成演示数据 + DuckDB 入库")
    subprocess.run([sys.executable, str(ROOT / "demo" / "make_demo_aba.py")],
                   check=True, capture_output=True)
    db = TMP / "t.duckdb"
    info = s1_load.load(ROOT / "demo" / "aba", db, rebuild=True, verbose=False)
    check("3 个文件全部入库", len(info["files"]) == 3, f"{len(info['files'])} 个")
    check("覆盖 3 周", len(info["weeks"]) == 3, str(info["weeks"]))
    check("行数 = 3×64", info["rows"] == 192, f"{info['rows']} 行")

    print("\n【2】ASIN 反向命中")
    asins = (ROOT / "demo" / "asins.txt").read_text().split()
    words, stat = s2_match.reverse_match(db, asins)
    check("命中词数 > 0", len(words) > 0, f"{len(words)} 个词")
    check("全部 ASIN 都命中", not stat["未命中的ASIN"], str(stat["未命中的ASIN"]))
    check("每个词都有最近排名", all(w["latest_rank"] for w in words))
    check("历史最佳排名 ≤ 最近排名", all(w["best_rank"] <= w["latest_rank"] for w in words))
    check("命中ASIN数 ≥ 1", all(w["hit_asin_count"] >= 1 for w in words))
    check("点击份额已归一化到 0–1",
          all(0 <= (w["click_share"] or 0) <= 1.0 for w in words),
          f"最大 {max(w['click_share'] or 0 for w in words):.3f}")
    check("命中ASIN都来自竞品清单",
          all(set((w["matched_asins"] or "").split(",")) <= set(asins) for w in words))

    print("\n【3】Listing 读取（离线）")
    listing = s3_listing.load_local(ROOT / "demo" / "listing.json")[0]
    txt = s3_listing.listing_text(listing)
    check("Listing 文本含标题+五点", listing["title"][:20] in txt and listing["bullets"][0][:20] in txt)
    check("币种无误报", s3_listing.currency_warning(listing) is None)

    print("\n【4】Jev 打分 + 分类（mock，验证流程与契约）")
    rows, sstat = s4_jev.score_all([w["term"] for w in words], listing, provider="mock")
    check("每词都有结果", len(rows) == len(words), f"{len(rows)}/{len(words)}")
    check("相关度分落在 1–10", all(1.0 <= (r["related_score"] or 0) <= 10.0 for r in rows),
          f"min {min(r['related_score'] for r in rows)} / max {max(r['related_score'] for r in rows)}")
    check("分类都落在 6 类内",
          all(r["category_key"] in s4_jev.CATS for r in rows),
          str(sorted({r["category_key"] for r in rows})))
    check("把握度落在 0–1", all(0 <= (r["confidence"] or 0) <= 1 for r in rows))
    check("评分档位=10（API 上限）", len(s4_jev.LEVELS) == 10)
    check("分批正确（每批 7 个）",
          s4_jev.score_all([w["term"] for w in words[:15]], listing, provider="mock", batch=7,
                           verbose=False)[1]["批次数"] == 3)

    print("\n【5】导出 Excel")
    merged = [{**w, **r} for w, r in zip(words, rows)]
    out = export(merged, TMP / "out.xlsx", {"测试": "自测"})
    import openpyxl
    wb = openpyxl.load_workbook(out)
    ws = wb["词表"]
    check("文件生成", out.exists() and out.stat().st_size > 5000, f"{out.stat().st_size//1024} KB")
    check("两个 sheet", wb.sheetnames == ["词表", "运行摘要"], str(wb.sheetnames))
    check("表头列齐全", [c.value for c in ws[1]] ==
          ["搜索词", "相关度分", "词分类", "最近排名", "历史最佳排名", "命中ASIN数",
           "点击份额", "把握度", "你会怎么用", "命中ASIN"])
    check("数据行数 = 词数", ws.max_row - 1 == len(merged), f"{ws.max_row-1} 行")

    print("\n" + "=" * 56)
    print(f"  通过 {len(PASS)} / {len(PASS)+len(FAIL)}")
    if FAIL:
        print("  失败：" + ", ".join(FAIL))
    shutil.rmtree(TMP, ignore_errors=True)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
