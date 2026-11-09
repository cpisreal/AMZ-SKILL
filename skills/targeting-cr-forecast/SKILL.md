---
name: targeting-cr-forecast
description: Forecast the next sliding-window conversion rate (CVR) for every targeting in an Amazon Ads Sponsored Products daily targeting report (.xlsx/.csv). Use whenever a targeting/keyword report is supplied and the user asks for the next x-day rolling conversion rate, e.g. "预估下一个7天的转化率", "滚动转化率预测", "滑动窗口转化率", "conversion rate forecast", "rolling CVR", "CVR prediction". Pools one gradient-boosted model across targeting keys (Campaign+Ad Group+Targeting+Match) with a mandatory persistence baseline, spend-coverage reporting, and low-confidence flags.
---

# Targeting 滑动窗口转化率预测

输入一份日维度 targeting report，输出每个 Targeting 在**下一个 x 天滑动窗口**的预估转化率。

## 何时使用

用户提供了 Amazon Ads Sponsored Products targeting / keyword report（日维度），并要求"下一个 x 天窗口的转化率 / 预估转化率 / CVR"。也适用于他要求把这套口径重复跑一遍（例如 Daily 报表）。

## 目标定义（向用户复述时用这个）

```
cr_x(t) = sum(orders, t-x+1 .. t) / sum(clicks, t-x+1 .. t)     # 窗口点击为 0 时未定义(NaN)，不是 0
用 cr_x(t-1) ... cr_x(t-K) 预测 cr_x(t+1)
```

`x` 是滑动窗口长度（`--window`），`K` 是用多少个历史窗口做特征（`--lags`）——两者是**独立**的参数，不要混为一谈。

## 运行

先用 `--check-env` 确认依赖，再跑预测。推荐解释器用 `$HOME` 展开（macOS 上即 `/Users/<你的账户>/anaconda3/bin/python`），通常已装 pandas / numpy / openpyxl / scikit-learn / lightgbm：

```sh
"$HOME/anaconda3/bin/python" "<skill-dir>/scripts/forecast_cr.py" --check-env

"$HOME/anaconda3/bin/python" "<skill-dir>/scripts/forecast_cr.py" "<report.xlsx>" \
  --window 7 --lags 14 --out <outdir>
```

`<skill-dir>` 是本 skill 所在目录（含 `SKILL.md` 与 `scripts/`）。若上面那个解释器不存在，改用自己的 python，但**必须**先跑 `--check-env` 看缺什么；脚本在缺 lightgbm/sklearn 时会自动降级到内置 ridge，缺 pandas 时直接报错退出。

## 参数

| 参数 | 默认 | 说明与建议 |
|---|---|---|
| `--window` / `-w` | 7 | 滑动窗口天数 x |
| `--lags` / `-k` | 14 | 历史窗口个数 K。实测 14 明显优于 7，不建议调小 |
| `--horizon` | 1 | 向前预测几个窗口。>1 走递归预测，误差会累积，必须提示用户 |
| `--key-level` | targeting | `targeting`(4段键) / `adgroup` / `campaign`。稀疏或低置信度太高时往上退一级 |
| `--min-valid` | 15 | 序列至少要有多少个"可用窗口"(窗口点击数>0)才建模；调低会纳入更多噪声序列 |
| `--val-days` | 7 | 验证集天数（时间切分，最后 N 天） |
| `--model` | auto | `auto`(lightgbm→histgb→ridge 降级) / `gbdt` / `persistence` |
| `--features` | lags | 默认只用 lag。`lags+volume` 会加成交量特征，**实测更差**，仅在明确要求时用 |
| `--min-clicks-flag` | 5 | 上一窗口点击数低于此值标记 `low_confidence` |
| `--date-col` / `--clicks-col` / `--orders-col` | 自动 | 自动识别列名失败时手工指定 |

## 必须遵守的规则

1. **永远对照 persistence 基线。** 读 `summary.json` 或 stdout 里的 `validation`，向用户回报的是**相对基线技能**（`skill_vs_persistence`），不是 R² 绝对值。相邻窗口重叠 `(x-1)/x` 天，persistence 的 R² 天然就很高，报 R² 会严重误导。
2. **推荐列可能不是模型。** `cr_pred_recommended` 的来源由脚本在验证集上判定：模型打不过基线时自动退回 persistence，`source` 列写明用了哪个。向用户说明这一点，不要说成"模型预测"。
3. **必须回报数据现实**，缺一不可：
   - 保留了多少序列 / 总序列数、花费覆盖率（有 Spend 列时）
   - 零点击窗口占比（CR 未定义的比例）
   - `low_confidence` 占比
4. **低置信度占比高时要说实话。** 在 targeting 级这是**常态而非例外**——该粒度下大量"转化率"是 1~2 次点击的小分母噪声。此时应主动建议：改 `--key-level campaign`、或把 `--window` 调到 14、或改用"未来 x 天是否出单"的分类口径。
5. **不要宣称高准确率。** 该任务的本质接近"抄上一个窗口"，任何模型增益都要用相对基线的口径表达。
6. **数据不足时不要硬跑。** 脚本返回 `status: insufficient_data` 并给出原因，此时按提示调低 `--min-valid` / `--window`，或换更粗的 `--key-level`。

## 已知实测结论（不要重新发明）

- `K=14` 优于 `K=7`；**允许 lag 缺口**远优于强制连续（强制连续会丢掉大量样本，因为窗口零点击时 cr 是 NaN）
- 加入成交量 / 星期 / 匹配类型等上下文特征会**变差**，所以默认 `--features lags`
- 最强的特征永远是 `cr_lag1`（置换重要性约为第二名的 7 倍），其余几乎不贡献
- 换聚合粒度会改变结论：campaign 级模型可能输给 persistence，脚本会自动退回

## 反模式

- **不要**把报表里的 `7 Day Conversion Rate` 列直接当成滚动转化率：它是日频归因比值（校验过等于 orders/clicks），不是 7 天窗口比率。滚动窗口必须按 `sum(订单)/sum(点击)` 自己重算。
- **不要**对缺失日期做插值或跳过：缺行 = 当天无投放 = 0 点击 0 订单，必须补 0 才能对齐日历。
- **不要**用随机切分做验证；必须按时间切分。
- **不要**为了跑通而把 `--min-valid` 降到 1、2 这类值，那只是把噪声当信号。

## 输出

| 文件 | 内容 |
|---|---|
| `<outdir>/predictions_<level>_w<x>.csv` | 每个序列一行：`cr_last_window`（当前窗口观测值）、`cr_pred_persistence`、`cr_pred_model`、`cr_pred_recommended`、`source`、`low_confidence`、`n_valid_windows`、`clicks_last_window` |
| `<outdir>/summary.json` | 全部诊断：列识别结果、日期范围、窗口统计、覆盖率、样本量、验证指标、Top10、状态 |

`--json` 可让 stdout 直接输出 JSON 摘要，便于程序化读取。

## 交付

把预测 CSV 用 `present` 给用户；同时在回复里给出最小结论集：序列数 + 覆盖率、验证集上模型 vs baseline 的 RMSE 与技能、推荐列来源、低置信度占比、Top-N 预测。如果 `low_confidence` 占比过高，先给出粒度或口径的改进建议，再给数字。
