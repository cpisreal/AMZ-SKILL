---
name: Heating Pad
description: "亚马逊美国站加热垫/肩颈热敷（Wireless Heating Pad、shoulder heat wrap）卖家的每日运营决策简报。抓 Open-Meteo 美国 12 城未来 7 天降雪与最低温，结合当日美国寒潮/国家气象局资讯，判定备战期/临门期/爆发期/回落期，给出起量倒计时与 Listing、广告、转化、库存的 P0/P1/P2 动作，存档并按需推送到企业微信。触发词：加热垫简报、热敷垫运营、Heating Pad 日报、美国降温起量、雪季简报、寒潮告警、冬季备货节奏。"
---

# Heating Pad · 美国站加热垫雪季运营简报

## Purpose

这不是天气预报。这是一个**把天气翻译成运营动作**的每日决策系统。

每天只回答三个问题，且必须给出可执行的答案：

1. **美国大概什么时候降温？** → 起量倒计时（周/天）+ 时间轴。
2. **现在市场什么情况？** → NWS 官方口径、厄尔尼诺/极地涡旋状态、竞品与社媒动态。
3. **我的链接要做什么准备？** → Listing / 广告 / 转化 / 库存 四类具体动作，按 P0/P1/P2 排序。

判断标准：读完简报，卖家当天不需要再做任何分析，直接照着 P0 动手。

## 数据契约（先读这段，否则会写错）

- 币种/温度单位：**英寸（in）与华氏度（°F）**。呈现给用户时，°F 后可用括号补 °C。
- 脚本文件名 `scripts/fetch_uk_snow.py` 是历史命名（为兼容既有定时任务），**内部抓的是美国 12 城**，与英国无关。不要在简报里出现「英国站」「英国」字样。
- 城市清单与阈值：`references/us_locations.md`。改脚本 `CITIES` 常量必须同步改那个文件。
- 脚本只输出**事实与机读信号**；阶段判定、市场解读、运营动作**由模型完成**，不得让脚本猜。

## 执行流水线（每日本地跑一次，约 1–2 分钟）

### ① 抓预报

```bash
python scripts/fetch_uk_snow.py --out state/today.json
```

- 输出 JSON 到 stdout 和 `state/today.json`，同时写 `state/latest.json`、`state/YYYY-MM-DD.json` 作为次日比对基准。
- 关键字段：
  - `cities[].days[]` → `{date, snow_in, tmin_f}`（未来 7 天，已剔除「今天」）
  - `cities[].snow_total_in` / `snow_days` / `snow_peak_in` / `tmin_7d_f`
  - `season.weeks_to_cold_peak` → 距全年最冷月还有几周
  - `signals` → `snow_in_7d`、`multi_city_low_20f`、`cold_cities`、`any_city_drop_ge_5f`、`consecutive_warmup_3d`、`coldest_city`、`snow_cities`
  - `changes` → `tmin_drops`（降幅榜，负值=变冷）、`tmin_rises`、`snow_added`、`snow_removed`、`max_single_city_drop_f`、`baseline_date`
- **首跑**：`changes.baseline_date` 为 `null` 表示无昨日快照，简报「较昨日」段写「首跑，建立基准，明日开始显示变化」，**不要编造变化数字**。
- 失败处理：`failed_cities` 非空时，简报里注明「N 城抓取失败，结论基于其余城市」，**不重试超过 2 次**，不因单城失败中断整条流水线。
- 断网兜底：若全部城市失败，改用 WebSearch 的 NWS 官方预报做定性判断，并在页脚标注「今日降雪数据缺失」。

### ② 搜资讯（WebSearch，固定 3 组关键词）

依次搜索，**至少取到 2 条可引用信息**：

- `US cold snap forecast today`
- `National Weather Service winter storm`
- `US snow forecast winter 2026`

补充搜索（按需，最多 2 条）以覆盖「市场信号」段：

- `polar vortex forecast US` / `La Nina winter 2026 US`（厄尔尼诺/拉尼娜、极地涡旋口径）
- `wireless heating pad amazon best seller` / `shoulder heat wrap trend`（竞品与社媒动态）

