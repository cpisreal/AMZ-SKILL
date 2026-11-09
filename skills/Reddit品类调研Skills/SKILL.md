---
name: Reddit 品类调研
description: "given one product category keyword (e.g. cat food, air fryer, electric toothbrush), pull real consumer discussions from public reddit archives, then auto-compute community distribution, comment long-tail and word-frequency signals and produce a white-background chart set plus a data report. use when an amazon seller wants to mine unfiltered user pain points and opportunities, discover what customers actually complain about, or build category insights from reddit + duckduckgo public search. runs locally via python run.py; offline demo mode needs no key, live mode needs a proxy you provide."
---

# Reddit 品类调研

把「一个品类词 → 消费者原话 → 痛点和机会」这套调研从手工扒帖变成一条命令。
给一个品类词，去 Reddit 公开归档拉真实讨论，自动统计社区分布、评论长尾、词频信号，出白底图表 + 数据报告。

## Quick start（不联网、不需要 key）

```bash
pip install -r requirements.txt
python run.py demo        # 用随包示例数据（250 帖 / 1,785 评论 / 81 万字）跑完整链路
```

## 用自己的品类跑（要联网）

```bash
export HTTPS_PROXY=http://127.0.0.1:你的端口   # 本工具不内置代理，请用你自己的
export HTTP_PROXY=http://127.0.0.1:你的端口
python run.py "cat food" --subreddits catfood,CatAdvice,cats,AskVet
```

| 参数 | 说明 | 默认 |
|---|---|---|
| `关键词` | 品类词（英文） | 必填 |
| `--subreddits` | 逗号分隔相关社区 | `BuyItForLife,Frugal,AskReddit` |
| `--limit` | 每社区每查询帖子数 | 15 |
| `--queries` | 行业侧搜索角度数 | 5 |
| `--out` | 输出目录 | `./output` |

产出 `output/`：`data.json`（原始数据，可再喂 LLM 提炼）/ `stats.json` / `report.md` / `charts/`（5 张白底图）。

## 关键口径（详见 README.md）

- 检索矩阵：社区 × 关键词要多切面，覆盖成分/健康/品牌/安全/生命周期，别只搜宽泛词。
- 结果数量自检：采集结束主动检查帖子数，0 帖直接告警，防止「静默失败」误判「没人讨论」。
- 入库按帖子 id 去重，否则统计虚高。
- 诚实标注边界：词频=讨论热度，不等于市场规模/发病率；样本偏活跃用户，非全体消费者。

## 隐私与合规

- 不含任何个人信息、绝对路径、代理端口或 key；代理/路径/社区全由使用者自配。
- 数据来源：Reddit 公开归档 + DuckDuckGo 零注册搜索，不登录、不采集账号信息。
- 商业用途请自行确认 Reddit 数据授权条款；对外只发布聚合洞察，不搬运原文。

依赖：`ddgs`、`matplotlib`、`numpy`、`Pillow`。完整说明见同目录 `README.md`。
