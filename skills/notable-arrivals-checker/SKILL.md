---
name: 新品徽章检查（Notable Arrivals）
description: "audit amazon new products for new arrival or notable arrival badge readiness using amazon's official badge logic: time-bound new selection, forecasted customer popularity, objective product-quality analysis, comparison with similar popular items, and ongoing customer feedback or engagement signals. use when a seller asks whether a new asin or listing can qualify for notable arrivals, wants a 100-point score, cold-start plan, listing fixes, keyword plan, seller central export analysis, or article-ready case study about amazon new arrival badges."
---

# Notable Arrivals Checker

## Purpose

Evaluate whether an Amazon new product is structurally and behaviorally positioned to receive or benefit from a `New Arrival` or `Notable Arrival` badge.

Base the audit on the official badge logic supplied by the user:

- The badge can show `New Arrival` or `Notable Arrival`.
- It spotlights newly arrived products on Amazon that are predicted to become customer favorites.
- Prediction uses objective analysis of product qualities and popularity of similar existing items.
- The badge is time-bound and automatically removed after the product is no longer considered new.
- Predictions refine over time as customer feedback and engagement come in.
- All selling partners, including third-party sellers, are eligible.

Do not claim guaranteed badge eligibility, exact Amazon thresholds, or a fixed badge duration unless the user provides official marketplace-specific proof. Present outputs as probability, readiness, and optimization priorities.

## Inputs to Accept

Use whatever the user provides:

- ASIN, listing URL, product title, bullets, description, A+ content, images described in text, backend terms, price, coupon, reviews, Q&A, variation info.
- Seller Central or ad exports such as impressions, clicks, CTR, CVR, sessions, unit session percentage, orders, TACOS/ACOS, search term reports, price, coupon history.
- Competitor ASINs, target category, target keywords, marketplace, launch date, buyable date, and current badge status.

If data is missing, run a best-effort audit and mark assumptions clearly. Ask at most one follow-up only when the product category or product itself is unclear.

## Core Model

Think in two stages:

1. **forecast fit:** does the product look like a future customer favorite when compared with similar successful items?
2. **behavior validation:** do early customer signals support that forecast during the new-product time window?

Use this interpretation in reports:

> notable arrivals readiness = similar-popular-item fit + product-quality clarity + early engagement validation within a limited new-product window.

## 100-Point Scorecard

Score out of 100 using four modules.

| Module | Points | What it measures |
|---|---:|---|
| Popular-item structure match | 40 | Whether the product resembles successful similar products in category, offer, attributes, price, and discoverability. |
| Click attraction | 20 | Whether the search-result appearance can earn engagement. |
| Conversion readiness | 20 | Whether the product page can convert early traffic into orders and positive signals. |
| Cold-start momentum | 20 | Whether the product can generate fast, stable, early validation while it is still new. |

### 1. Popular-item structure match, 40 points

| Subfactor | Points | Check |
|---|---:|---|
| Category and competitor alignment | 10 | Product maps clearly to a known demand pool and similar successful items. |
| Product quality and attribute clarity | 10 | Material, size, compatibility, function, bundle contents, and differentiators are explicit. |
| Offer and price fit | 10 | Price, coupon, pack size, and value proposition fit the current category norm. |
| Keyword and browse discoverability | 10 | Title, bullets, backend terms, and browse placement make the product easy to classify and retrieve. |

### 2. Click attraction, 20 points

| Subfactor | Points | Check |
|---|---:|---|
| Main image clarity | 8 | Shopper can identify product type and core value in under 2 seconds. |
| Search-result differentiation | 5 | Product has a visible reason to click versus similar items. |
| Title click value | 4 | Title includes core category, key spec, and main benefit without looking stuffed. |
| Price or coupon trigger | 3 | Offer reduces new-product risk and improves click motivation. |

### 3. Conversion readiness, 20 points

| Subfactor | Points | Check |
|---|---:|---|
| Trust proof | 5 | Reviews, ratings, brand story, warranty, certifications, or risk reversal reduce buyer hesitation. |
| Detail-page completeness | 5 | Images, bullets, A+ content, and description answer major objections. |
| Benefit clarity | 5 | Copy connects features to customer outcomes and use cases. |
| Friction removal | 5 | Compatibility, dimensions, contents, exclusions, shipping, returns, and variants are clear. |

### 4. Cold-start momentum, 20 points