引用规则：
- **优先 NWS / NOAA / weather.gov 等官方口径**，标注来源与日期（如「NWS 10/20 06Z 更新」）。
- 商业媒体/自媒体口径必须写「据 XX 报道」并视为弱信号。
- 气候现象（厄尔尼诺/拉尼娜/极地涡旋）只写**当前状态 + 对美东/五大湖的含义**，不写科普。
- 搜不到就写「今日无新增权威口径，沿用昨日判断」，**严禁编造日期、机构或数据**。

### ③ 判阶段（严格按表，冲突时取更靠后的阶段）

| 阶段 | 触发条件 | 起量倒计时口径 | 核心动作 ||---|---|---|---|
| **备战期** | 未来 7 天无雪 **且** 距寒冷高峰 > 4 周 | 气象周数 − 4 周 = 商业倒计时 | 优化 listing 关键词；搭建广告结构（手动精准 + 自动）；测冬季素材；完善 A+ 页面 |
| **临门期** | 未来 7 天无雪但距寒冷高峰 < 4 周，**或**有明显降温（任一城市最低温较昨日降 ≥ 5 °F） | 2–4 周，给出具体周数 | 加词（shoulder heat wrap、cordless heating pad）；加预算；上冬季场景素材（通勤/办公/居家热敷） |
| **爆发期** | 7 天内有雪 **或** 多城最低温 ≤ 20 °F | 0，已起量 | 提预算抢排名；开 Coupon/PED；卡核心词首位；开启「寒冷天气肩颈不适」场景广告 |
| **回落期** | 雪后回暖（连续 3 天最低温回升 ≥ 10 °F） | 本波结束，下一波看 2–3 周后 | 收预算；清长尾词；复盘转化数据；为下一波寒潮蓄力 |

判定细则：

- **优先级**：爆发期 > 回落期 > 临门期 > 备战期。有雪必然爆发期，回暖信号只在「本波已下过雪」时才算回落期（雪前升温回落不算）。
- **多城** = `signals.cold_cities` 长度 ≥ 2。
- **明显降温** 用 `signals.any_city_drop_ge_5f`，不是看绝对值。
- Anchorage 权重最低，**不单独触发**阶段变更，仅作说明。
- 起量倒计时 = `season.weeks_to_cold_peak` − 4 周（商业提前量），负值归 0 写作「已起量」。若 WebSearch 抓到 NWS 明确寒潮日期表，用官方日期覆盖，并注明「按 NWS 口径修正」。
- 阶段切换（如临门→爆发）必须在「今日结论」里**点名**，并说明触发证据。

### ④ 出简报

严格用下面模板，手机友好（短句、短行、善用 emoji 与分隔，不用宽表格），存档到：

```
logs/us-heatpad-brief-YYYY-MM-DD.md
```

> 命名说明：早期版本用 `uk-snow-brief-`。**新文件统一用 `us-heatpad-brief-`**；若目录里已有 `uk-snow-brief-*` 历史文件，保持原样不迁移、不改名。

### ⑤ 推送企业微信

用 `wecom-cli` 发消息（先 `wecom-cli auth show --status` 确认 authorized）：

- **日报**：每天 09:30 推送，用模板全文的精简版（保留全部 7 个板块，每块压到 1–3 行）。
- **降雪告警**：`signals.snow_in_7d == true` **且** 昨日基线没有雪 / 或新增城市降雪（`changes.snow_added` 非空）时，**当天立即额外推一条**，不等 09:30。内容只写：哪个城、哪天、多少英寸、一句话动作。
- 降温告警（可选）：`any_city_drop_ge_5f` 为真时，在告警里附带一句「XX 城最低温较昨日跌 X °F」。
- 推送失败（如 850002/850003 权限问题）不阻塞日报存档，把原文照打印到会话里，并告知用户授权问题。

### ⑥ 三条硬告警规则（每日必判，命中即单独推送）

