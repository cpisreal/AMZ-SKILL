# 打标规则：六类意图 + 五类文本特征

两套规则用途不同，**别混用**：

| | 意图分层（第三把刀） | 文本特征（第五把刀） |
|---|---|---|
| 打标方式 | **一条一个标签**，先命中先算 | **一条可命中多个** |
| 分组数 | 6 类 + 其他 | 5 类，允许重叠 |
| 回答的问题 | 这类话在吃什么流量 | 这个卖点有没有人问 |

规则是**模板**，不是真理。换一套词表，组内数字就变 —— 所以：

- 一篇文章只能用一套规则（中途换规则，前后数字会打架）。
- 文章里若引用组内数字，把规则表一起贴出来，读者才能复现。
- 换了规则要整篇重跑，不要只改一张表。

🔴 **这套词表只用于打标，不用于写作。** 下列英文词（velvet / linen / blackout / thermal…）
组合起来足以反推品类。对外文章里引用买家原话时，一律换成 `〔材质〕` `〔功能〕` `〔场景〕`，
或只标约束数（「三个约束」/「零约束」）—— 论证靠的是约束数量，不是具体哪个词。
详见 `SKILL.md` §6 与 `references/worked-example.md` 的脱敏说明。

---

## 六类意图（顺序 = 优先级）

引擎里的 `DEFAULT_INTENTS`，**从上往下第一个命中就停**。这个顺序的语义是
**「具体的压过泛问的」**：一句话里点名了某个麻烦，就归那个麻烦，不归「通用疑问」。

| 优先级 | 组 | 这句话在干什么 | 触发特征（正则摘要） | 典型句子 |
|---|---|---|---|---|
| 1 | 品牌决策 | 在几个牌子之间比 | vs / versus / compare / better than / why choose / brand | why choose this brand of cover |
| 2 | 痛点担忧 | 在问能不能解决某个麻烦 | noise / slip / water / stain / scratch / dust / odor / smell / fade / shrink | can it help reduce outside noise |
| 3 | 材质属性 | 在确认具体材质和功能 | velvet / linen / cotton / thermal / blackout / insulated / stretch / elastic / fabric | thermal insulated cover for winter |
| 4 | 易用维护 | 好不好装、好不好洗、尺寸合不合 | wash / clean / machine / install / assemble / easy / fit / size / inch | machine washable for pet homes |
| 5 | 场景人群 | 在说自己家的具体处境 | pet / dog / cat / kid / baby / family / bedroom / outdoor / patio / winter / dorm | cover for a bedroom with two cats |
| 6 | 通用疑问 | 泛问这个产品行不行（兜底） | 以 does / do / is / are / can / could / will / would / should / what / how / why 开头 | does it absorb water effectively |
| — | 其他 | 以上都不中 | — | （允许存在，报告覆盖率） |

**为什么「通用疑问」放最后**：如果放最前，"can it help reduce outside noise" 会被算成泛问，
而它其实是一条很具体的诉求。放最后，泛问只收真正没有具体名词的句子，
下面这个结论才立得住：**泛问吃走大部分曝光，而具体处境被饿着。**

**「其他」不硬塞。** 覆盖率一般落在 85%–92%；低于 80% 说明词表跟这个品类不贴合，
先补词表（同义名词、这个类目的专有说法），再跑。

**换优先级会得到完全不同但同样自洽的结论。** 如果你的分析目标是"泛问占比有多大"，
就把「通用疑问」提到最前；那时泛问组会明显变大。**两种都可以，但不能混着写。**

---

## 五类文本特征（可多命中）

引擎里的 `DEFAULT_FEATURES`。一条提问可以同时命中尺寸 + 人群 + 场景。

| 特征 | 在找什么 | 正则摘要 |
|---|---|---|
| 尺寸 | 有没有说出具体数字和英寸 | `\d+\s*(inch\|in\|cm)` / fits up to / size / dimension / measure |
| 材质 | 有没有点名材质或工艺 | velvet / linen / cotton / polyester / thermal / blackout / insulated / stretch / elastic / fabric |
| 人群 | 有没有说清是谁在用 | pet / dog / cat / kid / child / baby / family |
| 场景 | 有没有说清用在哪 | winter / summer / bedroom / living room / outdoor / patio / office / dorm / apartment |
| 担忧 | 有没有在问某个具体麻烦 | noise / slip / water / stain / scratch / dust / allerg* / odor / smell / fade / shrink |

**五类之间的效率差往往大到不像同一份表**（尺寸类 CTR 常见是全场三到五倍，
担忧类曝光占比 39% 但 CTR 只有全场 0.37 倍）。这个反差本身就是文章最有说服力的那张图。

---

## 自定义规则

```bash
python3 scripts/analyze_prompts_report.py --input report.xlsx --out-dir out --rules my_rules.json
```

```json
{
  "intents": [
    {"name": "品牌决策", "regex": "\\b(vs\\.?|versus|compare|better than)\\b"},
    {"name": "痛点担忧", "regex": "\\b(noise|slip|stain)\\b"},
    {"name": "材质属性", "regex": "\\b(velvet|linen|blackout)\\b"},
    {"name": "易用维护", "regex": "\\b(wash|install|fit|size)\\b"},
    {"name": "场景人群", "regex": "\\b(pet|kid|bedroom|winter)\\b"},
    {"name": "通用疑问", "regex": "^(does|do|is|are|can|will)\\b"}
  ],
  "features": [
    {"name": "尺寸", "regex": "\\d+\\s*(inch|in\\b)"},
    {"name": "材质", "regex": "\\b(velvet|linen|thermal)\\b"},
    {"name": "人群", "regex": "\\b(pet|kid|family)\\b"},
    {"name": "场景", "regex": "\\b(winter|bedroom|outdoor)\\b"},
    {"name": "担忧", "regex": "\\b(noise|slip|water|stain)\\b"}
  ]
}
```

数组顺序 = 优先级。省略某一组也不会报错，只是那一类提问会落到「其他」。

---

## 词表适配建议（换品类时）

- 按品类各抽 30 条真实提问，把买家自己的说法抄进词表（上面的正则可以当起点）
- 同一个词在不同品类里权重完全不同，别跨品类套用

先抽 30 条真实提问读一遍，把买家自己的说法抄进词表 —— **别照抄竞品文章里的词**。