| Subfactor | Points | Check |
|---|---:|---|
| Early traffic quality | 5 | Early impressions and clicks come from relevant keywords or placements. |
| Early conversion signal | 5 | Clicks turn into orders at a rate that is competitive for the category. |
| Engagement trend | 5 | CTR, CVR, sessions, carts, or orders improve or remain stable over the launch window. |
| Campaign and optimization speed | 5 | Seller adjusts ads, images, price, and keywords quickly based on early data. |

## Grade Bands

| Score | Label | Meaning |
|---:|---|---|
| 80-100 | strong readiness | High readiness. Focus on defending momentum and improving conversion proof. |
| 65-79 | possible with fixes | The product has a plausible path but needs focused improvements. |
| 50-64 | weak or unstable | Some fundamentals exist, but badge readiness is fragile. |
| 0-49 | unlikely | Product is not positioned like a likely customer favorite yet. |

## Required Audit Workflow

1. **Identify the product mission**
   - State product category, buyer segment, primary job-to-be-done, price tier, main competitors or substitute categories, and likely objections.

2. **Map similar-product fit**
   - Compare the product to what similar popular items usually win on: function, specs, price, image promise, reviews, brand trust, bundle, use case, and keyword path.
   - If actual competitor data is missing, label the comparison as an assumption and use category logic.

3. **Score the product**
   - Use the 100-point scorecard. Give subfactor scores, not just the total.
   - Explain every low score in seller-friendly language.

4. **Diagnose the time-window risk**
   - State whether the product is still in the new-product window if launch or buyable date is provided.
   - If date is missing, do not guess. Say the time-window risk cannot be determined.

5. **Prioritize fixes**
   - Separate fixes into: before launch, first 7 days, first 30 days, and ongoing optimization.
   - Tie each fix to either forecast fit or behavior validation.

6. **Create the seller action plan**
   - Give concrete listing, offer, ad, and data-monitoring actions.
   - For ads, separate broad discovery, exact core keywords, competitor/substitute research, and retargeting when relevant.

## Output Format

Use this structure unless the user asks for a different format:

```markdown
# Notable Arrivals Readiness Audit: [product]

## Executive summary
[3-5 bullets with total score, readiness label, biggest strength, biggest weakness, and next move]

## Official-badge logic applied
[Explain how the product maps to: newness, objective product qualities, similar-item popularity, and customer feedback/engagement.]

## Product mission
[Category, buyer, use case, offer position, competitors/substitutes, objections]

## 100-point scorecard
| Module | Score | Max | Reason | Main fix |
|---|---:|---:|---|---|

## Subfactor diagnosis
| Subfactor | Score | Max | Diagnosis |
|---|---:|---:|---|

## Notable Arrivals probability read
[Use qualitative wording: strong readiness / possible with fixes / weak or unstable / unlikely. Do not guarantee badge outcome.]

## Time-window risk
[State launch/buyable date if provided, whether urgency is high, and what must be done now.]

## Listing and offer fixes
### Title
### Main image
### Secondary images
### Bullets
### A+ / description
### Price / coupon
### Variations
### Reviews / Q&A

## Keyword and ad structure
### Core category terms
### Specification terms
### Use-case terms
### Substitute/comparison terms
### Irrelevant traffic to filter

## 7-day action plan
[Day-by-day or phase-by-phase steps]

## 30-day optimization plan
[What to monitor and how to adjust]
```

## Suggested Data Benchmarks

Use these only as directional seller heuristics, not as official Amazon thresholds:

- CTR below category norm usually indicates image, title, price, or search-result mismatch.
- CVR below category norm usually indicates trust, offer, detail-page, review, or traffic-quality problems.
- Strong early order growth matters more than one isolated sales spike.
- A coupon can reduce new-product friction but cannot compensate for unclear product fit.

If the user provides category averages, use those instead of generic benchmarks.

## Article or Marketing Use

When the user asks for an article, case study, lead magnet, or seller-facing content:

- Explain the official mechanism in plain Chinese when the conversation is Chinese.
- Avoid overclaiming that sellers can force the badge.
- Use the phrase: `先看你像不像爆款，再看你能不能跑出爆款数据。`
- Include the 100-point model as the practical takeaway.
- Add a sample audit case when useful.

## Safety and Compliance Rules

- Do not suggest fake orders, fake reviews, review manipulation, rebate abuse, or deceptive traffic.
- Do not recommend trademark misuse or disparaging competitor claims.
- For competitor brand terms, recommend compliant research, category comparison, and legal/ad-policy review when needed.
- Preserve only truthful product claims. Mark claims that require evidence, such as certifications, lab results, waterproof ratings, or medical claims.
- Always state uncertainty when Amazon has not disclosed exact ranking or badge thresholds.
