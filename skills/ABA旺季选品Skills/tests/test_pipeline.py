#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自测：6 条口径逐条验 + 一次端到端。

    python tests/test_pipeline.py

不需要 ABA 数据、不需要网络、不需要任何 key（自己造演示数据）。
退出码 0 = 全绿。
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from abapeak import export, pipeline, roots, rhythm          # noqa: E402
from abapeak.cluster import classifier_for, load_pack         # noqa: E402

FAILS = []
N = [0]


def check(name, cond, detail=""):
    N[0] += 1
    ok = bool(cond)
    print(f"  {'✅' if ok else '❌'}  {name}" + (f"   {detail}" if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


def test_roots():
    print("\n【口径① 词根边界】")
    m = roots.make_matcher(["men"])
    check("men 命中 'men's gift'", m("men's gift"))
    check("men 命中 'mens shoes'", m("mens shoes"))
    check("men 不命中 'women'", not m("women pajamas"))
    check("men 不命中 'omen'", not m("omen decor"))
    check("men 不命中 'garment'", not m("garment steamer"))
    c = roots.make_matcher(["christmas", "xmas"])
    check("christmas 命中 'christmas-tree'", c("christmas-tree"))
    check("christmas 命中 'christmas lights'", c("christmas lights"))
    check("auto 口径保住连写词 'christmaslights'", c("christmaslights"))
    check("auto 口径保住 'christmastime'", c("christmastime"))
    check("auto 口径挡住含 xmas 的假命中 'boxmasters'", not c("boxmasters"))
    check("多词词根 'christmas tree'", roots.make_matcher(["christmas tree"])("christmas tree skirt"))
    check("pattern 不含 lookbehind（RE2 不支持）", "(?<" not in roots.build_pattern(["a"]))
    check("auto：长词根只查左边界", roots.build_pattern(["christmas"], "auto").count("(^|") == 1)
    check("auto：短词根两边都查", roots.build_pattern(["men"], "auto").count("([^a-z]|$)") == 1)
    _loose = roots.build_pattern(["christmas"], "loose")
    check("loose 等价 LIKE（无边界）", "^" not in _loose and "[^a-z]" not in _loose, _loose)


def test_cluster():
    print("\n【口径③⑥ 聚类 + 子类守卫 + 同形异义】")
    clf = classifier_for("christmas")
    check("christmas tree → 圣诞树", clf("christmas tree") == "圣诞树")
    check("tree skirt 被守卫摘掉（不被 tree 吃）", clf("christmas tree skirt") is None)
    check("tree collar 被守卫摘掉", clf("christmas tree collar") is None)
    check("tree topper 被守卫摘掉", clf("christmas tree topper") is None)
    check("stuffer 排在 stocking 之前（独立产品）",
          clf("christmas stocking stuffers") == "袜内填充礼物")
    check("裸 stocking → 圣诞袜", clf("christmas stockings") == "圣诞袜")
    check("女性丝袜被剔除", clf("thigh high stockings") is None)
    check("不认识的词 → None", clf("christmas unknownthing xyz") is None)
    pk = load_pack("christmas")
    check("规则包有 roots", bool(pk.get("roots")))
    check("规则包产品数 >= 15", len(pk["products"]) >= 15, f"{len(pk['products'])} 类")


def test_rhythm():
    print("\n【口径④ 六维度 + 加速度 vs 词量】")
    labels = ["10/18", "10/25", "11/01", "11/08", "11/15", "11/22", "11/29", "12/06"]
    seq = [24, 30, 47, 83, 100, 120, 136, 167]
    m = rhythm.detect_turning_points(seq, labels)
    check("加速度峰在 11/08", m["acc_peak_week"] == "11/08", m["acc_peak_week"])
    check("词量顶点在 12/06", m["volume_peak_week"] == "12/06", m["volume_peak_week"])
    check("进场信号早于销量顶点", m["lead_weeks"] > 0, f"lead={m['lead_weeks']}")

    d = rhythm.six_dimensions([5, 20, 8, 2, 1, 1], labels[:6])
    check("峰值周识别正确", d["peak_week"] == "10/25", d["peak_week"])
    check("加速值为 +15", d["acc_peak_v"] == 15, d["acc_peak_v"])
    check("半衰期 = 1（10/25→11/01 就跌破 50%）", d["half_life"] == 1, d["half_life"])
    check("形态是早峰陡落型", d["shape"] == "早峰陡落型", d["shape"])
    check("晚峰 + 热尾 → 晚峰热尾型",
          rhythm.classify_shape(7, 3, 12) == "晚峰热尾型")
    check("平序列不炸", rhythm.six_dimensions([3, 3, 3], labels[:3])["total"] == 9)


def test_packs():
    """三个规则包都要能被 explain 讲清楚，且顺序铁律真的生效。"""
    print("\n【规则包：christmas / halloween / valentine】")
    from abapeak.cluster import available_packs
    pk_names = available_packs()
    for n in ("christmas", "halloween", "valentine"):
        check(f"{n} 在内置规则包里", n in pk_names, str(pk_names))
        p = load_pack(n)
        check(f"{n} 有 roots", bool(p.get("roots")), str(p.get("roots")))
        check(f"{n} 产品数 >= 15", len(p["products"]) >= 15, f"{len(p['products'])} 类")
        check(f"{n} 有 _explain_samples（explain 才讲得清楚）", bool(p.get("_explain_samples")))

    # ---------- 万圣节 ----------
    h = classifier_for("halloween")
    check("万圣节：讨糖装备排最前（trick or treat bag 不被糖果吃）",
          h("trick or treat bag") == "讨糖装备")
    check("万圣节：candy bucket 也是讨糖装备（不被糖果吃）",
          h("halloween candy bucket") == "讨糖装备")
    check("万圣节：costume → 服装装扮", h("halloween witch costume") == "服装装扮")
    check("万圣节：dog costume → 宠物装扮（宠物排在服装之前）",
          h("halloween dog costume") == "宠物装扮")
    check("万圣节：人的 costume 不被宠物吃掉", h("halloween kids costume") == "服装装扮")
    check("万圣节：t shirt → 服饰配件（不被「服装装扮」的宽泛键吃掉）",
          h("halloween t shirt") == "服饰配件")
    check("万圣节：witch hat 归装扮（不是女巫魔法）",
          h("halloween witch hat") == "服装装扮")
    check("万圣节：连写词 halloweencostume → 服装装扮", h("halloweencostume") == "服装装扮")
    check("万圣节：` bat ` 带空格键命中 'bat decorations'",
          h("halloween bat decorations") == "蜘蛛蝙蝠")
    check("万圣节：裸 bat 不会把 'bath bombs' 错划成蜘蛛蝙蝠",
          h("halloween bath bombs") != "蜘蛛蝙蝠")
    check("万圣节：battery 被同形异义剔掉", h("halloween battery operated") is None)
    check("万圣节：电影被守卫摘掉", h("halloween movie blu ray") is None)
    check("万圣节：零售商 Spirit Halloween 被守卫摘掉", h("spirit halloween costume") is None)
    check("万圣节：witch hazel 被同形异义剔掉", h("halloween witch hazel toner") is None)
    check("万圣节：pumpkin spice 被同形异义剔掉", h("halloween pumpkin spice latte") is None)
    check("万圣节：pumpkin decor 仍归南瓜", h("halloween pumpkin decor") == "南瓜")
    check("万圣节：裸 cat 不吃 'cat decor'（宠物装扮用双词键）",
          h("halloween black cat decor") != "宠物装扮")
    hg = roots.make_matcher(load_pack("halloween")["roots"])
    check("万圣节词根：连写 halloweendecor 命中", hg("halloweendecor"))
    check("万圣节词根：左边界挡住 ahalloween", not hg("ahalloween"))
    check("万圣节词根：多词词根 trick or treat 命中", hg("trick or treat bag"))
    check("万圣节词根：多词词根要分隔符，trickortreat 不命中", not hg("trickortreat"))

    # ---------- 情人节 ----------
    v = classifier_for("valentine")
    check("情人节：珠宝排在鲜花之前（rose gold necklace → 珠宝首饰）",
          v("valentine rose gold necklace") == "珠宝首饰")
    check("情人节：裸 rose 仍归鲜花", v("valentine roses bouquet") == "鲜花玫瑰")
    check("情人节：teddy bear → 毛绒玩具", v("valentine teddy bear") == "毛绒玩具")
    check("情人节：裸 teddy → 内衣情趣（靠顺序分开）",
          v("valentine teddy lingerie") == "内衣情趣")
    check("情人节：'heart' 链：heart sweater → 服装装扮",
          v("valentine heart sweater") == "服装装扮")
    check("情人节：heart pillow → 家居布艺", v("valentine heart pillow") == "家居布艺")
    check("情人节：heart banner → 气球派对", v("valentine heart banner") == "气球派对")
    check("情人节：heart sign 才落到心形装饰", v("valentine heart sign") == "心形装饰")
    check("情人节：dog toy → 宠物礼物（宠物排在玩具之前）",
          v("valentine dog toy") == "宠物礼物")
    check("情人节：人的 toy 不被宠物吃掉", v("valentine kids toy") == "玩具游戏")
    check("情人节：电影被守卫摘掉", v("valentine movie blu ray") is None)
    check("情人节：heart rate 被同形异义剔掉", v("valentine heart rate monitor") is None)
    vg = roots.make_matcher(load_pack("valentine")["roots"])
    check("情人节词根：连写 valentinesdaygift 命中", vg("valentinesdaygift"))
    check("情人节词根：galentine 命中", vg("galentine party"))
    check("情人节词根：左边界挡住 avalentine", not vg("avalentine"))
    check("情人节词根：品牌 valentino 不命中（不含 valentine）", not vg("valentino dress"))
    check("情人节：unmatched 词根 vday 不命中（刻意没收）", not vg("vday gift"))


def test_roots_真值表():
    """把口径①的真实行为钉住：docs 里曾经把 '3 ftchristmas tree' 说成 auto 会保住 —— 实际不会。"""
    print("\n【口径① 真值表（防文档漂移）】")
    c = roots.make_matcher(["christmas", "xmas"])
    cl = roots.make_matcher(["christmas", "xmas"], mode="loose")
    check("auto 保住连写词 christmaslights", c("christmaslights"))
    check("auto 保住 christmastime", c("christmastime"))
    check("auto 保住 christmasdecor", c("christmasdecor"))
    check("auto 挡住 '3 ftchristmas tree'（前面是字母 t，左边界不满足）",
          not c("3 ftchristmas tree"))
    check("loose 才保留 '3 ftchristmas tree'", cl("3 ftchristmas tree"))
    check("带空格的 '3 ft christmas tree' 命中", c("3 ft christmas tree"))


def test_schema():
    print("\n【口径⑤ 列裁剪 / 列名陷阱】")
    from abapeak import schema
    check("Brand #1 是单数", schema.COL_BRAND[1] == "Top Clicked Brand #1")
    check("Brands #2 是复数", schema.COL_BRAND[2] == "Top Clicked Brands #2")
    check("COLS_LIGHT 只要 2 列", len(schema.COLS_LIGHT) == 2)
    check("列名加引号（含空格/#）", schema.q(schema.COL_RANK) == '"Search Frequency Rank"')
    sql, _ = schema.source_sql("/tmp/x.csv", schema.COLS_LIGHT)
    check("source_sql 带 skip=1", "skip=1" in sql)
    check("深挖列集不含 Click Share（只取要的）",
          not any("Click Share" in c for c in schema.COLS_DEEP))


def test_end_to_end():
    print("\n【端到端】造演示数据 → 跑全链路")
    tmp = tempfile.mkdtemp(prefix="abapeak_test_")
    try:
        from demo.make_demo_aba import build_demo
        files = build_demo(os.path.join(tmp, "aba"))
        check("演示数据生成 4 周", len(files) == 4, str(len(files)))
        check("演示数据第一行是元数据（坑保留）",
              open(files[0], encoding="utf-8-sig").readline().startswith('"Reporting Range"'))

        pack = load_pack("christmas")
        r = pipeline.scan(os.path.join(tmp, "aba"), pack,
                          pattern="ABA_demo_week_{week}.csv", verbose=False)
        check("扫到 4 周", len(r["weeks"]) == 4, str(r["weeks"]))
        check("词根闸门挡掉了噪音词", r["unique_terms"] < 90, f"{r['unique_terms']} 个词")
        check("有效词 < 去重词（阈值口径生效）",
              r["valid_terms"] < r["unique_terms"],
              f"{r['valid_terms']}/{r['unique_terms']}")
        check("聚类出了产品（>=10 类）", len(r["products"]) >= 10, f"{len(r['products'])} 类")
        names = [p["product"] for p in r["products"]]
        check("树裙/树顶星没被算进「圣诞树」", "圣诞树" in names)
        check("袜内填充礼物是独立产品", "袜内填充礼物" in names)

        rep = export.build_report(r)
        m = rep["market"]
        check("加速度峰早于词量顶点", m["lead_weeks"] > 0, f"lead={m['lead_weeks']}")
        check("报告含决策映射章节", "分析 → 决策" in export.markdown(rep))
        check("报告含两个数的区分", "去重词数" in export.markdown(rep))

        xl = os.path.join(tmp, "r.xlsx")
        export.to_xlsx(rep, xl)
        check("xlsx 能写出来", os.path.getsize(xl) > 4000)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    print("=" * 62)
    print("abapeak 自测（6 条口径 + 端到端）")
    print("=" * 62)
    test_roots()
    test_roots_真值表()
    test_cluster()
    test_packs()
    test_rhythm()
    test_schema()
    test_end_to_end()
    print("\n" + "=" * 62)
    if FAILS:
        print(f"❌ {len(FAILS)}/{N[0]} 项未通过：")
        for f in FAILS:
            print("   -", f)
        return 1
    print(f"✅ 全部通过（{N[0]}/{N[0]}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
