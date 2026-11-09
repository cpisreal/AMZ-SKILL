---
name: lingfei-amazon-prompts-report
description: >-
  把亚马逊 Sponsored Products Prompts 报表（Alexa / Rufus / AI 购物提问报告）算成结论，再写成一篇能发的公众号文章。
  触发：用户甩来 Prompts report / 提示词报告 / Alexa 广告数据报告 / AI 购物提问报表，说「分析一下」「拆一下这张表」
  「写篇公众号」「这个报表怎么看」；或提到「五把刀」五步分析法。含可跑的分析引擎（体检 / 集中度 / 意图分层 /
  四象限 / 文本特征）、出图脚本（Apollo 白底极简 10.5pt 口径）、文章骨架模板、凌飞口吻规则与成稿结构提要。
  一句话：报表进，五把刀 + 一份名单 + 一篇能发的文章出。
version: 1.0.0
author: hermes
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [amazon, sponsored-products, prompts-report, alexa, rufus, 报表分析, 公众号, 五把刀]
---

# Prompts 报表 → 五把刀 → 一篇能发的文章

## 什么时候用

> 「这份 Prompts 报表帮我看看」/「提示词报告分析一下」/「Alexa 广告数据报告怎么读」/
> 「写成公众号」/「五把刀跑一遍」

输入是一份 **Sponsored Products Prompts report**（.xlsx / .csv，广告后台 报表 → 新建报表 →
Report type = Prompts）。输出三样：**读数表、优化名单、文章**。

不适用：Search Term Report（那是词，不是话）、Bulk 操作表（那是改账户结构的活，不在本 skill 范围）。

## 30 秒速判卡

| 问题 | 答案 | 不成立时 |
|---|---|---|
| 表里有没有 `Prompt details` 列？ | 有 = 是 Prompts 报表 | 没有就别硬套，先确认 Report type |
| 有销售的行占比多少？ | <10% 走分层，10–20% 分层+挑名单，>20% 可以直接挑名单 | 0 行先排四因（功能刚开/日期错/没投到 prompt 位/报表还在生成） |
| 前 10% 提问吃掉多少花费、交回多少销售？ | 开口大 = 有单点黑洞；开口小 = 平均撒钱 | 两种都要往下走分层，别在活动层找答案 |
| 曝光占比 vs 销售占比，哪组对不上？ | 这是全文唯一主角 | 组内样本 <20 条只当线索 |
| 低曝光高效的提问交回多少销售？ | 常常是全场一半以上 | 这一格是被饿着的钱，不是噪音 |

**顺序不能乱**：先判层级，再判钱集中不集中，再分层，再挑名单，最后才改字。
跳过前两步直接排 ACOS，会把预算推向最差的地方，而且自己以为在优化。

## 七步流水线

### 1. 认表（1 分钟）

- 确认有 `Prompt details`、`Impressions`、`Clicks`、`Spend`、`7 Day Total Sales` 这几列。
- 记下日期范围、站点、`Time unit`。**归因窗口是 7 天**，写进文章的口径段。
- 打开是空表 → 四个原因逐个排：功能刚开、日期选错、广告没投到 prompt 位、报表还在生成。

### 2. 跑分析引擎

```bash
python3 scripts/analyze_prompts_report.py --input report.xlsx --out-dir out
# 阈值按客户目标线改；曝光阈值给数字或 median
python3 scripts/analyze_prompts_report.py --input report.xlsx --out-dir out \
        --imp-threshold 3000 --acos-target 0.30
```

产出三份：

| 文件 | 内容 |
|---|---|
| `out/analysis.json` | 全部读数（体检/集中度/意图/四象限/特征/结构/极值/数据质量） |
| `out/report.md` | 人看的读数表，只有数字和口径，**不含结论** |
| `out/prompts.csv` | 每条提问一行：曝光/点击/CTR/花费/销售/ACOS/意图/象限 —— **这就是优化名单的原料** |

### 3. 把读数翻成一句话

对着 `report.md` 回答三个问题，写下来，**先发给用户看，别急着写文章**：

1. 问题在哪一层？（分层结构 / 少数几条 / 没有明显问题）
2. 钱集中在哪？（单点黑洞 / 平均撒钱）
3. 哪一类话被喂多了、哪一类被饿着？

判读口径全在 `references/judgment-rules.md`，别凭感觉改阈值。

### 4. 出图

```bash
python3 scripts/build_figures.py --analysis out/analysis.json --items out/prompts.csv --out-dir out/figures
```

七张：行 vs 提问、累计曲线、意图双柱、四象限散点、文本特征 CTR、四格销售占比、五步链条。
视觉口径写在脚本头部（12×8 英寸 @200dpi、正文 10.5pt、标题 15pt、注 9pt、脚注 8pt、
主色 `#1D4ED8`、白底、中文 Hiragino Sans GB）。**别自行放大字号**，那是这个库的固定口径。

### 5. 写文章

骨架照 `templates/article-template.md`，每节该放哪个数字见 `references/article-skeleton.md`。
口吻照 `references/voice-lingfei.md`（若不需要个人口吻，用中性的技术写法也行，但骨架与顺序不变）。

写之前先回答一个问题：**这篇给谁看**。给没打开过这张表的操盘手看，就从「这行数据在说什么」讲起；
给老手看，就从「五个常见误判」讲起。两头都想要，就会两头都不满足。

