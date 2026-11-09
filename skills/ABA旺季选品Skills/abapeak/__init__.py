# -*- coding: utf-8 -*-
"""abapeak —— 一颗模糊种子词 → 旺季产品机会报告。

6 条内置口径（每条都能单独看懂、单独改）：
  ① 词根边界         roots.py      避免 `men` 命中 `women`
  ② 有效词阈值       pipeline.py   rank ≤ 5000
  ③ 产品实体聚类     cluster.py    规则包驱动，子类守卫在前
  ④ 六维度 + 加速度  rhythm.py     进场看导数不看积分
  ⑤ DuckDB 列裁剪    schema.py     2.9M 行/周也不 OOM
  ⑥ 子类语义甄别     cluster.py    剔除「女性丝袜」这类误命中
"""
__version__ = "1.0.0"

from .roots import build_pattern, make_matcher  # noqa: F401
from .cluster import Classifier, classifier_for, load_pack, available_packs  # noqa: F401
from .rhythm import six_dimensions, detect_turning_points, classify_shape  # noqa: F401
from . import export, pipeline, schema  # noqa: F401
