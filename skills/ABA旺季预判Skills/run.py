#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ABA 旺季预判 Skills 入口。

  python run.py demo                                    # 零依赖试跑
  python run.py cache --csv-dir ./aba --cache-dir ./.cache
  python run.py all   --csv-dir ./aba --must christmas,pajama --rules rules/pajama_winter.json --out ./out
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from abagrow.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