### 6. 配图落位 + 自检

- 每个大节至少一张图；图注要能独立看懂（不写「如上图所示」）。
- 图里不许出现真实 ASIN、品牌名、账号。
- **脱敏要脱两层，不止品类。** 第一层是品类（`〔品类〕` / `[CATEGORY]`）；
  第二层是**属性词** —— 材质 → `〔材质〕`、功能 → `〔功能〕`、结构 → `〔结构〕`。
  理由很实在：**品类词删了，属性词照样能把它拼回来** —— 一个材质词加一个功能词摆在那里，
  读者自己就把品类补出来了。
- 所以文章里引用买家原话时，**只保留结构，不保留词**：写成
  「[CATEGORY] 要 100%〔效果〕，材质是〔材质〕，还要〔功能〕」，
  或者直接标约束数（「四个约束」/「零约束」）。这样"具体的话值钱、泛问不值钱"这个论证
  反而更清楚，因为论据本来就是**约束的数量**，不是哪个具体的词。
- 例外：`19 英寸`、`100%`、`ACOS` 这类**纯数字**不指向任何品类，可以留。
- 打标时用原文（`references/intent-taxonomy.md` 的词表），**只用于算，不用于写**。
- 交付前过一遍「去 AI 味」检查（破折号、中文冒号堆叠、翻案腔、三连排比），**数字一个都不许动**。

### 7. 交付

```
out/report.md（读数）
out/prompts.csv（名单）
out/figures/*.png（7 张）
文章 md / 飞书文档
```

## 🔴 红线

1. **先聚合，再算比率。** 一行 = 一个提问 × 一个活动 × 一个 ASIN × 一天。直接对行排 ACOS，
   几百条 0.4 美元花费的行会把排名全污染掉。
2. **不对比率列取平均。** ACOS、CTR、CPC 必须用「总花费 ÷ 总销售」重算。
3. **阈值跑之前定死。** 看完结果再挪线，你会得到你想要的任何结论。
4. **组内样本 <20 条只当线索。** 不写「品牌词最赚钱」这种话。
5. **组内 ACOS 不跨组排名。** 各组曝光基数不同，跨组比 ACOS 会反向。
6. **主角是曝光占比 vs 销售占比**，不是 ACOS 高低。
7. **低曝光低效那一格不逐条优化。** 它通常占七八成条数，逐条修是纯消耗。
8. **单一账户 30 天不是规律。** 跨类目再验一次才叫规律，文章里要写明这条边界。
9. **ACOS 空白 ≠ 0**，它表示这一分钱销售都没有；聚合时当 0 会把全场 ACOS 算低。
10. **它只记录跑出过曝光的提问。** 买家问了但广告没展示的，不在这张表里 —— 这是硬边界。

## 坑（都是实测踩过的）

| 坑 | 症状 | 解法 |
|---|---|---|
| Amazon 导出的 xlsx 里 `<dimension ref="A1">` 是坏的 | `openpyxl` read_only 只读到 1 行，看着像空表 | 读之前 `ws.reset_dimensions()`（引擎已内置） |
| 列名带尾空格、`#`、大小写不一 | `7 Day Total Sales ` 匹配不上 | 归一化后匹配；引擎按别名表找列 |
| `7 Day Total Sales` 与 `7 Day Advertised SKU Sales` | 前缀匹配会串列 | 先精确匹配，再按别名回退 |
| CTR / ACOS 有的导出是 `0.125` 有的是 `12.5%` | 差 100 倍 | 带 `%` 就除 100 |
| 同一句话占多行 | 长尾提问被算到头部 | 先聚合到 `Prompt details` |
| 意图标签规则一改，组内数字全变 | 同一篇文章前后数字打架 | 一篇文章只用一套规则；换规则就整篇重跑 |
| 打标「其他」组想清零 | 硬塞把结论带偏 | 允许「其他」，报告覆盖率即可 |
| matplotlib 中文里出现 `$` | 后面的中文被当公式吞掉 | 转义或别用 `$` |
| 图表里放了真实 ASIN / 品牌 | 客户信息泄漏 | 一律 `〔品类〕`，ASIN 只在内部名单里 |

## 支持文件

| 文件 | 用途 |
|---|---|
| `scripts/analyze_prompts_report.py` | 主引擎：报表 → analysis.json / report.md / prompts.csv。`--self-test` 跑内置检查 |
| `scripts/build_figures.py` | 七张图，口径写死在脚本头部 |
| `scripts/make_demo_report.py` | 造一份同结构的合成报表（**测试只用它，别拿客户真表试**） |
| `references/judgment-rules.md` | 每一把刀的取数、算法、判读阈值、反例 |
| `references/intent-taxonomy.md` | 六类意图 + 五类文本特征的正则与优先级语义 |
| `references/article-skeleton.md` | 文章十一节骨架，每节放什么数字 |
| `references/voice-lingfei.md` | 凌飞口吻：六个可校验指纹 + 十个动作 + 五条禁忌 |
| `references/worked-example.md` | 成稿结构提要 + 反例清单 + 自检表（**不含任何真实数字、买家原话、品类**） |
| `templates/article-template.md` | 带配图位的文章骨架，复制后填 |
| `examples/` | 合成报表跑出来的读数样例（demo 产物） |
