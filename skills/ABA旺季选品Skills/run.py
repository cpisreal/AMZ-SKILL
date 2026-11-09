#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ABA 旺季选品分析 Skills —— 一颗方向词，一条命令，出一份机会报告

快速试跑（不需要 ABA 数据、不需要任何 key）：
    python run.py demo

用自己的数据：
    python run.py cache  --csv-dir ./aba --out ./.cache        # 建议：先转缓存
    python run.py all    --csv-dir ./aba --pack christmas \
                         --cache-dir ./.cache --out ./out

看某条口径到底做了什么：
    python run.py explain --pack christmas     # 词根边界 + 聚类抽样
    python run.py packs                        # 有哪些内置季节规则包
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from abapeak.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
