# targeting-cr-forecast

把一份 **Amazon Ads Sponsored Products targeting report（日维度）** 变成每个 Targeting 在**下一个 x 天滑动窗口**的预估转化率。

这是一个 DeepSeek Harness (DSH) Skill，同时它的核心脚本也是**可直接单独运行的命令行工具**——不安装 Skill 也能用。

---

## 目标定义

```
cr_x(t) = sum(orders, t-x+1 .. t) / sum(clicks, t-x+1 .. t)     # 窗口点击为 0 时未定义(NaN)，不是 0
用 cr_x(t-1) ... cr_x(t-K) 预测 cr_x(t+1)
```

`x` = 滑动窗口天数（`--window`），`K` = 用多少个历史窗口做特征（`--lags`）。两者独立。

---

## 依赖

| 包 | 必需性 | 用途 |
|---|---|---|
| `pandas` `numpy` | 必需 | 全部数据处理 |
| `openpyxl` | 读 xlsx 时必需 | 也支持直接读 csv（无需 openpyxl） |
| `lightgbm` | 推荐 | 主力模型 |
| `scikit-learn` | 推荐 | lightgbm 缺失时降级为 HistGradientBoosting |
| — | — | 两者都没有时自动降级为内置 numpy ridge，仍可运行 |

`prophet` **不需要**（见下方「为什么不用 Prophet」）。

```sh
# 先自检依赖；$HOME 在 macOS 上展开为 /Users/<你的账户>
"$HOME/anaconda3/bin/python" scripts/forecast_cr.py --check-env
```

若该解释器不存在，改用任意 `python3`，但必须先用 `--check-env` 确认 pandas / openpyxl 可用。

---

## 直接使用（不安装 Skill）

```sh
"$HOME/anaconda3/bin/python" scripts/forecast_cr.py \
  "<你的 targeting report>.xlsx" \
  --window 7 --lags 14 --out ./cr_forecast_out
```

输出：

| 文件 | 内容 |
|---|---|
| `cr_forecast_out/predictions_<level>_w<x>.csv` | 每序列一行：`cr_last_window`、`cr_pred_persistence`、`cr_pred_model`、`cr_pred_recommended`、`source`、`low_confidence`、`n_valid_windows`、`clicks_last_window` |
| `cr_forecast_out/summary.json` | 列识别、日期范围、窗口统计、覆盖率、验证指标、Top10、状态 |

### 常用参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `--window` / `-w` | 7 | 滑动窗口天数 x |
| `--lags` / `-k` | 14 | 历史窗口个数 K（实测 14 明显优于 7） |
| `--horizon` | 1 | 向前预测几个窗口；>1 为递归预测，误差累积 |
| `--key-level` | targeting | `targeting` / `adgroup` / `campaign` |
| `--min-valid` | 15 | 序列至少要有多少个可用窗口才建模 |
| `--val-days` | 7 | 验证集天数（时间切分） |
| `--model` | auto | `auto` / `gbdt` / `persistence` |
| `--features` | lags | `lags` / `lags+volume`（后者实测更差） |
| `--min-clicks-flag` | 5 | 低置信度阈值 |
| `--date-col` `--clicks-col` `--orders-col` | 自动 | 列名识别失败时手工指定 |
| `--json` | — | stdout 直接输出 JSON 摘要 |

---

## 安装为 DSH Skill（可选）

Skill 是一个含 `SKILL.md` 的目录。DSH 按以下 rank 顺序扫描 skill 根目录，**只识别根目录顶层的 `<name>/SKILL.md`，不支持嵌套发现**：

| Rank | 作用域 | 路径 |
|---|---|---|
| 100 | 项目（本仓库） | `<项目根>/.dsh/skills` |
| 200 | 项目（agents 约定） | `<项目根>/.agents/skills` |
| 400 | 用户（DSH Beta） | `~/.dsh-beta/skills` |
| 400 | 用户（DSH Stable） | `~/.dsh/skills` |
| 500 | 用户（agents 约定） | `~/.agents/skills` |

`<项目根>` = 最近一个含 `.git` 的祖先目录；没有就是当前工作目录。

用自带的安装脚本：

```sh
./install.sh project     # 装到当前目录的 .dsh/skills
./install.sh user        # 装到 ~/.dsh-beta/skills（跨项目可用；Stable 版请改 ~/.dsh）
```

或手工复制：把整个 `targeting-cr-forecast/` 目录丢进上面任一 `skills/` 下即可。DSH 有文件监视，新增 skill 无需重启，会直接出现在下一次会话目录里。

---

## 为什么不用 Prophet

Prophet 是加性分解模型（趋势 + 周/年季节性 + 节假日 + 高斯噪声），在这个任务上有三个硬伤：

1. **没有自回归项。** 实测最强的特征是上一个窗口 `cr_lag1`（置换重要性约为第二名的 7 倍），Prophet 默认看不到它。
2. **给不出 0。** 目标序列零点击时未定义、有定义时中位数也是 0，Prophet 会输出平滑正数，"大多数日子是 0"这种结构它表达不了。
3. **没有池化能力。** 每条序列要单独 fit；数以百计的短稀疏序列之间无法互相借力。

Prophet 真正合适的场景是**稠密聚合序列**（例如 Portfolio 级：零点击窗口占比低、每个窗口有可观的点击量），或汇总 KPI 且有 ≥2 年历史可估年季节性/节假日。

---

## 诚实的边界（重要）

这个任务**本质接近"抄上一个窗口"**，因为相邻的 x 天窗口重叠 `(x-1)/x` 天：

- persistence 基线（`cr_pred = 上一个窗口值`）的 R² 天然就**很高**。所以**不要用 R² 绝对值**判断效果，要看 `skill_vs_persistence`。
- 脚本会在验证集上比较模型与基线，**模型打不过基线时自动把 `cr_pred_recommended` 退回 persistence**，并在 `source` 列注明用了哪个。
- targeting 级实测中，低置信度占比高是**常态而非例外**——该粒度下大量"转化率"是 1~2 次点击的小分母噪声。若占比过高，建议改 `--key-level campaign`、把 `--window` 调到 14，或改用"未来 x 天是否出单"的分类口径。
- 报表里的 `7 Day Conversion Rate` 列**不是**滚动转化率（它是日频归因比值，校验过等于 orders/clicks）。滚动窗口必须按 `sum(订单)/sum(点击)` 自己重算。
- 缺失日期必须补 0（缺行 = 当天无投放 = 0 点击 0 订单），不要插值或跳过；验证必须按时间切分，不能随机切分。

---

## 实测行为（定性）

在真实样例报表上跑过三种配置，观察到的行为稳定且可复现——**这些结论不依赖任何具体账户数据**：

- **targeting 级 + w=7**：模型在验证集上小幅超过 persistence 基线，`source=model`。
- **targeting 级 + w=14**：同样超过基线，但幅度更小——窗口越长，相邻窗口重叠越多，基线本身越强。
- **campaign 级 + w=7**：模型**输给** persistence，脚本自动把推荐列退回基线，`source=persistence`。

这解释了为什么脚本内置"打不过就退回"的机制：粒度变粗、窗口变长都会抬升基线强度，模型增益随之缩小甚至转负。判断效果请始终看 `skill_vs_persistence`，而不是 R²。
