# -*- coding: utf-8 -*-
"""口径 ④：六维度体检 + 「积分 vs 导数」节奏判读。

🔴 这套东西的第一原理（也是本工具最值钱的一句）：

    词量 = 积分（累积结果）；加速度 = 导数（变化速度）。**进场看导数，不看积分。**

  * **进场点** = 加速度（环比增量）见顶的那一周
  * **加码点** = 词量见顶的那一周
  * **撤退点** = 加速度断崖的那一周

圣诞实战：加速度峰值 11/08（+35,823），词量顶点 12/06（167,027）——
**进场信号比"看起来最热"的那周早整整 4 周**。等词量见顶才进场，海运（30–40 天）+ 上架
已经来不及了。

⚠️ **加速度必须用「全部词条数」算，不能用「rank≤5000 的头部词」算。**
稳定头部词每周都在榜 → 每周词条数恒定 → 差分全 0 → 节奏图是平的（真踩过）。
节奏分析一律扫全量（含长尾），长尾词才是"旺季才冒出来"的部分。
"""
from __future__ import annotations

SHAPES = ("早峰陡落型", "早峰缓降型", "晚峰热尾型", "晚峰脉冲型", "晚峰缓降型")


def detect_turning_points(seq, labels):
    """大盘节奏：加速度峰值周 / 词量顶点周 / 领先周数。"""
    if not seq:
        return {}
    diffs = [seq[i] - seq[i - 1] for i in range(1, len(seq))]
    vi = seq.index(max(seq))
    if not diffs:
        return {"volume_peak_week": labels[vi], "volume_peak_v": max(seq),
                "acc_peak_week": labels[0], "acc_peak_v": 0, "lead_weeks": 0}
    av = max(diffs)
    ai = diffs.index(av) + 1
    return {"volume_peak_week": labels[vi], "volume_peak_v": max(seq),
            "acc_peak_week": labels[ai], "acc_peak_v": av,
            "lead_weeks": vi - ai,          # 正数 = 进场信号更早
            "acc_series": diffs}


def six_dimensions(seq, labels):
    """单个产品的六维度。

    1 起量周    首次达到峰值 10% 的那一周（阈内起点）
    2 加速值    最大环比增量 + 出现的那一周
    3 量级      12 周词条总量 + 峰值周词量 + 峰值周
    4 节奏      起量周数 / 半衰期 / 前3后3比
    5 尾周占比  最后一周 / 峰值
    6 形态      4 形态分类
    """
    total = sum(seq)
    peak_v = max(seq) if seq else 0
    peak_i = seq.index(peak_v) if peak_v else 0

    diffs = [seq[i] - seq[i - 1] for i in range(1, len(seq))]
    if diffs:
        acc_v = max(diffs)
        acc_i = diffs.index(acc_v) + 1
    else:
        acc_v, acc_i = 0, 0

    start_i = next((i for i, v in enumerate(seq) if peak_v and v >= peak_v * 0.10), 0)
    ramp_weeks = peak_i - start_i
    half_life = next((i - peak_i for i in range(peak_i, len(seq))
                      if peak_v and seq[i] <= peak_v * 0.50), len(seq) - peak_i)
    tail_pct = (seq[-1] / peak_v * 100) if peak_v else 0.0
    pre3 = sum(seq[max(0, peak_i - 3):peak_i + 1])
    post3 = sum(seq[peak_i:peak_i + 4])
    pre_post = round(pre3 / post3, 2) if post3 else 99.0

    return {
        "total": total,                                    # 3 量级
        "peak_v": peak_v, "peak_i": peak_i, "peak_week": labels[peak_i],
        "ramp_week": labels[start_i], "ramp_weeks": ramp_weeks,   # 1 起量 + 4 节奏
        "acc_peak_v": acc_v, "acc_peak_week": labels[acc_i],      # 2 加速
        "half_life": half_life, "pre_post": pre_post,             # 4 节奏
        "tail_pct": round(tail_pct, 1),                            # 5 尾周
        "shape": classify_shape(peak_i, half_life, tail_pct),      # 6 形态
        "seq": list(seq),
    }


def classify_shape(peak_i, half_life, tail_pct):
    """4 形态分类。

    ⚠️ 主判据必须是**峰值周位置**（早/晚），把半衰期和尾周当副判据。
    只用阈值分类会把 20/20 全归成一类（真踩过）。
    """
    if peak_i <= 6 and half_life <= 1:
        return "早峰陡落型"
    if peak_i <= 6:
        return "早峰缓降型"
    if tail_pct >= 8:
        return "晚峰热尾型"
    if half_life <= 1:
        return "晚峰脉冲型"
    return "晚峰缓降型"


# 形态 → 备货/广告动作（报告的"分析→决策"那一步）
SHAPE_ACTION = {
    "早峰陡落型": "脉冲型：小批量多款，不深备；广告集中在加速峰当周冲",
    "早峰缓降型": "可以多备，节后还能收；广告提前 2 周铺",
    "晚峰热尾型": "热尾型：可多备，节后仍有量；广告延续到节后",
    "晚峰脉冲型": "脉冲型：小批量多款，绝不深备",
    "晚峰缓降型": "常规备货；广告跟随词量曲线",
}


def format_table(results, labels):
    """终端表格：产品 × 六维度。"""
    hdr = (f"{'产品':<14}{'总量':>9}{'加速峰':>8}{'加速值':>9}{'词量峰':>8}"
           f"{'起量周':>8}{'起量周数':>8}{'半衰期':>7}{'尾周%':>7}  形态")
    out = [hdr, "-" * len(hdr)]
    for name, r in results.items():
        out.append(f"{name:<14}{r['total']:>9,}{r['acc_peak_week']:>8}"
                   f"{r['acc_peak_v']:>9,}{r['peak_week']:>8}{r['ramp_week']:>8}"
                   f"{r['ramp_weeks']:>8}{r['half_life']:>7}{r['tail_pct']:>7.1f}  {r['shape']}")
    return "\n".join(out)
