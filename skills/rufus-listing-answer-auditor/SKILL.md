---
name: Rufus 答案框架审计
description: "audit and improve amazon listing pages using a patent-aligned rufus answer-recommendation framework. use when reviewing amazon titles, bullets, descriptions, a+ content, q&a, image copy, backend keywords, advertising keyword groups, or competitor positioning for sellers who want a rufus-ready diagnosis. focus on the chain: shopper question, generated or associated answer, noun phrases and n-grams, semantic ranking, product association, and click-training feedback. produce practical listing rewrites while clearly distinguishing patent-supported mechanisms from seller-side inferences."
---

# Rufus Listing Answer Auditor

## Purpose

Use this skill to audit and rewrite Amazon listing content through a patent-aligned Rufus lens. The core diagnosis is not keyword density. The core diagnosis is whether the listing provides clear, truthful product information that can support answer generation and expose useful noun phrases or n-grams for semantic product association.

## Patent-aligned operating model

When analyzing a listing, follow this interpretation:

```text
shopper question
  -> associated or generated answer
  -> extracted n-grams / noun phrases from the answer
  -> semantic scoring and ranking
  -> product search / product association
  -> click feedback can improve training over time
```

Be precise:

- Do not claim Rufus directly extracts all recommendation terms from a listing unless the user provided evidence. Say listing content can influence or supply answerable product information.
- Do not claim Rufus uses every Amazon page module in the same way. Say titles, bullets, descriptions, A+, Q&A, reviews, and image copy can help make product information clearer and more answer-ready.
- Do not recommend keyword stuffing, fake claims, review manipulation, competitor disparagement, trademark misuse, or unsupported performance claims.
- Mark any claim that requires proof, certification, lab test, or product documentation.

## Required inputs

Use whatever the user provides. Common inputs include:

- Amazon listing URL or pasted copy
- product category and marketplace
- title, bullets, description, A+ content, backend terms, image copy, reviews, Q&A
- target keywords, core selling points, buyer persona, competitor ASINs

If the data is incomplete, perform a best-effort audit and label assumptions. Ask only one concise follow-up question when the actual product is unclear.

## Audit workflow

### 1. Identify the product mission

Summarize:

- core category
- primary job-to-be-done
- target buyer and use case
- main purchase objections
- major substitutes or comparison paths
- claims that need evidence

### 2. Build the shopper question map

Create likely natural-language questions grouped by intent:

- use case: "is this good for camping?"
- problem: "how do I keep food cold without ice?"
- compatibility: "does it work in an RV or truck?"
- performance: "can it freeze food?"
- risk or objection: "is it easy to move when full?"
- comparison: "is it better than a regular cooler?"
- complement: "what accessories or power options does it need?"

### 3. Convert questions into answer-ready content needs

For each question, identify:

- direct answer the listing should support
- high-value noun phrases or n-grams likely to appear in the answer
- page module that should carry the answer: title, bullet, description, Q&A, image, A+, backend keyword, or ad group

### 4. Score answer-readiness

Score each dimension from 0 to 5:

- **question coverage:** how well the page anticipates real shopper questions.
- **answer clarity:** whether answers are direct, truthful, and easy to quote or summarize.
- **noun phrase quality:** whether phrases combine category, attribute, use case, compatibility, and benefit.
- **semantic bridge strength:** whether features are connected to outcomes and use cases.
- **product association clarity:** whether the product identity and category are unmistakable.
- **click-path fit:** whether copy aligns with likely user refinement and click behavior.
- **irrelevant traffic filtering:** whether the page clarifies boundaries, limitations, compatibility, and non-use cases.
- **conversion trust:** whether claims are supported by proof, visuals, reviews, specs, warranty, or risk reversal.

Scoring scale:

- 0 = absent or harmful
- 1 = very weak
- 2 = partial but unclear
- 3 = acceptable baseline
- 4 = strong
- 5 = excellent / category-leading

### 5. Inspect listing modules

Evaluate each module with the answer-recommendation chain in mind:

- **Title:** category + high-value specification + use case + differentiator. Avoid stuffing.
- **Bullets:** each bullet should answer a core purchase question.
- **Description/Q&A:** should provide natural-language answers that can expose useful noun phrases.
- **Images:** image copy should clarify use case, compatibility, dimensions, and differentiators.
- **A+ content:** should build a decision path: problem, solution, proof, comparison, use cases, compatibility.
- **Backend keywords:** should support specification, synonym, use-case, substitute, and complement discovery without repeating obvious title terms excessively.
- **Reviews/Q&A:** mine for missing questions, objections, and actual buyer language.
- **Ads:** group by question intent and search path, not only by root keyword.

### 6. Rewrite with patent-aware wording

When rewriting, use this pattern:

- Start with the shopper question.
- Write a direct answer.
- Include noun phrases naturally.
- Connect feature to use case or outcome.
- Preserve truthfulness.
- Mark proof-needed claims.

Example:

```text
Question: How do I keep food cold on a road trip without ice?
Answer-ready phrase: portable electric car fridge keeps food cold without melting ice during long road trips.
Listing use: bullet + image headline + Q&A answer.
```

## Output format

Use this structure unless the user asks for a different format:

```markdown
# Rufus Listing Answer Audit: [product]

## Executive summary
[3-5 concise bullets]

## Product mission
[category, job-to-be-done, buyer, objections, substitutes]

## Shopper question map
| Shopper question | Intent | Answer the listing should support | Useful noun phrases / n-grams |
|---|---|---|---|

## Scorecard
| Dimension | Score | Diagnosis | Main fix |
|---|---:|---|---|

## Module diagnosis
### Title
### Bullets
### Description / Q&A
### Images
### A+ content
### Backend keywords
### Reviews / Q&A mining
### Ads keyword structure

## Rewrite recommendations
### Rufus-ready title
### Rufus-ready bullets
### Q&A description block
### Image copy plan
### A+ module plan
### Backend keyword groups

## Patent-alignment notes
[Clarify what is directly supported by the patent mechanism and what is a seller-side optimization inference.]

## 7-day action plan
[Concrete implementation steps]
```

## Quality rules

- Be concrete and product-specific.
- Prefer rewrites the seller can paste into a listing after legal and compliance review.
- Do not overstate how Rufus works internally. Use "can help", "may support", "is more consistent with", and "seller-side inference" where appropriate.
- Preserve Amazon policy safety: no false medical, safety, durability, certification, or competitor claims.
- For image and A+ suggestions, describe copy and module intent; do not imply visual OCR is the patent's primary extraction mechanism.

## Optional references

For compact rubrics and phrase templates, consult `references/rufus_audit_rubric.md` when needed.
