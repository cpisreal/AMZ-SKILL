#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ABA 自动词库 Skills —— 一条命令出表

用法：
  python run.py --aba-dir ./aba_csv --asins ./asins.txt --target B0XXXXXXXX --out 词表.xlsx

先试跑（不需要任何 key）：
  python demo/make_demo_aba.py                       # 造一份演示用 ABA 数据
  python run.py --aba-dir ./demo/aba --asins ./demo/asins.txt \\
      --target B0DEMOTGT1 --provider mock --out ./成品_演示词表.xlsx
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from abaword.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
