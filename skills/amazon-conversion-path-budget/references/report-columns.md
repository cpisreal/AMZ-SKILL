# 转化路径报告的 20 列，逐列说清

导出的报表固定 20 列。按用途分六组，只有前四组和预算决策有关。

| 组 | 列名 | 列数 | 用途 |
|---|---|---|---|
| 时间 | Start Date、End Date | 2 | 这条路径第一次和最后一次触达的日期 |
| 主体 | Brand、Conversion path | 2 | 品牌名；唯一带顺序信息的结构字段 |
| 结果 | Sales、Purchases | 2 | 相除 = 客单价 |
| 拉新 | New-to-brand product sales、New-to-brand purchases | 2 | 判断拉新还是收割 |
| 频次 | 11 个 `... frequency` 列 | 11 | 平均被看到几次 |
| 单位 | Currency | 1 | 币种 |

## 逐列

**1. Start Date / 2. End Date**
这条路径里第一次触达和最后一次成交的日期。**每行跨度不一样**：这 298 行里，56 行是整段 30 天，10 行只跨一天。
⇒ 跨度长的路径销售额天然更大，绝对金额不能横比。

**3. Brand**
品牌名。品牌级报表，可能跨多个广告账号。

**4. Conversion path**
全表核心。用 `>` 把广告产品按发生顺序串起来，最后落在 `[Purchase]`。

```
Sponsored Products > Display (Amazon DSP) > [Purchase]
```
读法：先被商品推广点到，后来被 DSP 展示触达，然后下单。

同一个产品的写法可能不止一种，例如：
- `Sponsored Display` 与 `(Sponsored Display)`（后者带括号）
- `Display (Amazon DSP)` 与 `Online Video (Amazon DSP)` 与 `Amazon DSP`

**5. Sales / 6. Purchases**
这条路径的销售额与订单数。两者相除 = 客单价。必须一起看，只看销售额会漏掉「量大单小」和「量小单大」。

**7. New-to-brand product sales / 8. New-to-brand purchases**
这批订单里，有多少来自第一次买这个品牌的人。**这是判断拉新还是收割的唯一字段**，没有它分不清增长是真拉新还是老客回头。

**9–19. 11 个频次列**
```
Sponsored Brands display frequency
Sponsored Display display frequency     ← 和 18 列同名
Amazon DSP display frequency
Sponsored Brands video frequency
Amazon DSP online video frequency
Sponsored TV streaming TV frequency
Amazon DSP streaming TV frequency
Amazon DSP audio frequency
Sponsored Products frequency
Sponsored Display frequency             ← 和 10 列同名
Sponsored Display online video frequency
```

回答「平均被看到几次」。跟路径结构是两个问题，第一次读先遮住。

数值跨度极大：同一条路径里 SP 频次可能是 2.7、DSP 展示 7.9；换一条路径某个频次能到 113.6。没有基准时这些数看懂了也用不上。

🔴 **第 10 列和第 18 列同名**，是报表本身的问题，不是导错。
- Excel 打开会自动改名（通常加 `_1` 后缀）
- 脚本按列名取数会**永远拿到第一个，静默取错**
- 判断办法：按位置认。第 10 列紧跟 SB 频次，第 18 列在 SP 频次后面

**20. Currency**
币种（USD / EUR / GBP…）。多站点账号混用时注意别把不同币种的金额相加。

## 三个必知口径

**一笔订单只算一条路径，不拆开分摊。** 所以各行可以直接相加，加起来 = 全部销售。这不是多触点归因，不会把 100 美元拆成 60 给 SP、40 给 DSP。

**路径 ≠ 因果。** 路径里出现 DSP，只说明这个买家中途被 DSP 触达过，不说明是 DSP 促成了它。

**一行是汇总，不是明细。** 一行 = 一条路径在整段窗口的全部成交。所以算不出日销，也看不到单笔。
