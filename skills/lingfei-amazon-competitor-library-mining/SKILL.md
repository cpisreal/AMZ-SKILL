---
name: lingfei-amazon-competitor-library-mining
description: "从一个自家 ASIN 出发，自动搭出「同赛道竞品库」：爬 BSR 榜 + 核心词搜索结果页 → 按 ASIN 去重 → 用 Jev 决策模型逐个打同赛道相关度分并归类。Use when the user says 竞品库 / 竞对库 / 对手库 / 找竞品 / 同赛道竞品 / 竞品筛查 / 竞品名单 / competitor library / 扒竞品。含限速+反爬熔断的抓取层、1-10 相关度打分、6 类归类、Excel 导出。配套 skill：`amazon-aba-keyword-mining`（管「投什么词」，本 skill 管「跟谁打」）。"
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
prerequisites:
  packages: [httpx, beautifulsoup4, lxml, openpyxl]
  env: [TYPESAFE_API_KEY]
metadata:
  hermes:
    tags: [amazon, competitor, bsr, 竞品库, jev, 反爬, 跨境电商]
    related_skills: [amazon-aba-keyword-mining, data-charts]
---

# 竞品库自动挖掘（ASIN → 同赛道竞品名单）

## 这个 skill 干什么

**输入**：一个自家产品的 ASIN（+ 4–5 个核心关键词）
**输出**：一份带**同赛道相关度分（1–10）**、**6 类归类**、**可核对备注**的竞品库；同时给出全量候选与「直接竞品」两个 sheet。

核心判断（一句话）：**竞品库的难点不是「爬不到」，是爬回来一屏、没人告诉你哪几个是同赛道。**
实测：272 个候选里，配件/替代/无关占 **50.0%**，真正的直接竞品只有 **21.3%**。

## When to Use

- 「帮我搭个竞品库」「找一下这几个词的竞品」「这个 ASIN 的同赛道对手有哪些」
- 要一份**可以复算**的竞品名单（每个判定都带证据），而不是一次性的人工印象
- **不适用**：要的是「关键词」（那是 `amazon-aba-keyword-mining`）；要的是短期人工看几个对手（直接开页面看更快）

## 六步流水线

| 步 | 做什么 | 产出 |
|---|---|---|
| 1 | 找关键词：从自家 Listing 标题/类目提炼**一个**种子词 | — |
| 2 | 拆核心词：拆成 **4–5 个**（覆盖不同形态/冰型/场景） | `--keywords` |
| 3 | 爬 BSR 榜：自家 ASIN 所在**最细类目**，前 N 页 | `bsr_raw.json` |
| 4 | 爬竞品页面：每个核心词爬前 P 页搜索结果 | `serp_raw.json` |
| 5 | 整理竞品库：按 **ASIN 去重**（同一 ASIN 多次出现只算一次），记录来源/频次/最好位次 | `competitors_raw.json/.csv` |
| 6 | 自动筛查：对每个候选打**同赛道相关度 1–10** + **6 类归类** + 备注 | `competitors_scored.json` → `竞品库.xlsx` |

## 环境准备

```bash
pip install httpx beautifulsoup4 lxml openpyxl
export TYPESAFE_API_KEY=...        # Jev（TypeSafe System One）的 key
export AMZ_PROXY=http://host:port  # 可选；不设则直连 amazon.com
```

## 用法

```bash
python3 scripts/run_pipeline.py \
  --asin B0XXXXXXXX \
  --keywords "countertop ice maker,nugget ice maker,portable ice maker,bullet ice maker,ice maker machine" \
  --bsr-pages 2 --search-pages 5 --enrich 120 --out out
```

产出：`out/竞品库.xlsx`（概览 / 全量候选 / 直接竞品 三个 sheet）、`out/competitors_scored.json`、`out/pages/`（原始页面留证）。

分步跑也行：`build_competitor_lib.py` → `score_competitors.py` → `export_table.py`。

## 6 类归类口径

