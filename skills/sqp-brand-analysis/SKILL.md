---
name: SQP 品牌搜索分析
description: Generates a full Amazon SQP (Search Query Performance) brand analysis from weekly CSV exports. Produces CSV files, a PNG trend chart, and a complete Markdown report with all data tables embedded. Use when the user provides Amazon SQP CSV files, asks for brand search-term analysis, week-over-week comparison, high-conversion term detection, or trend charts across weeks.
---

# SQP Brand Analysis

Run `sqp_report.py` to generate all outputs from Amazon SQP Brand View weekly CSV exports (≥ 2 weeks required for WoW sections).

## Requirements

```bash
pip install pandas matplotlib
```

## Running the Script

```bash
python ~/.cursor/skills/sqp-brand-analysis/scripts/sqp_report.py \
  --input "path/to/SQP/*.csv" \
  --output "./sqp_output/"
```

**`--input`** accepts any combination of:
- Glob pattern: `"Marketing Projects/SQP - Analysis/*.csv"`
- Directory:    `"Marketing Projects/SQP - Analysis/"`
- Space-separated files: `wk1.csv wk2.csv wk3.csv`

**`--output`** defaults to `./sqp_output/` (created automatically).

## Input File Requirements

- Filename must match: `..._Week_YYYY_MM_DD.csv` (standard Amazon export name)
- First row is Amazon metadata — automatically skipped
- Minimum **2 weeks** for WoW comparison; 1-week runs still produce portfolio + high-conv outputs

## Outputs

| File | Description |
|------|-------------|
| `sqp_report.md` | Full text report — all data tables embedded as Markdown |
| `weekly_brand_portfolio.csv` | Per-week, per-term: brand counts + 4 brand-share-of-week-total % |
| `high_conv_terms.csv` | Terms where `Purchase Rate % / Brand Impression Share % ≥ 1` |
| `wow_new_dropped.csv` | New / dropped terms for each consecutive week pair |
| `wow_self_drops.csv` | Top 10 biggest brand decreases per metric per week pair |
| `wow_market_deviation.csv` | Top 10 brand-vs-market deviations per metric + direction judgment |
| `top5_stable_terms.csv` | Top 5 high-freq & high-brand-share terms — weekly detail |
| `sqp_top5_trend.png` | Trend chart: market impressions (bar) + brand share % (line) |

## Report Sections (sqp_report.md)

1. **每周品牌数据快照** — Brand totals + Top 25 terms sorted by brand impressions
2. **转化能力高于类目的词** — High-conversion terms per week
3. **WoW 新入列 & 跌出列** — Terms appearing / disappearing between weeks
4. **和自己比** — Top 10 biggest brand drops per metric (impressions / clicks / cart adds / purchases)
5. **和大盘比** — Top 10 terms where brand change deviates most from market; includes direction judgment
6. **Top 5 稳定高价值词** — Most consistent high-brand-share terms across all weeks + weekly detail table

## Key Metric Definitions

| Column | Formula |
|--------|---------|
| `pct_brand_imp/clk/cart/pur` | Term's brand count ÷ week's brand total × 100% |
| `conv_ratio` | `Purchases: Purchase Rate %` ÷ `Impressions: Brand Share %` (≥ 1 = high potential) |
| `相对变化比` | Brand WoW rate ÷ Market WoW rate |

## Direction Judgment Labels (`判断` column)

| Label | Meaning |
|-------|---------|
| `↑↑ 比大盘涨得快` | Brand grew > 1.5× market rate |
| `↑ 与大盘同步上涨` | Brand and market grew similarly |
| `↑↓ 比大盘涨得慢` | Brand grew but slower than market |
| `↓↓ 比大盘跌得快` | Brand fell > 1.5× market decline |
| `↓ 与大盘同步下跌` | Brand and market fell similarly |
| `↓↑ 比大盘跌得慢` | Brand fell but less than market |
| `⚡ 逆势上涨` | Market fell, brand rose |
| `⚠ 逆势下跌` | Market rose, brand fell |

## Workflow

1. Ask the user for the SQP CSV file location
2. Run the script (command above)
3. Present `sqp_report.md` as the primary text report
4. Show `sqp_top5_trend.png` for visual trend review
5. Mention the 6 CSVs are available for further analysis
