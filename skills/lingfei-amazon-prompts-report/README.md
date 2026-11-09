# Prompts 报表 → 五把刀 → 一篇能发的文章

把亚马逊 **Sponsored Products Prompts report**（也叫 Alexa 广告数据报告 / Rufus 报告 /
AI 购物提问报表）算成结论，再写成一篇公众号文章。

报表进 → 读数、优化名单、七张图、一篇文章出。

---

## 它解决什么

拿到这份报表的人，通常的动作是**按 ACOS 排序，然后去给第一名降价**。
这个动作在这份表上几乎总是错的，原因有三条：

1. 一行 ≠ 一条提问（一个提问 × 一个活动 × 一个 ASIN × 一天），不聚合就排比率，几百条小分母行会把排名全污染。
2. 这份表里 **ACOS 高不代表该降价** —— prompt 位由算法按商品页内容匹配，你没法投、没法否，只能改商品页。
3. 真正该看的是**曝光占比 vs 销售占比的错配**，不是 ACOS 高低。

五把刀就是把这套判断固化成五步，每步有固定取数、固定算法、固定判读口径。

---

## 依赖

- Python 3.8+
- `openpyxl`（读 .xlsx；.csv 不需要）
- `matplotlib`（出图）
- 中文字体：macOS 自带 Hiragino Sans GB；Linux 可换 Noto Sans CJK（改 `scripts/build_figures.py` 顶部）

用你环境的包管理器安装这两个库即可，没有别的依赖。

---

## 五分钟跑通（用合成数据，不碰客户报表）

```bash
# 1) 造一份同结构的合成报表（547 行 / 311 条提问，含四类典型病态）
python3 scripts/make_demo_report.py --out /tmp/demo/demo.xlsx

# 2) 分析
python3 scripts/analyze_prompts_report.py --input /tmp/demo/demo.xlsx --out-dir /tmp/demo/out

# 3) 出图
python3 scripts/build_figures.py --analysis /tmp/demo/out/analysis.json \
        --items /tmp/demo/out/prompts.csv --out-dir /tmp/demo/out/figures
```

跑完会看到：

```
rows=547 prompts=311 spend=2144.37 sales=4666.88 acos=45.9%
written: /tmp/demo/out/analysis.json /tmp/demo/out/report.md /tmp/demo/out/prompts.csv
wrote /tmp/demo/out/figures/fig01_rows_vs_prompts.png
...
```

`examples/` 里存着这次跑出来的完整产物，可以拿来对照"输出应该长什么样"。

**真报表怎么跑**：把 `--input` 换成你的文件，`--imp-threshold` 和 `--acos-target` 换成
客户的目标线（默认 3,000 曝光 / 30% ACOS）。阈值必须**跑之前**定，别看完了再挪。

---

## 输出的三份东西

| 文件 | 给谁 | 内容 |
|---|---|---|
| `out/report.md` | 你自己 | 八节读数：体检 / 集中度 / 意图分层 / 四象限 / 文本特征 / 结构 / 极值样本 / 数据质量。**只有数字和口径，没有结论** |
| `out/prompts.csv` | 执行的人 | 每条提问一行：曝光、点击、CTR、花费、销售、ACOS、意图组、所属象限。**这就是优化名单** |
| `out/analysis.json` | 后续脚本 | 全部读数，出图与二次计算都读它 |

判断在哪做？在 `SKILL.md` 和 `references/judgment-rules.md` 里。
引擎只交出读数 —— 它不会替你下"这个账户有问题"的结论，那需要人看。

---

## 目录

```
lingfei-amazon-prompts-report/
├── SKILL.md                         主文件：触发条件、速判卡、七步流水线、红线、坑
├── README.md                        这份
├── scripts/
│   ├── analyze_prompts_report.py    主引擎（含 --self-test）
│   ├── build_figures.py             七张图，视觉口径写在脚本头部
│   └── make_demo_report.py          合成报表生成器（测试只用它）
├── references/
│   ├── judgment-rules.md            五把刀：取数 / 算法 / 阈值 / 反例
│   ├── intent-taxonomy.md           六类意图 + 五类文本特征的正则与优先级
│   ├── article-skeleton.md          文章十一节骨架，每节放什么数字
│   ├── voice-lingfei.md             个人口吻规则（六个指纹 / 十个动作 / 五条禁忌）
│   └── worked-example.md            成稿结构提要 + 自检清单（不含真实数据）
├── templates/
│   └── article-template.md          带配图位的骨架，复制后填
└── examples/
    ├── report.md                    合成数据跑出的读数样例
    ├── prompts.csv                  合成数据跑出的名单样例
    └── figures/
        ├── fig01_rows_vs_prompts.png
        ├── fig02_concentration.png
        ├── fig03_intent.png
        ├── fig04_quadrant.png
        ├── fig05_features.png
        ├── fig06_quadrant_sales.png
        └── fig07_pipeline.png
```

---

## 图的口径（别自己改）

12 × 8 英寸 @ 200 dpi；正文 10.5 pt、图标题 15 pt、注 9 pt、脚注 8 pt；
主色 `#1D4ED8`，文字 `#0B1220` / `#6B7280`，网格 `#E6E9EE`，白底，不用深色科技风。

字号是照已发表文章的出图脚本量出来的。「看着有点小、放大一点」这条路上踩过三次坑
（16pt / 13pt / 11.5pt 全部被判太大），所以默认值就是 10.5pt，改之前先问一句。

---

## 用它之前先确认三件事

1. 这份表是不是 **Report type = Prompts**（必须有 `Prompt details` 列）。Search Term Report 不适用。
2. 归因窗口是不是 **7 天**（绝大多数站点是）。文章里要写明。
3. 客户数据能不能写进文章。**默认按两层脱敏口径**：品类写 `〔品类〕` / `[CATEGORY]`，
   **属性词也一起脱**（材质 → `〔材质〕`、功能 → `〔功能〕`、结构 → `〔结构〕`），
   因为属性词组合起来就能反推品类；纯数字（19 英寸、100%）可以留。
   ASIN 与品牌名不进任何对外产物。打标用原文，写文章用结构。
