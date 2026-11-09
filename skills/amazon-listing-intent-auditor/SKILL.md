---
name: Listing 搜索意图审计（A9）
description: audit and improve amazon marketplace listing pages through intent-aware search path analysis. use when reviewing amazon listings, product detail pages, seo copy, titles, bullet points, backend keywords, a+ content, images, variation strategy, cross-sell opportunities, or advertising keyword structure using six query intent types: specification, generalization, equivalence, substitution, complement, and irrelevant. useful for sellers who want a checklist, scoring report, optimization roadmap, or search path map for a product listing.
---

# Amazon Listing Intent Auditor

## Purpose

Use this skill to audit an Amazon product listing page through a two-layer lens:

1. **keyword retrieval:** whether the listing can be found for the right terms.
2. **intent path prediction:** whether the listing is positioned for likely next searches as shoppers narrow, broaden, compare, lock onto a product, buy, or move to accessories.

Do not treat keyword density as the main goal. Evaluate whether the listing captures a shopper's movement across the six intent types.

## Required inputs

Use whatever the user provides. Common inputs include:

- product category and marketplace
- product title, bullets, description, A+ modules, backend search terms, images, variations, reviews, price, coupon, and competitor ASINs
- a listing URL or pasted listing copy
- target customer, price tier, primary competitors, and known search terms

If important inputs are missing, still produce a best-effort audit and label assumptions clearly. Ask only one concise follow-up question when the product itself is unclear.

## Core taxonomy

Classify listing opportunities by six query transition intents:

1. **Specification:** shopper adds modifiers, attributes, use cases, brand, size, material, color, demographic, compatibility, or price ceiling.
2. **Generalization:** shopper removes modifiers or broadens after poor results, limited selection, high price, or uncertainty.
3. **Equivalence:** shopper searches exact brand, product line, model, SKU, generation, size variant, or known item phrase.
4. **Substitution:** shopper swaps brand, material, feature, price tier, or product type to compare alternatives.
5. **Complement:** shopper searches accessories, bundles, refills, add-ons, replacement parts, companion products, or post-purchase needs.
6. **Irrelevant:** shopper leaves the mission or the listing attracts mismatched traffic that bounces or confuses the recommendation context.

## Audit workflow

### 1. Identify the product mission

Summarize:

- core product category
- primary job-to-be-done
- likely buyer segment
- price/quality position
- main purchase objections
- likely primary competitors or substitute categories

### 2. Build a search path map

Create 2-4 likely shopper paths. Include at least:

- **normal purchase path:** broad term -> specification -> known item or purchase
- **comparison path:** specification -> substitution -> equivalence
- **post-purchase path:** primary product -> complement chain

Use arrows and label every transition with intent type.

Example format:

```text
broad category
  -> attribute/use-case modifier [specification]
  -> brand/model/variant [equivalence]
  -> accessory/refill/add-on [complement]
```

### 3. Score listing coverage

Use a 0-5 score for each dimension:

- **generalization capture:** core category terms, simple category language, broad relevance.
- **specification depth:** long-tail attributes, use cases, compatibility, material, size, demographic, problem/benefit specificity.
- **equivalence capture:** exact model/name/SKU/variant naming, memorable product naming, consistent title-image-bullets identity.
- **substitution defense/offense:** comparison positioning, alternative phrases, competitor-safe differentiation, price/value framing.
- **complement capture:** accessories, bundles, replacement parts, “works with / for / pairs with” language, post-purchase cross-sell path.
- **irrelevant filtering:** immediate clarity about what the product is and is not, compatibility boundaries, size limits, use-case exclusions.
- **conversion friction:** proof, reviews, price, coupon, images, FAQs, risk reversal, trust claims, contradiction removal.

Scoring scale:

- 0 = absent or actively harmful
- 1 = very weak
- 2 = partial but unclear
- 3 = acceptable baseline
- 4 = strong
- 5 = excellent / category-leading

### 4. Inspect page elements

Check each element against the intent map:

- **Title:** must include core category + primary differentiator + highest-value specification. Avoid stuffing that hurts clarity.
- **Main image:** must confirm category and core value in under 2 seconds.
- **Secondary images:** should answer specification objections, compatibility, dimensions, use cases, before/after, bundle contents, and trust proof.
- **Bullets:** first bullet clarifies product mission and filters mismatch; middle bullets deepen specification; final bullet supports complement or risk reversal.
- **Description / A+ content:** should include modules for quick relevance confirmation, feature/spec proof, comparison positioning, and complement ecosystem.
- **Backend keywords:** should allocate roughly 60% specification, 15% generalization, 15% equivalence/substitution, 10% complement unless category data suggests otherwise.
- **Variations:** should reflect real shopper specification branches such as size, color, quantity, material, or compatibility.
- **Reviews / Q&A:** mine language for missing specification terms, objections, compatibility issues, and substitute comparisons.
- **Ads / keyword campaigns:** separate campaigns by intent type instead of mixing all terms.

### 5. Detect intent dynamics

Flag these high-value patterns when relevant:

- **saturation cliff risk:** if the listing requires too many specification steps before convincing the shopper, recommend stronger proof or comparison content before users switch brands.
- **post-purchase inversion opportunity:** if the product has accessories, refills, or companion products, recommend complement keywords, bundles, and cross-sell modules.
- **session reset risk:** if page copy attracts the wrong customer or has vague compatibility, recommend clearer exclusions and stronger first-screen relevance.
- **substitution window:** if competitors dominate branded or feature terms, recommend defensible non-disparaging comparison language.

## Output format

Use this structure unless the user requests another format:

```markdown
# Amazon Listing Intent Audit: [product]

## Executive summary
[3-5 bullets: biggest opportunities and risks]

## Search path map
[2-4 paths using arrows and intent labels]

## Scorecard
| Dimension | Score | Why it matters | Main fix |
|---|---:|---|---|

## Page-level findings
### Title
### Images
### Bullets
### A+ / Description
### Backend keywords
### Variations
### Reviews / Q&A
### Ads keyword structure

## Priority fixes
1. [highest impact action]
2. [second action]
3. [third action]

## Keyword and content recommendations
### Generalization terms
### Specification terms
### Equivalence terms
### Substitution terms
### Complement terms
### Irrelevant-filtering phrases

## 7-day action plan
[concrete steps the seller can implement immediately]
```

## Quality rules

- Be specific to the product; avoid generic SEO advice.
- Distinguish facts from assumptions when full listing data is not available.
- Do not recommend trademark misuse, false claims, review manipulation, or deceptive competitor comparisons.
- For competitor brand terms, recommend compliant research, non-disparaging comparison positioning, and ad/legal review where needed.
- Prefer concise, actionable rewrites over abstract advice.
- When rewriting listing copy, preserve truthful claims only and mark claims that require evidence.

## Optional reference

For a compact checklist and keyword allocation guide, consult `references/checklist.md`.