| # | 触发条件（机读字段） | 含义 | 推送要求 |
|---|---|---|---|
| A1 | 7 天内**任一城** `tmin_f ≤ 32.0°F` | 跌破冰点（0°C）——室内久坐与通勤开始刺冷，加热护肩需求拐点 | 当日单独推一条 |
| A2 | 7 天内**任一城** `tmin_f ≤ 20.0°F` | 严寒（= `signals.cold_cities` 非空） | 当日单独推一条 |
| A3 | `changes.any_city_drop_ge_5f == true`（即某城 `delta_f ≤ -5.0°F`） | 急剧降温——加热护肩品类**直接起量信号** | 当日单独推一条，**且在简报里标 P0** |

判定细则：

- **A1 口径**：脚本仅有 `tmin_f`（日最低温），故 A1 以日最低温判「≤32°F」。不得改用「温度 > 0°F」之类的反向判据——全美 12 城常年恒 >0°F，必触发而失去意义。
- **A1 与 A2 可同时命中**（≤20°F 必然 ≤32°F）。同时命中时**合并为一条告警**，以 A2（更严重）为主标题，A1 不单独重发。
- **A3 优先级最高**：与 A1/A2 同天命中时，A3 独立成条，不并入。
- **A3 与 P0 冲突处理**：A3 命中即**接管当日 P0**；原 P0 顺延为 P1，并在「🔄 较昨日」段写明「X 城最低温较昨日跌 Y °F，急剧降温接管今日 P0」。全天 P0 仍只有一件。
- **告警内容格式**（每条 ≤3 行，不写板块标题）：
  - A1：`⚠️ 冰点告警｜{City} {MM/DD} 最低温 {XX.X}°F（0°C 以下）→ 建议：今日上「cold weather shoulder pain」场景广告组` 
  - A2：`🥶 严寒告警｜{City} {MM/DD} 最低温 {XX.X}°F → 建议：核心词 Top of Search 加价 30–50%，开 10–15% Coupon`
  - A3：`📉 急降告警｜{City} 最低温较昨日跌 {X.X}°F → 建议：今日 P0 改为提预算抢排名，原 P0 顺延 P1`
- **同日多条告警**：按 A3 → A2 → A1 顺序各发一条，不合并成一条长消息。
- **首跑无基线**（`changes.baseline_date == null`）：A3 不判定，写「无基线，A3 明日生效」，**严禁编造 delta**。
- **基准读取**：`load_prev()` 优先读 `state/latest.json`；若它已是今日快照（同日重跑会自己比自己，delta 恒为 0），自动退回日期早于今天的最新 `state/YYYY-MM-DD.json`。禁止为凑出 delta 伪造昨日快照数值。
- **A3 与降雪无关**：只要满足 `delta_f ≤ -5.0°F` 即告警，**不要求有雪**。降雪只是爆发期的阶段判据，不是告警前提。
- 三条全部未命中时，不推送告警，仅在简报页脚写「今日 A1/A2/A3 均未触发」。

**机读入口**（新增，别手算）：

```bash
python scripts/check_alerts.py --out state/alerts.json
```

输出 `a1_status` / `a2_status` / `a3_status`（`fired` / `not_fired` / `skipped_no_baseline`）、
`a3_takes_p0`（为 true 时必须接管 P0）、`alerts[]`（已按 A3→A2→A1 排序）、`summary_line`（页脚直接用这句）。
`baseline_only` 为 Anchorage 参考值，**不参与 A1/A2 判定**。

## 每日简报模板（**必须逐字保留结构与 emoji 标题**）

