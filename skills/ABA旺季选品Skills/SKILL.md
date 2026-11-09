---
name: ABA 旺季选品分析
description: "turn one vague direction word (e.g. christmas, halloween, pet, camping) plus amazon brand analytics (ABA) weekly search-term reports into a product opportunity report with entry timing and stocking playbook. use when an amazon seller wants to mine ABA data for seasonal product selection, break a theme into 20 products, find the best entry week and inventory plan, or validate search-term parsing. runs locally via python run.py with duckdb + openpyxl; no api key needed."
---

# ABA 旺季选品分析

把「一个方向词 → 20 个产品 → 进场时点 + 备货打法」这套分析从手工跑变成一条命令。
手上有 ABA 热搜词周报就能拿到带**进场时点**和**备货建议**的产品机会报告。

## Quick start

```bash
pip install -r requirements.txt
python run.py demo        # 零数据/零 key 试跑，自动造演示数据
```

## 用自己的数据

```bash
python run.py cache --csv-dir ./aba --out ./.cache          # 建议先转 parquet 缓存
python run.py all   --csv-dir ./aba --pack christmas \
                    --cache-dir ./.cache --out ./out
```

产出 `out/圣诞季Christmas_机会报告.md` / `.xlsx` / `.json`。

## 常用命令

| 命令 | 作用 |
|---|---|
| `python run.py demo` | 离线试跑（自带演示数据） |
| `python run.py all --pack christmas` | 完整链路出报告 |
| `python run.py packs` | 列出内置季节规则包 |
| `python run.py explain --pack christmas` | 看三道闸门怎么判（不读数据） |
| `python run.py scan --csv-dir ./aba` | 只扫词 + 聚类 |
| `python run.py rhythm --csv-dir ./aba` | 只出六维度节奏 |
| `python run.py deep --csv-dir ./aba --product 圣诞袜` | 只深挖一个产品 |

内置季节包：`christmas` / `halloween` / `valentine`（共用同一套代码，只换 JSON）。
换成自己的季节：复制 `abapeak/rules/<某包>.json` 改 `roots` 和 `products` 即可。

## 关键口径（详见 README.md）

- 词根边界 `auto`：≥6 字符只查左边界（保住连写词），<6 字符两边都查。
- 有效词阈值 `Search Frequency Rank ≤ 5000`（`--valid-rank` 可调）。
- 产品实体聚类：词 ≠ 产品，必须归到产品实体。
- 进场看加速度（导数）不看词量（积分）：进场点=加速度峰，加码点=词量顶，撤退点=加速度断崖。
- DuckDB 列裁剪：单周 1.7–2.3 GB 也不 OOM；CSV 首行是元数据必须 `skip=1`。

依赖：`duckdb`、`openpyxl`。完整说明与踩坑记录见同目录 `README.md`。
