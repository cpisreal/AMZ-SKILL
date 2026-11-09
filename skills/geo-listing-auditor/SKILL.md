---
name: GEO Listing 优化审计
description: "analyze a rufus answer report against an amazon listing title and bullets, then generate a structured geo and listing optimization report. use when chatgpt is given a rufus response summary, current listing copy, or both, and needs to identify which geo or ai-recommendation points should be present, score the current listing against those points, diagnose missing or weak coverage, and recommend how to improve the listing. best for ecommerce, amazon listing audits, geo readiness reviews, and ai-search optimization reports."
---

# Geo Listing Auditor

Audit a current Amazon listing against a Rufus-derived insight report and produce a practical GEO and listing optimization report.

## Workflow

1. Read the Rufus report carefully and extract the recommendation signals.
2. Read the current listing title and bullets.
3. Convert the Rufus signals into a GEO expectation map.
4. Score the current listing against that map.
5. Explain the largest gaps.
6. Recommend concrete listing improvements.

## Inputs

Expect these inputs when available:
- `rufus_report`: required. A Rufus answer report, summary, transcript, or structured notes.
- `title`: required. Current listing title.
- `bullets`: required. Current five bullets. If fewer than five are provided, audit what exists.
- `category`: optional.
- `brand`: optional.
- `competitor_info`: optional.

If the Rufus report is messy or verbose, summarize it first into stable signals before scoring.

## Core task

Turn the Rufus report into an evidence-based checklist of what the listing should communicate for GEO and AI recommendation readiness.

Always separate three layers:
1. **Expected points**: what the listing should communicate based on Rufus.
2. **Current coverage**: what the title and bullets already communicate.
3. **Gap and recommendation**: what is missing, weak, vague, or poorly positioned.

Do not score based on general ecommerce best practices alone. Anchor the audit primarily in the Rufus report.

## GEO expectation map

Extract and normalize the Rufus report into these six audit dimensions.

### 1. Scenario coverage
Look for use cases, environments, contexts, and jobs-to-be-done that Rufus repeatedly surfaces.

Examples:
- small apartments
- remote work
- beginners
- daily meal prep
- travel

### 2. Audience match
Look for the buyer types or user personas implied by Rufus.

Examples:
- parents
- seniors
- students
- home office workers
- first-time users
- budget-conscious shoppers

### 3. Decision-driver coverage
Identify the factors Rufus treats as important in choosing this product.

Examples:
- size
- comfort
- durability
- setup speed
- noise
- battery life
- ease of cleaning
- price-value tradeoff

### 4. Positioning and differentiation
Identify how Rufus frames the product relative to alternatives.

Examples:
- compact option
- beginner-friendly option
- premium long-term choice
- easy-to-maintain alternative

### 5. User-language and GEO semantics
Identify the natural-language framing Rufus uses or responds to.

Examples:
- “good for small spaces”
- “easy to use for beginners”
- “helps reduce back strain”

Prefer natural buyer language over keyword stuffing.

### 6. AI-readable structure clarity
Assess whether the title and bullets state the right points clearly enough for an AI recommendation system to interpret.

Look for:
- explicitness
- low ambiguity
- concrete benefit statements
- sensible ordering of claims
- strong linkage between feature and outcome

## Scoring method

Use a 100-point system.

Score the six dimensions like this:
- Scenario coverage: 20
- Audience match: 15
- Decision-driver coverage: 20
- Positioning and differentiation: 15
- User-language and GEO semantics: 15
- AI-readable structure clarity: 15

Rules:
- Score only against expectations that are actually supported by the Rufus report.
- Do not give full credit for vague or generic wording.
- Penalize missing high-signal points more than missing minor points.
- If the title or bullets imply a point weakly, award partial credit and explain why.
- If the Rufus report is too thin to support a dimension strongly, say so and use a conservative score.

## Scoring guidance

Use these rough ranges for each dimension:
- **Excellent**: most high-signal points are present, specific, and easy to understand.
- **Adequate**: some important points are present, but coverage is partial, weak, or badly ordered.
- **Weak**: key points are missing, overly generic, or hard for AI or shoppers to infer.

Use [references/scoring-rubric.md](references/scoring-rubric.md) for detailed scoring cues.

## Diagnosis rules

For each weak or partial dimension, explain:
- which Rufus-derived signals matter most
- whether the listing misses them entirely or communicates them weakly
- whether the issue is absence, vagueness, poor ordering, or weak wording

Distinguish between:
- **missing point**: not present at all
- **underdeveloped point**: present but too weak, too generic, or too buried
- **misaligned point**: listing emphasizes things Rufus does not appear to value most

## Recommendation rules

Recommendations must be specific and tied to the gap.

Good recommendations:
- tell the user what message to add, strengthen, reorder, or rewrite
- explain where the change belongs: title, bullet 1, bullet 2, etc.
- preserve factual caution; do not invent unsupported claims
- prioritize the biggest GEO and recommendation gaps first

Avoid generic advice like:
- “make it more engaging”
- “improve seo”
- “add more keywords”

Prefer advice like:
- “bring the small-space use case into the title because Rufus repeatedly frames this product around compact living situations.”
- “rewrite bullet 2 to connect the feature to the user outcome, because the current bullet states the feature but not why it matters.”

## Output format

Always use this report structure.

# GEO and Listing Audit Report

## 1. Input summary
- Product / category: [brief note]
- Rufus report quality: [strong / moderate / thin]
- Listing assets reviewed: [title + number of bullets]

## 2. GEO expectation map
For each of the six dimensions, list the specific points Rufus suggests should be present.

## 3. Listing scorecard
- Total score: [0-100]
- Scenario coverage: [score]/20
- Audience match: [score]/15
- Decision-driver coverage: [score]/20
- Positioning and differentiation: [score]/15
- User-language and GEO semantics: [score]/15
- AI-readable structure clarity: [score]/15

After each dimension score, include 1-3 sentences explaining the score.

## 4. Strong coverage
List the points the current listing already communicates well.

## 5. Gaps and missed GEO signals
List the highest-priority missing, weak, or misaligned points.

## 6. Recommended changes
Provide prioritized recommendations.
For each recommendation, include:
- change priority: high / medium / low
- where to change: title / bullet number
- what to change
- why it matters for GEO / AI recommendation readiness

## 7. Executive takeaway
End with a short synthesis of the biggest issues and the biggest upside opportunities.

## Style rules

- Be analytical, crisp, and evidence-based.
- Write for operators who want to improve a listing, not for shoppers.
- Keep the report practical and diagnosis-heavy.
- Do not rewrite the full listing unless the user explicitly asks.
- If evidence is uncertain, say so.
- If the Rufus report and listing conflict, point it out clearly.

## Example framing

If Rufus strongly emphasizes “small spaces,” “easy setup,” and “good for remote work,” but the current listing mostly talks about generic premium materials, say that the listing is under-scoring on scenario coverage and misaligned on decision-driver emphasis.

If the listing mentions a relevant point but only as a feature and not as a user outcome, treat that as partial coverage, not full coverage.
