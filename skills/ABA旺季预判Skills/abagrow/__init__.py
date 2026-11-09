# -*- coding: utf-8 -*-
"""ABA 旺季预判 Skills —— 用 ABA 热搜词的「属性加速度」预判品类起量时间。

五步：数据准备 → 找种子 ASIN → 反查关联词 → 词根归属性 → 加速度 + 三个时间点
"""
__version__ = "1.0.0"

from . import pipeline, report, schema  # noqa: F401
