# 竞品库自动挖掘 Skills · 使用说明

> 从一个自家 ASIN 出发，自动搭出「同赛道竞品库」：
> **爬 BSR 榜 + 核心词搜索结果 → 按 ASIN 去重 → Jev 决策模型逐个打相关度分并归类。**

---

## 一、它能给你什么

**输入**：你自己的一个 ASIN + 4–5 个核心关键词
**输出**：一份 Excel（三个 sheet）

| Sheet | 内容 |
|---|---|
| 概览 | 目标产品、核心词、候选总数、高相关占比、分类分布 |
| 全量候选 | 所有 ASIN，带相关度分 / 分类 / 备注 / 类目 / 价格 / 出现频次 / 最好位次 / 来源 |
| 直接竞品(≥7分) | 只留最该盯的那批 |

每个候选都带**可核对的备注**（例：「类目『Ice Makers』与目标一致；标题命中核心词『nugget ice maker』；品牌不同 → 抢同一批搜索流量，是最该盯的对位竞品」）。

---

## 二、装什么

```bash
pip install httpx beautifulsoup4 lxml openpyxl
```

两个环境变量：

```bash
export TYPESAFE_API_KEY=你的key        # Jev（TypeSafe System One）决策模型的 key，必填
export AMZ_PROXY=http://host:port      # 可选：需要代理才能访问 amazon.com 时设置；不设则直连
```

---

## 三、怎么跑

```bash
python3 scripts/run_pipeline.py \
  --asin B0XXXXXXXX \
  --keywords "countertop ice maker,nugget ice maker,portable ice maker,bullet ice maker,ice maker machine" \
  --bsr-pages 2 --search-pages 5 --enrich 120 --out out
```

常用参数：

| 参数 | 默认 | 说明 |
|---|---|---|
| `--bsr-pages` | 2 | 爬 BSR 榜前几页（一页 30 条） |
| `--search-pages` | 5 | 每个核心词爬前几页搜索结果（一页约 22 条） |
| `--enrich` | 120 | 给前 N 个候选爬详情页（补品牌/类目/五点）。设 0 = 不补，快但判定信息少 |
| `--min-delay` / `--max-delay` | 5 / 8 | 每请求随机等待秒数。**别调小** |
| `--max-requests` | 400 | 请求上限，到顶即停（防封） |

**实测参考耗时**（5 词 × 5 页 + BSR 2 页 + 补 120 个详情）：**约 25–30 分钟 / 141 次请求**。
打分阶段另需 **约 11 秒**（272 个候选）。

---

## 四、它怎么保证不把你自己搭进去

- **慢**：默认每请求随机等 5–8 秒，不并发
- **停**：命中验证码立刻熔断，不硬闯；请求数到顶自动停
- **留证**：每个页面原文落盘 `out/pages/`，可回溯复算，也支持断点续跑

---

## 五、四个必须知道的坑（都已在代码里处理好）

1. **`bm-verify` 软验证页**：会返回 2KB 空壳页 + 5 秒后自动跳转，看起来像「选择器写错了」
2. **每次新建连接 = 触发反爬**：这就是「打开太快关太快」的根因，必须用持久连接 + 首页预热
3. **代理出口决定币种**：非美国出口会回本地货币 → 用 cookie 强制美元
4. **美元价格是「分」为单位渲染**：`$3999` 实际是 **$39.99**，不修会全盘出错

详见 `references/crawl-pitfalls.md`。

---

## 六、目录结构

```
lingfei-amazon-competitor-library-mining/
├── SKILL.md                       # 给 AI Agent 读的技能说明
├── README.md                      # 你正在看的这份
├── scripts/
│   ├── crawl_amazon.py            # 抓取层：限速 + 熔断 + 断点续跑 + 三个解析器
│   ├── build_competitor_lib.py    # 步骤 1–5：建库
│   ├── score_competitors.py       # 步骤 6：Jev 打分 + 归类 + 备注
│   ├── export_table.py            # 导出 Excel
│   └── run_pipeline.py            # 一键跑完
└── references/
    ├── jev-api.md                 # Jev API 口径
    ├── crawl-pitfalls.md          # 反爬与解析坑实测记录
    └── worked-example-ice-maker.md # 一次完整跑的真实读数基线（拿它对量级 / 查症状）
```

---

## 七、边界

- 只读公开页面，不登录、不操盘、不改任何账号设置
- 分数与归类由 **Jev 决策模型**给出（同一输入必得同一结论）；**备注由证据拼装**，不是模型编的
- 输出是**判断依据**，不是最终决策 —— 高分候选仍建议人工扫一眼
