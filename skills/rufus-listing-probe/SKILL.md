---
name: Rufus 问题探针生成
description: generate up to 10 high-value rufus questions for amazon listing optimization from search terms, title, bullets, and optional category, brand, or competitor context. use when the user wants to probe rufus, reverse-engineer amazon's recommendation logic, improve listings, extract shopper intent, design question sets, or build a reusable question-generation workflow or skill for amazon products.
---

# Rufus Listing Probe

Generate a compact, high-signal set of Rufus questions that helps the user improve an Amazon listing. Treat Rufus as a probe into shopper intent and recommendation logic, not as a generic chat assistant.

## Inputs

Expect these fields when available:
- `search_terms` (required)
- `title` (required)
- `bullets` (required)
- `category` (optional)
- `brand` (optional)
- `competitor_info` (optional)

If bullets are provided as raw text, infer the 5 bullet points. If search terms are a list, treat them as a demand signal rather than something to repeat mechanically.

## Core objective

Produce questions that reveal one or more of these five layers:
1. demand context
2. buying criteria
3. competitive position
4. real user experience
5. shopper language

The questions should help the user improve titles, bullets, images, a+ content, faq, positioning, and semantic alignment with Rufus.

## Workflow

### Step 1: extract the listing signal
From the input, infer:
- product type
- core use case
- major features and benefits
- likely shopper segments
- likely shopping situation
- obvious differentiation claims
- missing or weak areas in the listing

Do not just restate the title and bullets. Build a short internal model of what the product is trying to win on.

### Step 2: choose the right question mix
Use these five question types:

#### 1. scenario and persona
Use to uncover who needs the product, in what situation, and why.
Best for weak positioning, vague bullets, new products, and listings that read like specification sheets.

#### 2. decision drivers
Use to uncover what factors matter most when shoppers choose within this product class.
Best for bullet ordering, image hierarchy, feature prioritization, and conversion optimization.

#### 3. comparison and substitution
Use to uncover what the product is compared against and what recommendation slot it can occupy.
Best for crowded categories, positioning work, premium vs budget framing, and competitor-aware optimization.

#### 4. user feedback and friction
Use to uncover what users love, dislike, misunderstand, or struggle with.
Best for faq, expectation setting, objection handling, and reducing disappointment or returns.

#### 5. shopper language
Use to uncover how real people describe the need in natural language.
Best for title rewrites, bullet phrasing, search term expansion, and semantic alignment.

### Step 3: adaptively allocate up to 10 questions
Do not distribute evenly by default. Prioritize the most valuable types based on the listing.

Use this guidance:
- If the listing is generic or feature-heavy but scenario-light, favor `scenario and persona`.
- If the listing has many claims but unclear hierarchy, favor `decision drivers`.
- If the category appears crowded or commoditized, favor `comparison and substitution`.
- If the product likely has experience risk, complexity, or expectation gaps, favor `user feedback and friction`.
- If the wording is stiff, technical, or seller-centric, favor `shopper language`.

Default allocation logic:
- choose 3 priority types
- generate 3 questions for the first priority type
- generate 3 questions for the second priority type
- generate 2 questions for the third priority type
- generate 2 questions for the remaining strongest type
- omit the weakest type unless it is clearly necessary

Total maximum: 10 questions.

If the input is very sparse, generate fewer than 10 rather than padding with weak questions.

## How to generate strong questions

### General rules
Every question must satisfy all of these:
- concrete enough that Rufus can return structured insight
- phrased like a plausible shopper question, not an analyst memo
- specific enough to expose recommendation logic, not generic product facts
- useful for a listing decision after reading the answer

Prefer questions that contain at least one of:
- a shopper segment
- a usage context
- a goal or pain point
- a tradeoff
- a comparison condition
- a level of expertise
- a budget or space constraint

### Do not generate weak questions
Avoid generic prompts like:
- is this product good
- what are the features
- who is this for
- what do users think
- what are the pros and cons
- what keywords should i use

These are too broad and usually produce low-value summaries.

## Question-type guidance

### 1. scenario and persona
Target the moment a need appears.

Good structure:
- in what situation would [persona] choose this product
- why would someone with [constraint or pain point] need this product
- is this a good option for [persona] in [specific environment]

Generate this type when the listing needs a clearer use-case story.

### 2. decision drivers
Target how shoppers judge products in the category.

Good structure:
- what matters most when choosing [product] for [scenario]
- how important is [attribute] for [persona or use case]
- how should shoppers weigh [factor a] vs [factor b] when buying [product]

Generate this type when the user needs help prioritizing claims or restructuring bullets.

### 3. comparison and substitution
Target recommendation slots and alternatives.

Good structure:
- for [persona or scenario], how does this compare with [alternative]
- what type of shopper should choose [product type a] over [product type b]
- if someone wants [goal] under [constraint], what option makes more sense

Generate this type when the user needs sharper positioning or competitor-aware messaging.

### 4. user feedback and friction
Target delight, complaints, confusion, and experience gaps.

Good structure:
- what do users most appreciate about products like this
- what problems do people most often run into when using this kind of product
- what makes buyers disappointed after purchase in this category

Generate this type when the listing likely needs objection handling or expectation management.

### 5. shopper language
Target natural wording and non-expert phrasing.

Good structure:
- how would a shopper describe needing this product in simple terms
- what would a beginner ask when looking for this kind of product
- how do people describe the problem this product solves without using technical terms

Generate this type when the current listing language sounds too technical, stiff, or seller-centric.

## Output format

Always organize the result by question type.
Use this exact structure when possible:

### priority summary
- primary focus: [top type]
- secondary focus: [second type]
- tertiary focus: [third type]
- reason: [1-3 sentences explaining why these types were prioritized from the input]

### rufus questions

#### [question type 1]
1. [question]
   - purpose: [what this is trying to uncover for listing optimization]
2. [question]
   - purpose: [what this is trying to uncover for listing optimization]

#### [question type 2]
1. [question]
   - purpose: [what this is trying to uncover for listing optimization]

Continue until all generated questions are included.

## Quality bar

A strong output should feel like:
- concise enough to run immediately
- smart enough to surface hidden intent
- specific enough to influence listing edits
- natural enough that Rufus will answer like it is talking to a shopper

## Final check before answering

Before finalizing, confirm:
- no more than 10 total questions
- no duplicate angles disguised with different wording
- at least 3 questions are clearly non-obvious
- each question maps to a likely listing action
- the mix matches the actual weaknesses or opportunities in the input
