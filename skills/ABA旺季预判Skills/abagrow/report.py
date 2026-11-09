"""输出：4 张明细表 + 一份 Markdown 报告（可选 xlsx）。"""
from __future__ import annotations

import csv
import os

from .schema import label_of


def _w(path, header, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def write_tables(out_dir, seeds, n_asin_hit, related_terms, weeks, root_rows, attr_rows, accel_rows):
    os.makedirs(out_dir, exist_ok=True)
    labels = [label_of(w) for w in weeks]

    _w(os.path.join(out_dir, "1_种子ASIN.csv"), ["排名", "ASIN", "被多少个相关词命中"],
       [[i + 1, a, n] for i, (a, n) in enumerate(seeds)])
    _w(os.path.join(out_dir, "2_关联词表.csv"), ["关联词"], [[t] for t in related_terms])

    _w(os.path.join(out_dir, "3_属性周矩阵.csv"),
       ["层级", "属性", "词根", "整季合计"] + labels,
       [["属性", r["attr"], "", r["total"]] + r["weekly"] for r in attr_rows] +
       [["词根", r["attr"], r["root"], r["total"]] + r["weekly"] for r in root_rows])

    rows = []
    for r in accel_rows:
        p = r["points"]
        rows.append([r["kind"], r["attr"], r.get("root", ""), r["total"], r["shape"],
                     label_of(p["进场点"]), p["进场点加速度"], p["进场点词量"],
                     label_of(p["加码点"]), p["加码点词量"],
                     label_of(p["撤退点"]), p["撤退点加速度"]]
                    + r["weekly"] + [""] + r["accel"])
    _w(os.path.join(out_dir, "4_加速度表.csv"),
       ["层级", "属性", "词根", "整季合计", "形态",
        "进场点", "进场加速度", "进场周词量", "加码点", "加码周词量", "撤退点", "撤退加速度"]
       + labels + ["环比增量→"] + labels[1:], rows)
    return labels


def _md_table(labels, rows, first_cols):
    head = "| " + " | ".join(first_cols + labels) + " |"
    sep = "|" + "|".join(["---"] * (len(first_cols) + len(labels))) + "|"
    body = ["| " + " | ".join([str(c) for c in r[:len(first_cols)] + r[len(first_cols):]]) + " |" for r in rows]
    return "\n".join([head, sep] + body)


def write_report(out_dir, meta, weeks, root_rows, attr_rows, accel_rows, labels):
    os.makedirs(out_dir, exist_ok=True)
    zero = [r["attr"] for r in attr_rows if r["total"] == 0]
    live = [r for r in attr_rows if r["total"] > 0]
    main_root = max(root_rows, key=lambda r: r["total"]) if root_rows else None

    lines = [f"# {meta['label']} · 旺季预判报告", ""]
    lines += ["## 一、跑了什么", "",
              f"- 周次：{labels[0]} – {labels[-1]}（{len(weeks)} 周）",
              f"- 品类词：`{', '.join(meta['must_terms'])}`（必须同时命中）",
              f"- 命中 ASIN：{meta['n_asin_hit']:,} 个去重 → 取前 {len(meta['seeds'])} 个作种子",
              f"- 反查关联词：{meta['n_related']:,} 个去重", ""]

    if main_root:
        share = main_root["total"] / meta["n_related"] * 100 if meta["n_related"] else 0
        lines += ["## 二、主轴词根", "",
                  f"- 整季份量最大的词根是 **`{main_root['root']}`**（{main_root['attr']}）："
                  f"{main_root['total']:,} 个词，占全部关联词的 **{share:.0f}%**。", ""]
        others = sorted([r for r in root_rows if r["root"] != main_root["root"]],
                        key=lambda r: -r["total"])[:3]
        if others:
            lines += ["- 排在其后的词根：" +
                      "、".join(f"`{r['root']}` {r['total']:,}" for r in others if r["total"] > 0), ""]

    if zero:
        lines += ["## 三、零需求属性（整季为 0，直接砍掉这条投放线）", "",
                  "、".join(f"`{a}`" for a in zero), ""]

    lines += ["## 四、属性 × 周（词数）", "",
              _md_table(labels, [[r["attr"], r["total"]] + r["weekly"] for r in attr_rows],
                        ["属性", "整季"]), ""]

    lines += ["## 五、三个时间点", "",
              "| 属性 | 形态 | 进场点（加速度见顶） | 加码点（词量见顶） | 撤退点（加速度断崖） |",
              "|---|---|---|---|---|"]
    for r in accel_rows:
        if r["kind"] != "属性":
            continue
        if r["total"] == 0:
            lines.append(f"| {r['attr']} | {r['shape']} | — | — | — |")
            continue
        p = r["points"]
        lines.append(f"| {r['attr']} | {r['shape']} | {label_of(p['进场点'])}（{p['进场点加速度']:+d}） "
                     f"| {label_of(p['加码点'])}（{p['加码点词量']:,}） "
                     f"| {label_of(p['撤退点'])}（{p['撤退点加速度']:+d}） |")
    lines.append("")

    total_seq = [sum(r["weekly"][i] for r in live) for i in range(len(weeks))] if live else []
    if total_seq:
        from .pipeline import turning_points
        tp = turning_points(total_seq, weeks)
        lines += ["## 六、整个品类的节奏（所有非零属性合计）", "",
                  f"- **进场点**：{label_of(tp['进场点'])}（加速度 {tp['进场点加速度']:+d}）",
                  f"- **加码点**：{label_of(tp['加码点'])}（词量 {tp['加码点词量']:,}）",
                  f"- **撤退点**：{label_of(tp['撤退点'])}（加速度 {tp['撤退点加速度']:+d}）",
                  f"- 进场点到加码点相差 **{weeks.index(tp['加码点']) - weeks.index(tp['进场点'])} 周**", ""]

    lines += ["## 七、怎么用", "",
              "1. **进场点**：加速度见顶那一周，增长最快且还在加速 → 这时候上预算、抢排名。",
              "2. **加码点**：词量见顶那一周，量最大但加速度已在降 → 加码要克制，准备收。",
              "3. **撤退点**：加速度断崖那一周 → 收预算、撤排名、清库存。",
              "4. 属性之间别用同一个节奏：`早衰` 属性早投早收，`慢衰减` 可以押后一周补刀，`零需求` 直接不投。",
              "",
              "> 注意：词量是积分、加速度是导数。**预判看导数，复盘看积分。**", ""]

    path = os.path.join(out_dir, "报告.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path
