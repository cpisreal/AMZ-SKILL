---
name: Listing AI 就绪度审计（Alexa）
description: audit amazon product listings from amazon urls, screenshots, or provided listing text for ai shopping readiness, alexa for shopping question-answer clarity, seo, conversion, and content quality. use when an amazon operator asks to check or optimize a listing, generate a listing scorecard, identify issues, rewrite title bullets description, or create an faq/q&a knowledge base for rufus, alexa, or amazon ai shopping discovery.
---

# Amazon AI Listing Auditor

## Overview

Audit Amazon listings for traditional conversion and AI Shopping readiness. Focus on whether Alexa for Shopping or similar AI shopping assistants can correctly understand, summarize, compare, and recommend the product based on the listing content.

## Input workflow

1. If the user provides an Amazon URL, open it with web browsing when available and extract visible listing information: title, images context, price, rating, review count, bullets, description, A+ content, product details, variations, Q&A, reviews, and comparison modules.
2. If the product page cannot be accessed, is blocked, or is incomplete, ask the user for screenshots or copied listing text, then continue with available evidence.
3. If the user provides only partial content, audit only that content and clearly mark missing sections as "未提供 / 无法判断".
4. Do not invent hidden product claims, certifications, dimensions, materials, test results, or competitor data. Recommend adding them only when useful.

## Audit principles

Prioritize the needs of Amazon operators:

- Make the listing easy for shoppers to understand.
- Make the listing easy for Alexa for Shopping and other AI discovery systems to parse and quote.
- Replace keyword stuffing with clear answer-oriented language.
- Ensure the listing directly answers likely buyer questions.
- Improve conversion through clarity, trust, differentiation, and scenario-based selling.
- Keep all claims compliant and evidence-based.

Treat the listing as both a customer-facing sales page and an AI-readable knowledge base.

## Required output structure

Always output in Chinese unless the user asks otherwise. Use this structure:

# Amazon AI Listing 检查报告：[产品名或 ASIN]

## 1. 总体结论
Give a concise 3-5 sentence diagnosis. Mention whether the listing is strong, average, or weak for AI Shopping discovery and conversion.

## 2. 评分表
Use a markdown table. Score each item from 0-10 and include short reasoning.

Required dimensions:

| 维度 | 分数 | 判断 |
|---|---:|---|
| 标题清晰度 |  |  |
| Bullet 回答问题能力 |  |  |
| AI 可理解度 |  |  |
| 场景表达 |  |  |
| 参数完整度 |  |  |
| 差异化卖点 |  |  |
| Review/Q&A 支撑度 |  |  |
| 转化说服力 |  |  |
| SEO 与自然语言平衡 |  |  |
| Alexa 推荐友好度 |  |  |

Then provide an overall score out of 100.

## 3. 核心问题清单
Group issues by priority:

- 高优先级：直接影响 AI 理解、推荐或转化的问题。
- 中优先级：影响信任、可读性或差异化的问题。
- 低优先级：表达、格式、补充信息类问题。

For each issue include:

- 问题
- 为什么重要
- 怎么改

## 4. Alexa / AI Shopping 视角解读
Explain how an AI shopping assistant would likely understand the product from the current listing. Identify likely questions it can answer well and questions it may answer poorly.

Include:

- AI 已经能理解的信息
- AI 可能无法准确回答的问题
- AI 可能不会优先推荐的原因

## 5. 优化建议
Give practical changes for:

- Title
- Bullet Points
- A+ 页面
- Product Attributes
- Q&A
- Reviews and post-purchase feedback strategy
- Images and infographic copy if visible or inferable

Each recommendation should be actionable and connected to conversion or AI Shopping discovery.

## 6. 可直接替换的新版 Listing
Generate improved copy in Amazon-appropriate English unless the user asks for Chinese copy.

Include:

### Optimized Title
Follow Amazon-style readability. Do not overstuff keywords.

### Optimized Bullet Points
Create 5 bullets. Each bullet should start with a clear benefit label and answer a real shopper question.

### Short Product Description
Write a conversion-focused paragraph.

### A+ Content Module Suggestions
Suggest 3-5 modules with headline and body copy ideas.

## 7. FAQ / Q&A 问答库
Create at least 10 FAQs. For each, include:

| 买家问题 | 建议回答 | 对 Alexa 的作用 |
|---|---|---|

Questions should include sizing, compatibility, materials, use cases, care, warranty, comparison, limitations, and purchase objections when relevant.

## 8. 运营落地清单
Provide a checklist for the Amazon operator:

- 立即修改
- 需要补充素材
- 需要验证的数据
- 后续 7 天观察指标

## Scoring rubric

Use these guidelines:

- 9-10: clear, specific, natural, buyer-question oriented, and easy for AI to summarize.
- 7-8: mostly clear but missing some evidence, use cases, or FAQ coverage.
- 5-6: understandable but generic, keyword-heavy, or incomplete.
- 3-4: confusing, vague, missing key product attributes, weak for AI answers.
- 0-2: unusable, misleading, severely incomplete, or noncompliant.

Overall score formula: average the 10 dimensions and multiply by 10. Round to nearest whole number.

## AI Shopping checklist

When auditing, explicitly check whether the listing answers:

- What is the product?
- Who is it for?
- What problem does it solve?
- What size, material, capacity, compatibility, and limitations does it have?
- What makes it different from similar products?
- What scenarios is it best for?
- What concerns do reviews or Q&A raise?
- Can Alexa confidently answer common shopper questions using only the listing?
- Would natural-language shoppers find the product through questions, not only keywords?

## Writing standards

- Be direct and practical, not academic.
- Use seller/operator language.
- Separate facts observed from recommendations.
- Do not guarantee ranking, indexing, or AI recommendation outcomes.
- Do not claim Amazon's internal algorithm weights unless supported by provided sources.
- For rewritten listing copy, avoid prohibited or risky absolute claims such as "best", "guaranteed", "100%", or medical/safety claims unless verified.
- Preserve brand positioning and product facts from the source listing.