```markdown
❄️ 加热美国站 · 每日运营简报 | {{YYYY-MM-DD}}

🎯 今日结论
· 阶段：{{备战期 / 临门期 / 爆发期 / 回落期}}{{（今日切换：旧→新）}}
· 起量倒计时：{{X 周 / 已起量}}（{{气象口径：距 1 月最冷月 X 周 − 4 周提前量}}）
· 今日必做：{{一句话，只能有一件事，必须是 P0}}

⏳ 雪季时间轴
现在（{{X 周}}）→ 临门（{{X 周}}）→ 初雪起量（{{X 周}}）→ 高峰（1 月）→ 回落（3 月）
{{一行说明：本波卡在哪一格，靠什么信号确认}}

🌨 未来 7 天降雪
{{有雪：}}
· {{MM/DD}} {{City}} {{X.X}}" / {{MM/DD}} {{City}} {{X.X}}"
· 累计 {{X.X}}" ，最强单日 {{City}} {{X.X}}"
{{无雪：}}
· 7 天 12 城零降雪。最冷 {{City}} {{XX}}°F（{{-X.X}}°C），其次 {{City}} {{XX}}°F
· 跌破 20°F 的城市：{{无 / 城市名}}

📈 市场信号
· {{信号 1：NWS/NOAA 官方口径 + 日期，一句结论}}
· {{信号 2：气候现象 或 竞品/社媒动态，一句结论}}

✅ 今日行动
P0｜{{动作}}：{{具体到改哪个词/加多少预算/上哪个素材}}
P1｜{{动作}}：{{...}}
P2｜{{动作}}：{{...}}

🔄 较昨日
· {{City}} 最低温 {{XX}}°F → {{XX}}°F（{{↓X.X}}°F）
· {{新增降雪：City MM/DD 起 X.X" / 无新增降雪}}
{{首跑时写：首跑建立基准，明日开始显示变化}}

⏰ 每天 9:30 推送 ｜ 有降雪当天提前告警
{{页脚告警行：取 alerts.json 的 summary_line；全未命中写「今日 A1/A2/A3 均未触发」}}
```

## 运营动作词库（写 P0/P1/P2 时从这里选，不要泛泛而谈）

**Listing**
- 核心词补位：`shoulder heating pad`、`shoulder heat wrap`、`cordless heating pad`、`wireless heating pad`、`neck and shoulder heating pad`、`heated shoulder wrap`、`rechargeable heating pad`、`heating pad for back pain`
- 场景词：`commute`、`office`、`desk`、`travel`、`gift for mom / elderly`
- A+ 与图片：加「冷天通勤」「办公椅久坐」「居家沙发上热敷」三张场景图；A+ 首屏放「15 秒速热 / 无线可走动 / 3 档控温」
- 标题与五点卖点前置「寒冷天气肩颈僵硬」痛点句

**广告**
- 结构：手动精准（3–5 个核心词，单独广告组）+ 手动词组 + 自动（仅做拓词，否定词每周清一次）
- 爆发期：核心词抢 Top of Search 加价 +30–50%；开 SB/SBV 打「heating pad」品类大词
- 场景广告组：`cold weather shoulder pain`、`winter office warm`、`heated wrap for neck`
- 否词：`electric blanket`、`heating pad for bed`、`microwave`（若不适用）、`seed`、`reptile`

**促销与转化**
- Coupon 10–15%（爆发期）、Prime Exclusive Discount、LD/BD 卡在寒潮前 3–5 天
- 评论：主动跟进「到货后 7 天」邮件，抢「keeps me warm at desk」这类场景化 review
- 定价：爆发期不轻易降价（需求刚性），用 Coupon 控利润

**库存**
- 备战期：按去年 11–1 月日均销量 × 1.3 备货，海运截单前 45 天定稿
- 临门期：确认 FBA 入仓时效，可用 AWD/海外仓做缓冲
- 爆发期：监控可售天数，< 21 天立即空运补 10–15%
- 回落期：停止补货，清长尾 SKU，留 20% 库存给 3 月倒春寒

## 输出质量红线

1. **不写废话**：不解释算法、不写「希望对你有帮助」、不做天气科普。
2. **数字必须来自脚本**：任何温度/降雪/变化值都要能在 JSON 里找到出处；不得四舍五入到失真（保留 1 位小数）。
3. **倒计时必须是单一数字**：不能写「大约 3–6 周」，要给一个值 + 一句不确定性说明。
4. **P0 只能有一件**。三件都是 P0 = 没有优先级。
5. **阶段与动作必须一致**：备战期不能写「提预算抢排名」，回落期不能写「加词扩量」。
6. **不预测不可预测的**：不承诺「今年一定冷冬」，用「按气候常年值」「按 NWS 当前口径」限定。
7. 简报正文控制在 **350 字以内**（手机一屏半），细节留给存档文件与 references。
