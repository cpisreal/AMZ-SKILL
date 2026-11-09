---
name: ABA 自动词库（关键词挖掘）
description: 用亚马逊 ABA（Brand Analytics 搜索词报告）+ 竞品 ASIN 反向命中，自动产出高相关关键词词表。当用户提供 ABA 热搜词报告 CSV、竞品 ASIN 清单，想选词、建词库、批量判关键词相关度、给词分类、挖竞品正在吃的词、导出词表 Excel 时使用。触发词：ABA、亚马逊搜索词报告、品牌分析、词库、选词、关键词相关度、竞品 ASIN 反查、Jev 打分、词表、关键词挖掘。
---

# ABA 自动词库（关键词挖掘）

用「ABA 数据反向命中竞品 ASIN」+「决策模型 Jev 打分」自动挖出高相关关键词，产出可直接投放的词表。

## 什么时候用

- 用户给了 ABA 热搜词报告（亚马逊品牌分析 → 搜索词报告，CSV），想选出该打哪些词
- 用户有一批竞品 ASIN，想知道「竞品正在吃、但自己可能没投」的词
- 需要批量判「搜索词 vs 我的商品」相关度、并分类（品类词 / 品牌词 / 属性词 / 场景词…）
- 要把选词结果导出成一张带分数、分类、打法的 Excel

## 核心思路（为什么要这么做）

- **反向命中**：ABA 每个搜索词都带「点击最多的商品 #1/#2/#3」三列 ASIN。把竞品 ASIN 丢进去，就能捞出「真实买家在搜、且搜完点进了这些竞品」的词——绕开正向捞词的天花板。
- **Jev 打分**：把目标 ASIN 的 Listing 当参考物，逐词给出 1–10 相关度分 + 6 类词分类 + 把握度。Jev 是 TypeSafe 的决策模型（Decisions API，非 chat），输出类型化概率，不幻觉、速度快、成本低。
- **为什么不直接开投**：本工具只解决「选词」这一步，出的是词表，不是投放结论。最终仍要结合转化、竞价、预算做判断。

## 使用步骤

### 第一步：准备输入（三样）

| 要准备 | 从哪来 |
|:--|:--|
| ① ABA 搜索词报告 CSV | 卖家后台 → 品牌分析 → 亚马逊搜索词报告，建议连续 4–12 周 |
| ② 竞品 ASIN 清单 | 自己列，3–10 个最直接的对手，写成 `asins.txt` 一行一个 |
| ③ 一个 Jev key | OpenRouter（`OPENROUTER_API_KEY=sk-or-...`）或 TypeSafe 直连，二选一 |

**环境**：Python 3.10+，`pip install -r requirements.txt`（5 个依赖）。

先无 key 试跑验证环境：

```bash
python demo/make_demo_aba.py     # 造合成 ABA 数据
python run.py --aba-dir ./demo/aba --asins ./demo/asins.txt --target B0DEMOTGT1 \
  --listing-json ./demo/listing.json --provider mock --out ./成品_演示词表.xlsx
```

### 第二步：正式跑（真实数据）

```bash
cp .env.example .env    # 填 OPENROUTER_API_KEY=sk-or-...
python run.py \
  --aba-dir  ~/Downloads/aba_reports \
  --asins    ./asins.txt \
  --target   B0XXXXXXXX \
  --provider openrouter \
  --out      词表.xlsx
```

**四步流水线**：① DuckDB 装载 ABA → ② ASIN 反向命中搜索词 → ③ 爬目标 Listing → ④ Jev 打分 + 分类 → Excel。

### 关键参数

| 参数 | 说明 |
|:--|:--|
| `--aba-dir` | ABA CSV 所在目录（必需，支持多文件） |
| `--asins` | 竞品 ASIN：文件路径或逗号分隔（必需） |
| `--target` | 目标 ASIN，爬它的 Listing 当打分基准（必需） |
| `--provider` | `openrouter` / `typesafe` / `mock`（无 key 试跑） |
| `--listing-json` | 直接喂已抓好的 Listing JSON，跳过爬取 |
| `--proxy` | 抓 Listing 用代理（被验证码拦时用） |
| `--batch` | 每批词数，默认 60（安全值，塞多了会报错） |
| `--market` | 站点后缀：com / co.uk / de / co.jp … |
| `--max-words` | 最多处理多少词（0=全部） |
| `--out` | 输出 xlsx 路径 |
| `--db` / `--rebuild` | DuckDB 库文件路径 / 清库重建 |

## 输出怎么读

词表含这些列：**搜索词、相关度分(1–10)、词分类、最近排名、历史最佳排名、命中ASIN数、点击份额、把握度、你会怎么用**。

- **相关度分**：≥8 分直接建活动；6–8 分层控成本；<6 放观察池
- **最近排名 vs 历史最佳**：最近 ≫ 最佳 = 在掉；最近 ≈ 最佳 = 正热
- **把握度**：<60% 建议人工抽验，≥90% 可放心用
- 自动上色：绿底 = 强相关，红底 = 竞品品牌词（否定词候选），黄 = 中相关
- 「运行摘要」sheet 给总词数、强相关数、竞品品牌词数、需人工抽验数

**6 类词打法**：品类词→主力投放；自有品牌词→守品牌；竞品品牌词→否定词/拦截；属性规格词、场景用途词→长尾拓量；其他长尾→低优先。

## 三个坑

1. **ABA CSV 第一行不是表头**——是元数据 `Reporting Range=...`，真表头在第二行。工具会自动跳过，别手动改。
2. **爬 Listing 的价格可能是别的币种**（走了海外节点），与相关度无关，别拿去做定价。
3. **Jev 一次别塞太多词**——默认 60/批，塞多了报错。用 `--batch` 调。

## 边界

本技能产出的是**词表**，不是**直接开投的结论**。替代的是「人肉筛词的体力活」，不替代操盘手的投放判断。
