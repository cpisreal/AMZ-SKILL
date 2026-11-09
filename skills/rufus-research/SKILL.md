---
name: Rufus 品类调研（浏览器自动化）
description: |
  通过 Chrome 浏览器自动化与 Amazon Rufus AI 对话，收集品类用户痛点和需求，生成 Listing 优化 + Rufus GEO 调研报告。

  触发条件：
  - 用户要求"调研 Rufus"、"用 Rufus 分析"、"Rufus + [品类]"、"收集 Rufus 回答"、"调研 [品类] 用户关心什么"
  - 用户提供多个问题要求与 Rufus 对话并出报告
  - 用户要求"帮我设计问题"然后"和 Rufus 聊"
  - 任何需要抓取 Rufus AI 回答的 Amazon 相关调研任务
---

# Rufus Research Skill

通过 Chrome CDP 控制 Amazon Rufus AI，收集品类调研数据并生成 Markdown 报告。

## 核心脚本

```
scripts/
├── rufus-chrome-session.mjs   # Chrome CDP 会话封装（launch/navigate/ask）
└── rufus-research-runner.mjs  # 调研编排器（run 方法即可执行全流程）
```

## 快速使用

```javascript
import { RufusResearchRunner } from './scripts/rufus-research-runner.mjs';

const runner = new RufusResearchRunner({
  topic: 'curtain',
  saveDir: '~/workspace/rufus-curtain-research',
});

const questions = [
  'What are the most important factors when buying curtains for a bedroom?',
  'What is the difference between blackout and sheer curtains?',
  'How do I choose the right size curtains for my window?',
  // ...
];

const results = await runner.run(questions);
```

## 输出文件

运行后在 `saveDir` 下生成：

- `Q1-xxx.md`, `Q2-xxx.md`, ... — 每个问题的详细 Rufus 回复
- `SUMMARY-xxx.md` — 汇总报告（高频追问词 + 竞品品牌统计 + 各问题概要）

## 手动操作流程（参考 references/workflow.md 详述）

1. **启动 Chrome**：`--remote-debugging-port=9222 --remote-allow-origins=*`
2. **获取页面 ID**：`curl -s -X PUT http://127.0.0.1:9222/json/new`
3. **WebSocket 连接**：`ws://127.0.0.1:9222/devtools/page/[PAGE_ID]`
4. **导航**：`Page.navigate` → 等待 5 秒
5. **找到输入框**：DOM 元素 `id="rufus-text-area"`
6. **发送问题**：
   - 写入 `ta.value = question`
   - 触发 `input` 事件
   - 发送 `KeyboardEvent("keydown", bubbles: true, key: "Enter")`
7. **等待回复**：至少 8 秒
8. **抓取内容**：`.nav-rufus-content` panel → 从问题关键词位置截取 5000 字符
9. **解析**：提取 Follow-ups / 品牌 / 价格区间（详见 references/workflow.md）
10. **保存**：本地 .md 文件

## 问题设计框架（10 个维度）

每调研一个新品类，设计 10 个问题覆盖以下维度：

| # | 维度 | 目的 |
|---|------|------|
| 1 | 核心购买因素 | 标题/要点关键词 |
| 2 | 品类基本概念/档次 | 定价/功能分层 |
| 3 | 尺寸选购指南 | 产品变体/描述 |
| 4 | 风格/颜色趋势 | 标题颜色词/风格词 |
| 5 | 类型/规格对比 | 变体标题区分 |
| 6 | 功能价值量化 | 要点功能数据 |
| 7 | 材质/护理 | 材质关键词/描述 |
| 8 | 常见问题 | FAQ 内容素材 |
| 9 | 场景细分 | 多场景关键词 |
| 10 | 配件/互补品 | 捆绑销售提示 |

## 输出格式

每个问题输出：
- **原始回复**：保留完整英文原文
- **Follow-ups**：Rufus 给的追问建议（买家搜索词来源）
- **提及品牌**：竞品分析
- **价格区间**：定价参考

汇总报告包含：
- 高频关键词地图（按出现频率排序）
- Listing 各位置优化模板
- Rufus GEO 发现（Rufus 如何嵌入产品/ASIN）

## 已知限制

- Chrome 必须完全退出后才能用调试端口启动（`pkill -f "Google Chrome"`）
- WebSocket 连接不稳定时，重新 `curl /json/new` 获取新页面 ID
- Rufus 回复等待时间建议 8 秒，过短会漏掉内容
