---
name: Rufus 友好度审计
description: audit and improve amazon marketplace listing pages for rufus-style ai shopping retrieval. use when reviewing amazon product detail pages, listings, titles, bullets, attributes, images, a+ content, reviews, q&a, variation structure, inventory readiness, launch hygiene, or ai-shopping discoverability. produces intent-aware checks, scoring, issue diagnosis, and seller action plans grounded in retrieval-first, query-planner, placeholder, streaming, and metadata-injection principles from amazon's generative ai product-page patent patterns.
---

# Listing Rufus Auditor

Use this skill to evaluate an Amazon listing as an AI-ready data object, not just as sales copy. The goal is to make the page easier for shopping assistants to retrieve, verify, cite, and stream into answers.

## Inputs to request or infer

Accept any of these inputs:
- ASIN or product URL, if the user wants external research.
- Listing text copied by the user: title, bullets, description, A+ content, attributes, images, reviews, Q&A, variation details.
- Product category and target shopper, if the listing itself is incomplete.
- Seller goal: launch readiness, conversion improvement, Rufus/GEO optimization, keyword review, or full audit.

If key fields are missing, still produce a partial audit and mark missing fields as `not provided` instead of inventing details.

## Core audit lens

Evaluate every listing through five mechanisms:

1. **Query planner fit**: Can common shopper questions be classified and routed to the right evidence? Cover item seeking, comparison, compatibility, review/quality, installation/use, gifting, replacement/accessory, and troubleshooting intents.
2. **Retrieval grounding**: Are product claims backed by structured catalog data, reviews, Q&A, images, or A+ modules?
3. **Placeholder readiness**: Can title, image, rating, price, specs, dimensions, compatibility, and identifiers be safely inserted as factual metadata without ambiguity?
4. **Streaming priority**: Are the title and first bullets front-loaded with the most important differentiators, so early streamed answers are useful?
5. **Freshness and eligibility**: Are inventory, variation structure, taxonomy, launch data, and identifiers clean enough for real-time retrieval?

## Audit workflow

1. **Map the listing data**
   - Identify provided and missing assets: title, bullets, attributes, images, A+, reviews, Q&A, variations, inventory notes.
   - Extract explicit facts, claims, use cases, specs, compatibility signals, and differentiators.

2. **Build an intent map**
   - List 8-15 likely shopper queries for the product.
   - Assign each query to an intent type.
   - Identify which listing element should answer it: title, bullet, attribute, image, A+, review, Q&A, or variation metadata.

3. **Score the listing**
   Use a 100-point score:
   - Title retrieval clarity: 10
   - Bullet structure and front-loading: 15
   - Structured attributes and specs: 15
   - Review evidence readiness: 10
   - Q&A coverage: 10
   - Image evidence and visual clarity: 10
   - A+ modular answer design: 10
   - Variation, ASIN, taxonomy, and identifiers: 10
   - Inventory and launch hygiene: 5
   - Cross-content consistency: 5

4. **Diagnose risks**
   Highlight risks in these categories:
   - hallucination risk: claims not backed by retrievable evidence
   - retrieval miss risk: important terms absent or only implied
   - intent gap: common questions not answered anywhere
   - ambiguity risk: vague specs, inconsistent units, unclear compatibility
   - streaming weakness: primary value appears too late
   - variation risk: parent-child or option structure confuses retrieval

5. **Create an action plan**
   Provide prioritized recommendations:
   - P0: fixes that block retrieval or create factual ambiguity
   - P1: high-impact content improvements
   - P2: conversion and merchandising enhancements

## Output format

Use this structure unless the user asks for a shorter result:

```markdown
# Amazon Listing AI-Readiness Audit

## Executive verdict
[2-4 sentence summary with total score and main issue]

## Scorecard
| Area | Score | Why it matters | Main fix |
|---|---:|---|---|

## Query intent map
| Shopper query | Intent | Best evidence source | Current coverage | Fix |
|---|---|---|---|---|

## Priority fixes
### P0 - Retrieval blockers
### P1 - High-impact improvements
### P2 - Nice-to-have enhancements

## Listing rewrite recommendations
### Title
[recommended title formula or rewritten title]

### Bullets
[5 rewritten bullets or bullet formulas]

### Attributes to add or normalize
[fields]

### Q&A to seed
[questions and model answers]

### Image/A+ module plan
[recommended modules]

## Final checklist
[concise checklist]
```

## Title rules

Recommend titles that prioritize:
`Brand + product type + primary use case + key spec/compatibility + main differentiator + size/count/model`

Avoid:
- empty adjectives without proof: premium, best, amazing, high quality
- keyword stuffing that breaks readability
- claims not supported elsewhere on page

## Bullet rules

Write bullets as atomic evidence blocks. Each bullet should answer one retrieval path:
1. who/what it is for
2. core measurable specs
3. compatibility or fit
4. usage/installation/performance proof
5. package, warranty, care, or objection handling

Each bullet should contain at least one retrievable fact: material, size, model, ingredient, certification, compatibility, count, use case, or measurable benefit.

## Q&A rules

Seed Q&A around questions shopping assistants are likely to retrieve:
- Does it fit/work with [model, device, body type, use case]?
- What is included?
- How do I install/use/clean it?
- What size should I choose?
- Is it safe for [user group]?
- How long does it last?
- How is this different from [alternative]?

Answers must be direct, factual, and avoid unsupported marketing claims.

## Image and A+ rules

Recommend visual modules that act as evidence:
- dimensions and scale
- compatibility chart
- installation or use steps
- material/certification proof
- package contents
- comparison table
- use-case scene
- objection-handling FAQ

A+ should be modular: each section must make sense independently because AI interfaces may stream or extract sections out of order.

## Review guidance

Never fabricate reviews. Recommend ethical prompts that encourage buyers to mention real experience, such as fit, installation, compatibility, comfort, durability, scent, packaging, or solved problem. Do not suggest incentivized, fake, or manipulated reviews.

## Evidence standard

When a claim is not explicitly present in the listing data, label it as `needs evidence` and suggest where to add proof: attribute, image, Q&A, A+, or documentation.

## Response style

Be practical and seller-facing. Use direct recommendations, examples, and rewrite snippets. Avoid over-explaining patent theory unless the user asks.
