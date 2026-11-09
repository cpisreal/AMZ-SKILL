---
name: SP 广告投放结构分析
description: >-
  Builds Amazon Sponsored Products targeting structure analysis from Advertised
  Product Report and Targeting Report (Excel). Produces Markdown report, UTF-8
  CSV with per-targeting labels and bid suggestions, and a styled text summary.
  Use when the user provides Sponsored Products Advertised product report.xlsx,
  Sponsored Products Targeting report.xlsx, ASIN_LIST, TARGET_ACOS, or
  AVG_CLICKS_PER_ORDER, or asks for targeting structure / 投放结构 / 核心流量
  protection / 分层标签 reports.
---

# Amazon Targeting 结构分析报告

## 何时使用

用户给出（或拖拽）以下输入时执行本流程：

1. **Advertised Product Report**：Sponsored Products 广告商品报告（`.xlsx`）
2. **Targeting Report**：Sponsored Products 投放报告（`.xlsx`）
3. **ASIN_LIST**：待分析 ASIN，可为单个或多个
4. **TARGET_ACOS**：目标 ACoS，小数形式（如 15% → `0.15`）
5. **AVG_CLICKS_PER_ORDER**：平均出单点击数（总点击 ÷ 总订单）

## 必须执行的步骤

1. **确认路径**：两个 xlsx 在用户工作区中的绝对路径或相对路径；若用户只上传文件，先保存到可写目录并记下路径。
2. **运行脚本**（优先，保证与 Notebook 逻辑一致）：

   ```bash
   python "<skill_dir>/scripts/run_targeting_structure_report.py" \
     --advertised-product "<AP_REPORT.xlsx>" \
     --targeting "<TARGETING_REPORT.xlsx>" \
     --asin <ASIN1> [--asin <ASIN2> ...] \
     --target-acos <0.15> \
     --avg-clicks-per-order <7> \
     --out-dir "<输出目录>"
   ```

   其中 `<skill_dir>` 为技能目录：用户若安装在 `~/.cursor/skills/amazon-targeting-structure-report/`，则使用该路径；若在项目内 `.cursor/skills/...`，则用项目内路径。

3. **依赖**：需要 `pandas`、`numpy`、`openpyxl`。若缺失则 `pip install pandas numpy openpyxl`。

4. **交付物**（向用户说明生成位置）：
   - `report_{首个ASIN}_{YYYY-MM-DD}.md`：完整 Markdown 报告
   - `targeting_labels_{首个ASIN}_{YYYY-MM-DD}.csv`：每行一个 Targeting，含标签与调价建议
   - 终端/Notebook 中的**样式文本报告**（脚本会打印）

5. **多 ASIN**：多个 `--asin`；报告文件名与 MD 主 ASIN 使用列表中的**第一个** ASIN（与 Notebook 中 `DEMO_ASIN` 行为一致）。数据层面会合并所有列出 ASIN 对应的 Campaign/Ad Group。

## 可选参数（脚本）

| 参数 | 默认 | 含义 |
|------|------|------|
| `--analysis-days` | 14 | 分析窗口（天），以 Targeting 报告日期列最大日为结束日向前推 |
| `--core-sales-share` | 0.2 | 销售占比 ≥ 该值视为核心流量，高 ACoS 时建议保护 |

## 报告内容概要（便于口头摘要）

- 账户健康度：整体 ACoS、与目标缺口、日均订单、订单波动 CV、不出单花费占比
- 流量集中度：Top 3/5/10/20 销售占比
- 投放分层：低/高 ACoS 出单、高/低点击不出单、无点击；分层花费与销售
- 核心流量保护名单：出单前 10 的 Targeting
- 高 ACoS 非保护 Top10 及建议调价幅度

## 若无法运行脚本

在用户明确要求且环境无 Python 时，再考虑用项目内 `targeting_structure_report.ipynb` 逻辑手写等价代码；否则**默认跑脚本**。

## 脚本维护

逻辑与 `Marketing Projects/Open Source - Time-Series Bidding System/targeting_structure_report.ipynb` 对齐；列名依赖亚马逊导出模板：`Advertised ASIN`、`Campaign Name`、`Ad Group Name`、`Date`、`Impressions`、`Clicks`、`7 Day Total Orders (#)`、`Spend`、`7 Day Total Sales`、`Targeting`、`Match Type`。
