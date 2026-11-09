# ABA 旺季选品分析 Skills

**解决的问题**：把「**一个方向词 → 20 个产品 → 进场时点 + 备货打法**」这套分析，
从手工跑变成**一条命令**。

你手上只要有一颗模糊的方向词（`christmas` / `halloween` / `宠物` / `露营`），
加上 ABA 热搜词周报，就能拿到一份带**进场时点**和**备货建议**的产品机会报告。

配套文章：《[附送Skills] ABA挖旺季选品机会：一个方向词拆出20个品类》

---

## 30 秒试跑（不需要任何数据、不需要任何 key）

```bash
pip install -r requirements.txt
python run.py demo
```

它会自己造 4 周演示数据 → 跑完整链路 → 在 `demo/out/` 出报告。
演示数据里**故意埋了坑**（噪音词、子类词、超阈值词），你一眼能看到三道闸门各自挡掉了什么。

---

## 用自己的数据

```bash
# 0) 准备：把 ABA 周报 CSV 放进一个目录
#    亚马逊后台 → 品牌分析 → 搜索词报告 → 按周下载
#    文件名要带 YYYY_MM_DD（如 US_Top_Search_Terms_Simple_Week_2025_11_08.csv）

# 1) 建议先转 parquet 缓存（第 2 遍起快一个量级）
python run.py cache --csv-dir ./aba --out ./.cache

# 2) 一条命令出报告
python run.py all --csv-dir ./aba --pack christmas \
                 --cache-dir ./.cache --out ./out
```

产出 `out/圣诞季Christmas_机会报告.md` / `.xlsx` / `.json`。

### 常用参数

| 参数 | 说明 |
|---|---|
| `--pack` | 规则包名（内置 `christmas` / `halloween` / `valentine`）或你自己的 JSON 路径 |
| `--week-from` / `--week-to` | 只分析某段周次，如 `--week-from 2025_10_18 --week-to 2026_01_03` |
| `--valid-rank` | 有效词阈值，默认 **5000** |
| `--top` | 取前 N 个产品，默认 20 |
| `--threads` | DuckDB 线程数，默认 4 |

### 只想看某一步

```bash
python run.py explain --pack christmas   # 三道闸门到底怎么判的（不读数据）
python run.py scan   --csv-dir ./aba     # 只扫词 + 聚类
python run.py rhythm --csv-dir ./aba     # 只出六维度节奏
python run.py deep   --csv-dir ./aba --product 圣诞袜   # 只深挖一个产品
```

---

## 六条内置口径

每一条都对应一个**真实的坑**，也都能单独关掉/修改。

### ① 词根匹配边界 —— 别让 `men` 命中 `women`

`LIKE '%men%'` 会命中 `women`、`omen`、`garment`、`amendment`。
一个词根越短，噪音越大，而且**结果看着像对的**，这是最容易静默出错的一步。

但**两边都加边界又会矫枉过正** —— 实测会把 `christmaslights`、`christmastime`、
`christmasdecor` 这类**连写搜索词**一起剔掉，而这些是有真实商业价值的。

所以默认口径 `auto` 分两种情况：

| 词根长度 | 边界 | 理由 |
|---|---|---|
| **≥ 6 字符**（`christmas` / `halloween`） | **只查左边界** | 长词根当前缀很安全，保住连写词 |
| **< 6 字符**（`men` / `xmas`） | **两边都查** | 短词根容易撞上无关词（`menswear`/`mental`/`mention`） |

左边界才是主力：`boxmasters`（里面嵌着 `xmas`）、`women`/`omen`/`garment`（嵌着 `men`）
**都是"左边一个字母"就挡住了**。

⚠️ **左边界也会挡掉一类词**：`3 ftchristmas tree` 这种「数字+单位直接贴在词根上」的写法，
三种口径里**只有 `loose` 保留**（真词大概率写成 `3 ft christmas tree`，带空格就正常命中）。
以 `run.py explain` 打印的真值表为准，别背文档。

