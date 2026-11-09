---
name: ABA 旺季预判
description: "turn amazon brand analytics (ABA) weekly search-term reports into three timing points (entry / add-position / retreat week) for a product category, by analyzing attribute-level search acceleration. use when an amazon seller wants to predict when a category ramps up, peaks, or should be exited, find seed ASINs and related query terms, or build an attribute weekly matrix from ABA data. runs locally via python run.py with duckdb; no api key, no crawler, no paid tool needed."
---

# ABA 旺季预判

让「一个品类什么时候起量、什么时候见顶、什么时候该撤」从凭经验猜变成一条命令跑出的三个时间点。
手上有 ABA 热搜词周报（按周下载），就能拿到：品类由哪些**属性**构成、每类属性每周涨多少、**进场点 / 加码点 / 撤退点**。

## Quick start

```bash
pip install -r requirements.txt
python run.py demo        # 零数据/零 key 试跑，自动造 12 周演示数据
```

## 用自己的数据

```bash
python run.py cache --csv-dir ./aba --cache-dir ./.cache
python run.py all   --csv-dir ./aba --cache-dir ./.cache \
                    --must christmas,pajama --rules rules/pajama_winter.json --out ./out
```

产出（`out/` 下）：`1_种子ASIN.csv` / `2_关联词表.csv` / `3_属性周矩阵.csv` / `4_加速度表.csv` / `报告.md`。

## 常用参数

| 参数 | 说明 |
|---|---|
| `--csv-dir` | ABA 周报 CSV 目录 |
| `--must` | 品类词，逗号分隔，必须全部同时命中（如 `christmas,pajama`） |
| `--rules` | 属性规则包（内置 `rules/pajama_winter.json`，换品类复制改词根） |
| `--top` | 种子 ASIN 个数（默认 10） |
| `--threads` | DuckDB 线程数（默认 4） |

换品类：复制 `rules/pajama_winter.json`，改 `label` / `attributes` / `must_terms` 三块即可，代码不用动。

## 三个时间点怎么读

- **进场点 = 加速度见顶那一周**（增长最快、还在加速）
- **加码点 = 词量见顶那一周**（量最大，但加速度已在下滑）
- **撤退点 = 加速度断崖那一周**（环比大幅转负，收预算、撤排名、清库存）

一句话：**加速度见顶进场，词量见顶加码，加速度断崖撤退。**

## 关键口径（详见 README.md）

- 用 DuckDB + 列裁剪只读 5 列，十几秒处理 20GB 级别 CSV（别用 Pandas 硬读会 OOM）。
- ABA 导出 CSV 第一行是 `Reporting Range` 元数据，必须 `skip=1`。
- 词根匹配要空格包裹，否则 `men` 误伤 `womens`。
- 算环比时第一周无上周可比，加速度图比词量图少一个点。

依赖：`duckdb`（见 `requirements.txt`）。完整说明见同目录 `README.md`。
