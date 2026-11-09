# 美国 12 城 · 加热垫需求观测点清单

> 本文件与 `scripts/fetch_uk_snow.py` 中的 `CITIES` 常量必须保持一致（lat/lon/时区/权重）。
> 脚本文件名沿用 `fetch_uk_snow.py` 是为了兼容既有定时任务；抓取目标已是**美国站 12 城**。

## 为什么是这 12 城

加热垫（肩颈/腰背/无线）的冬季需求是「冷 + 室内久坐 + 通勤」三个条件的交集。这 12 城覆盖了

- **东北走廊**（New York / Boston / Philadelphia 圈层 / Pittsburgh）：人口密度最大、Prime 次日达覆盖最好，是转化率最高的基本盘；
- **五大湖雪带**（Chicago / Detroit / Cleveland / Milwaukee / Buffalo）：湖效应降雪（lake-effect snow）单日可下 6–12"，是**首波爆发**最灵敏的信号源；
- **上中西部**（Minneapolis）：全美最低温常客，最早跌破 20°F，是「寒冷预警」的领先指标；
- **山地/西部**（Denver / Salt Lake City）：早雪早冷，10 月即可能出雪，适合作为**季前温度哨兵**；
- **阿拉斯加**（Anchorage）：常年最冷，只作基线参照，**不参与美国本土起量判定**（权重最低）。

## 城市明细

| # | 城市 | 州 | 纬度 | 经度 | 时区 | 权重 | 角色 |
|---|---|---|---|---|---|---|---|
| 1 | New York | NY | 40.7128 | -74.0060 | America/New_York | 1.0 | 基本盘/转化标杆 |
| 2 | Chicago | IL | 41.8781 | -87.6298 | America/Chicago | 1.2 | 五大湖枢纽 |
| 3 | Denver | CO | 39.7392 | -104.9903 | America/Denver | 1.0 | 季前哨兵（早雪） |
| 4 | Minneapolis | MN | 44.9778 | -93.2650 | America/Chicago | 1.3 | 最冷领先指标 |
| 5 | Boston | MA | 42.3601 | -71.0589 | America/New_York | 1.1 | 东北高客单 |
| 6 | Detroit | MI | 42.3314 | -83.0458 | America/Detroit | 1.1 | 雪带 |
| 7 | Cleveland | OH | 41.4993 | -81.6944 | America/New_York | 1.0 | 湖效应雪带 |
| 8 | Pittsburgh | PA | 40.4406 | -79.9959 | America/New_York | 1.0 | 阿巴拉契亚冷空气通道 |
| 9 | Milwaukee | WI | 43.0389 | -87.9065 | America/Chicago | 1.0 | 湖效应雪带 |
| 10 | Buffalo | NY | 42.8864 | -78.8784 | America/New_York | 1.1 | 全美最强湖效应雪 |
| 11 | Salt Lake City | UT | 40.7608 | -111.8910 | America/Denver | 0.9 | 西部早雪 |
| 12 | Anchorage | AK | 61.2181 | -149.9003 | America/Anchorage | 0.7 | 基线参照（不判定起量） |

## 阈值定义（与 SKILL.md / 脚本常量一致）

| 常量 | 值 | 含义 |
|---|---|---|
| `SNOW_ANY_IN` | 0.1 in | 单日降雪 ≥ 0.1" 计为「有雪日」 |
| `COLD_BURST_F` | 20 °F | 最低温 ≤ 20 °F 视为严寒 |
| `COLD_BURST_CITY_N` | 2 城 | 「多城低温」门槛，连续达标进爆发期 |
| `DROP_ALERT_F` | 5 °F | 任一城 7 天最低温较昨日跌 ≥ 5 °F → 临门期（含提前告警） |
| `WARM_BACK_F` | 10 °F | 连续 3 天逐日回升且累计 ≥ 10 °F → 回暖信号（回落期） |

## 起量倒计时的口径

- **气象倒计时**：`season.weeks_to_cold_peak`，由 12 城气候常年值（1991–2020 NOAA/NCEI，月均最低温）加权算出「距全年最冷月」的周数。9 月底 ≈ 13–14 周，11 月中 ≈ 6–7 周，12 月中 ≈ 2–3 周。
- **商业倒计时**：加热垫的真实起量点比气温高峰**提前 3–5 周**（用户提前备货、礼物购买、Prime 大促前置）。所以「起量倒计时 = 气象倒计时 − 4 周」。
- **修正项**：若 WebSearch 抓到明确寒潮/极地涡旋（polar vortex）下压时间表，以官方 NWS 口径覆盖倒计时，并在简报里注明「口径来源」。

## API 参数备忘

```
GET https://api.open-meteo.com/v1/forecast
  ?latitude=..&longitude=..
  &daily=snowfall_sum,temperature_2m_min
  &temperature_unit=fahrenheit
  &precipitation_unit=inch
  &forecast_days=8          # 取 8 天，丢掉「今天」= 未来 7 天
  &timezone=America/New_York
```

- 免费、无需 Key，非商业用途限速约 10,000 次/天，12 城 1 次运行远低于限额。
- `temperature_2m_min` 是**日最低**（通常出现在凌晨 4–6 点本地时间），与「出门冷、需要热敷」的手感更匹配，故不用 `apparent_temperature` 作主指标。
- `snowfall_sum` 单位已通过 `precipitation_unit=inch` 统一为英寸。
- 气候基准可加 `--live-climate` 改走 `archive-api.open-meteo.com` 拉 2020–2024 实测，默认用内置静态表（更快、无失败风险）。