```bash
python run.py explain --pack christmas   # 看三种口径的实际判定差异
python run.py --roots-mode auto          # 默认，推荐
python run.py --roots-mode strict        # 一律两边（会剔连写词，慎用）
python run.py --roots-mode loose         # 不查边界 = LIKE，只用来复现别人的数
```

> 🔴 **RE2 陷阱**：DuckDB 的 `regexp_matches` 用 RE2，**不支持 lookbehind / lookahead**。
> 写成 `(?<![a-z])` 会直接报 `invalid perl operator`。所以边界必须写成**消费式**字符类：
> `(^|[^a-z])` … `([^a-z]|$)`。本工具不需要 lookaround，所以两边行为一致。

### ② 有效词过滤阈值 —— 排名 ≤ 5000

一个方向词扫出来几万个词，**绝大部分是噪音**（圣诞案例里有效信号只占 0.17%）。
默认取 `Search Frequency Rank ≤ 5000` 作为"稳定头部词"。

改阈值：`--valid-rank 3000`

### ③ 产品实体聚类 —— 词 ≠ 产品

扫出来的是**词**，不是**产品**。必须归到产品实体上，否则
`christmas stocking` 和 `christmas stocking stuffers` 会被当成同一个东西 ——
而后者是**独立产品**（袜内填充礼物），机会完全不同。

规则存在 `abapeak/rules/christmas.json`，**顺序铁律**：

```
subclass_guards（子类守卫） → ambiguity（同形异义） → products（首个命中生效）
```

### ④ 六维度体检 + 「进场看加速度，不看词量」

> **词量 = 积分（累积结果）；加速度 = 导数（变化速度）。进场看导数，不看积分。**

- **进场点** = 加速度（环比增量）见顶的那一周
- **加码点** = 词量见顶的那一周
- **撤退点** = 加速度断崖的那一周

圣诞实战：加速度峰值 **11/08（+35,823）**，词量顶点 **12/06（167,027）** ——
**进场信号比"看起来最热"的那周早整整 4 周**。海运 30–40 天 + 上架 + 广告起量，
等词量见顶才进场，时间已经不够了。

⚠️ **加速度必须用「全部词条数」算**，不能用「rank ≤ 5000 的头部词」算 ——
头部词每周都在榜，差分全是 0，节奏图是平的。

六维度：**起量周 / 加速值 / 量级 / 节奏（含半衰期）/ 尾周占比 / 形态**。

### ⑤ DuckDB 列裁剪 —— 2.9M 行/周也不 OOM

单周文件 1.7–2.3 GB、约 290 万行、21 列。**只 SELECT 你真正要的列**，
DuckDB 就跳过其余列的解析 —— `--cols light` 只读 2 列。

三个必须知道的读法：
- **第一行不是表头，是 Reporting Range 元数据** → 必须 `skip=1`，否则列名全错位
- **列名单复数不一致**：`Top Clicked Brand #1` 是单数，`Brands #2` / `#3` 是复数
- 反复跑同一批文件 → 先 `cache` 转 parquet，之后亚秒级

### ⑥ 子类语义甄别 —— 剔除「女性丝袜」这类误命中

`stockings` 在英文里同时是「圣诞袜」和「女性丝袜」。
`stockings for women`、`thigh high stockings` 跟圣诞毫无关系，只是词里恰好有 stocking。

**不剔除的话，一个完全不同的品类会被算进来，让数据虚高。**
任何种子词都要过一遍人工甄别 —— **不存在全自动的正确规则**，这一步必须人看。

---

## 内置三个季节 + 怎么换一个

```bash
python run.py packs
```

| 规则包 | 词根 | 产品类 |
|---|---|---|
| `christmas` 圣诞季 | `christmas` / `xmas` | 20 |
| `halloween` 万圣节 | `halloween` / `trick or treat` | 21 |
| `valentine` 情人节 | `valentine` / `galentine` | 22 |

三个包**共用同一套代码**，全流程只换 JSON：

```bash
python run.py all --csv-dir ./aba --pack halloween --out ./out
python run.py all --csv-dir ./aba --pack valentine --out ./out
```