| 类 | 含义 |
|---|---|
| 直接竞品 | 同一细分品类、同一形态，抢同一批搜索流量 |
| 同类不同款 | 同类目但形态/规格/类型不同（例如台面机 vs 商用机、冰型不同） |
| 同品牌家族 | 同品牌其他型号（内部抢位 > 外部竞争） |
| 配件耗材 | 配件、滤芯、耗材、零件 |
| 替代方案 | 品类不同但满足同类需求 |
| 无关 | 类目与用途都无关 |

## 备注是怎么来的（重要设计）

**备注不是模型编的**，而是由**证据自动拼装**：类目是否一致 / 标题命中了哪几个核心词 / 品牌是否同一 / 价格差。
Jev 是决策模型，不生成自由文本 —— 所以它只负责「打分 + 归类」，解释由代码按证据拼。
这样读者能一眼看出「凭什么这么判」，也能自己复算。

## 🔴 抓取层的四个真坑（不修就白跑）

> 📌 抓取层的完整纪律（限速 / bm-verify / 持久连接 / 代理出口币种 / 选择器地图 /
> 熔断与断点续跑）见 `references/crawl-pitfalls.md`。下面四条是**速查**，
> 要改抓取层先读那份，别在这份里另立一套。

1. **`bm-verify` 软验证页**：amazon 会返回一个 2KB 的空壳页 + `<meta http-equiv="refresh">`（5 秒后跳回原 URL）。
   它**不是验证码**，熔断器认不出它，结果就是「解析到 0 个商品」还以为是选择器错了。
   → 判据：正文 `< 60KB` 且含 `bm-verify` / `noindex+refresh` → 等 8 秒用**同一连接**重试。
2. **每次新建连接 = 触发反爬**：这是「打开太快、关页面太快」的根因。
   → 用**一个持久 `httpx.Client`（带 cookie jar）+ 先访问首页预热**。实测修好后 141 次请求 0 次软验证。
3. **代理出口决定币种**：走非美国出口会回 `S$` 等本地货币，BSR 也可能取不到。
   → 设 `cookies={"i18n-prefs": "USD", "lc-main": "en_US"}` 强制美元。
4. **美元价格是「分」为单位渲染**：`$3999` 实际是 **$39.99**、`$5143` 是 **$51.43**。
   不修就会得出「一个制冰机卖 5143 美金」这种荒唐结论。
   → 无小数点且 ≥3 位数字 → ÷100。

## 其他坑

- **SERP 卡片的「品牌位」不可信**：常被配送日期 / `Amazon's Choice` 角标污染。品牌走**详情页**，用三重兜底（`#bylineInfo` → 页面文本 `Brand: X` → 标题首词）。
- **BSR 榜一页只给 30 条**，要更多得翻 `?pg=2` 之类。
- **类目相同 ≠ 竞品相同**：实测同一个 `Ice Makers` 类目里混着 $3,100–$9,450 的 Hoshizaki/Manitowoc **商用机**，它们不是台面机的竞品。这正是要打分而不是按类目硬筛的原因。
- **打分速度**：272 个候选 Jev 只用 **10.9 秒**（约 40ms/个），批量 20 个/请求。

## Verification Checklist

- [ ] `out/pages/` 里页面数 ≈ 请求数（说明缓存/留证正常）
- [ ] 详情页解析出的**价格**在合理区间（不是 4 位数「美金」）
- [ ] 候选池数量能解释：原始卡片数 × 去重率
- [ ] 打分分布不是「全高分」（全 9 分以上 = 目标描述或问题设计有问题）
- [ ] 抽样人工核对 5 个高分 + 5 个低分，理由与人工判断一致

## 参考

- `references/jev-api.md` — Jev（TypeSafe System One）API 口径：score / choice / noul 三种问题类型
- `references/crawl-pitfalls.md` — 反爬与解析坑的完整实测记录
- `references/worked-example-ice-maker.md` — **一次完整跑的真实读数基线**（跑完拿它对量级，并列出「症状 → 大概率原因」对照表）
