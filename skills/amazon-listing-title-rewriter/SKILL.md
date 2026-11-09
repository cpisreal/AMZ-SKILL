---
name: amazon-listing-title-rewriter
description: Rewrite and validate Amazon product Listing titles under the July 27, 2026 title policy, including the 75-character Product Title limit, the optional 125-character Item Highlights field, prohibited-character checks, and repeated-word checks. Use when a user provides an Amazon Listing URL, page text, screenshot, ASIN information, or an existing title and asks to shorten, optimize, audit, or rewrite the title for Amazon compliance.
---

# Amazon Listing Title Rewriter

Turn a product page or supplied product facts into one concise, factually supported Amazon title. Apply the policy in [references/policy.md](references/policy.md) and validate every final candidate with `scripts/validate_listing_copy.py`.

## Workflow

1. Read [references/policy.md](references/policy.md).
2. Inspect the supplied Listing URL, page text, screenshot, or product data. Extract only facts supported by the source:
   - exact brand;
   - product type;
   - variant-defining size, count, color, model, compatibility, or audience;
   - one or two attributes essential to identifying or distinguishing the product;
   - material, benefits, and use cases suitable for Item Highlights.
3. Determine applicability from the marketplace and product type.
   - Apply the 75/125 limits to non-media products outside Egypt, Saudi Arabia, Türkiye, and the UAE.
   - If applicability is uncertain, produce a 75-character-safe draft and state the assumption briefly.
   - Respect stricter category or marketplace rules when the source provides them.
4. Draft the title in this order when natural:

   `Brand + Product Type + Essential Differentiator + Variant/Size/Count`

   Preserve product identity. Remove keyword stuffing, promotional language, duplicated synonyms, use-case lists, and secondary benefits.
5. Move useful supported details that do not fit the title into Item Highlights. Do not merely repeat the title.
6. Validate the exact strings:

   ```bash
   python3 scripts/validate_listing_copy.py \
     --title "TITLE" \
     --highlights "ITEM HIGHLIGHTS" \
     --brand "EXACT BRAND"
   ```

7. Revise until the applicable hard checks pass. Treat stemming and readability findings as editorial warnings, not invented official rules.

## Writing Rules

- Count every Unicode character, including spaces and punctuation.
- Never truncate mechanically at character 75; rewrite the information hierarchy.
- Never invent certifications, performance claims, compatibility, materials, dimensions, audience, or use cases.
- Keep the exact brand spelling. Use a prohibited symbol only when it is demonstrably part of the formal brand name.
- Count the same word case-insensitively. Do not allow it more than twice, except articles, conjunctions, and prepositions.
- Prefer readable customer language over search-term strings.
- Do not claim that Item Highlights has the same search weight as the title. It is searchable, but the relative weight is unspecified.
- Do not treat Item Highlights as a replacement for bullet points, description, A+ Content, or backend search terms.

## Output

Lead with one recommended answer:

```text
推荐标题（NN/75）：
...

Item Highlights（NN/125）：
...

校验：
- 字符数：通过
- 禁用字符：通过
- 重复词：通过

改写说明：
一句话说明保留了哪些身份信息、哪些细节被移到 Item Highlights。
```

Omit Item Highlights only when the user explicitly requests title-only output. If critical product facts are unavailable, list the missing facts and provide a clearly labeled provisional draft instead of guessing. Provide alternatives only when they represent meaningful positioning choices.