换一个全新的季节，只改两个地方：

```bash
cp abapeak/rules/halloween.json abapeak/rules/<你的季节>.json
# ① roots   —— 这个季节的方向词（别收全年都在用的词，见 halloween 包里为什么不收 spooky）
# ② products —— 按「越具体越靠前」排；note 里写了每个包踩过的坑，照着改
python run.py all --csv-dir ./aba --pack <你的季节> --out ./out
```

规则包**自解释**：所有以 `_` 开头的字段都是注释（`_说明` / `_顺序铁律` / `_note`…），
另有三个可选字段能让 `run.py explain` 直接讲清楚**你的**包：

| 字段 | 作用 |
|---|---|
| `_root_probes` | 词根正反例（连写词保住了吗？嵌字假命中挡住了吗？） |
| `_explain_samples` | 三道闸门抽样（哪些词被守卫/同形异义摘掉） |
| `_boundary_compare` | `auto` / `strict` / `loose` 三口径对比 |

不填也能跑，只是 `explain` 会退回用圣诞的默认样例。

> 三个包里最值得读的是 `_note`：`bat` 为什么写成 `` ` bat ` ``、
> 「宠物装扮」为什么必须排在「服装装扮」前面、「服饰配件」为什么不能并进「服装装扮」——
> 每条都对应一个真踩过的坑，都是同一句话的不同版本：**宽泛的关键词会吃掉更具体的品类**。

---

## 输出长什么样

| 章节 | 内容 |
|---|---|
| 一、数据规模 | 12 周记录数 / **去重词数** / 有效词数 / 有效信号占比 |
| 二、大盘节奏 | 每周词条数 + 环比，标出**加速度峰**与**词量顶点**和领先周数 |
| 三、产品机会清单 | 每个产品的六维度 |
| 四、分析 → 决策 | 每个指标对应的**动作** |
| 五、形态 → 备货策略 | 4 种形态各自怎么备货 |

---

## 两个数别混（很多人在这里踩坑）

| 指标 | 含义 | 圣诞案例（12 周实测） |
|---|---|---|
| **12 周词条记录数** | 同一词在多周出现会**重复计** | **1,027,121** |
| **去重词数** | 不同词的数量 | **217,022** |
| **有效词数** | 去重后 rank ≤ 5000 | **377** |

**「有效信号只占 0.17%」的分母是「去重词数」**（377 / 217,022 = 0.174%），
**不是记录数**。把这两个数混起来会差 **4.7 倍**。

> 校对过的对应关系：用 `--roots-mode loose`（等价 `LIKE '%christmas%'`）跑 12 周
> （`2025_10_18` ~ `2026_01_03`），本工具算出的**去重词数正好是 217,022**、
> 分周去重之和正好是 **1,027,121** —— 与文章的 217,022 和它自己的周表完全一致。
> 换用默认的 `auto` 口径会变成 216,7xx（剔掉 `boxmasters` 这类嵌字假命中），
> 差别只在真假命中，结论不变。

---

## 自测

```bash
python tests/test_pipeline.py     # 108 项，不需要数据/网络/key
```

---

## 目录

```
run.py                      一条命令入口
abapeak/
  ├ schema.py               口径⑤ 读法（skip=1 / 列名陷阱 / 列裁剪）
  ├ roots.py                口径① 词根边界
  ├ cluster.py              口径③⑥ 聚类 + 子类守卫 + 同形异义
  ├ rhythm.py               口径④ 六维度 + 加速度/词量峰 + 形态
  ├ pipeline.py             主流水线（扫词/深挖/parquet 缓存）
  ├ export.py               报告（markdown + xlsx + json）
  ├ cli.py                  命令行
  └ rules/
      christmas.json        圣诞规则包（20 类）
      halloween.json        万圣节规则包（21 类）
      valentine.json        情人节规则包（22 类）
demo/make_demo_aba.py       造演示数据
tests/test_pipeline.py      自测
```

依赖只要两个：`duckdb`、`openpyxl`。
