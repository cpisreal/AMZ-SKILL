#!/usr/bin/env python3
"""Validate Amazon Product Title and Item Highlights copy."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter


PROHIBITED = set("!$?_{}^¬¦")
EXEMPT_WORDS = {
    # English articles
    "a", "an", "the",
    # Common conjunctions
    "and", "but", "or", "nor", "for", "so", "yet",
    # Common prepositions
    "about", "above", "across", "after", "against", "along", "among", "around",
    "at", "before", "behind", "below", "beneath", "beside", "between", "beyond",
    "by", "despite", "down", "during", "except", "from", "in", "inside", "into",
    "like", "near", "of", "off", "on", "onto", "out", "outside", "over", "past",
    "since", "through", "throughout", "to", "toward", "under", "underneath",
    "until", "up", "upon", "via", "with", "within", "without",
}


def word_counts(text: str) -> Counter[str]:
    words = re.findall(r"[^\W_]+(?:['’][^\W_]+)?", text.casefold(), re.UNICODE)
    return Counter(word for word in words if word not in EXEMPT_WORDS)


def prohibited_outside_brand(title: str, brand: str) -> list[str]:
    inspected = title
    if brand:
        inspected = re.sub(re.escape(brand), "", inspected, flags=re.IGNORECASE)
    return sorted({char for char in inspected if char in PROHIBITED})


def validate(title: str, highlights: str, brand: str) -> dict:
    repeats = {word: count for word, count in word_counts(title).items() if count > 2}
    prohibited = prohibited_outside_brand(title, brand)
    title_length = len(title)
    highlights_length = len(highlights)

    checks = {
        "title_length": {
            "pass": title_length <= 75,
            "actual": title_length,
            "maximum": 75,
        },
        "highlights_length": {
            "pass": highlights_length <= 125,
            "actual": highlights_length,
            "maximum": 125,
        },
        "prohibited_characters": {
            "pass": not prohibited,
            "found": prohibited,
            "brand_exception_applied": bool(brand),
        },
        "repeated_words": {
            "pass": not repeats,
            "found": repeats,
            "rule": "same non-exempt word must not appear more than twice",
        },
    }
    return {
        "pass": all(check["pass"] for check in checks.values()),
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--highlights", default="")
    parser.add_argument("--brand", default="")
    args = parser.parse_args()

    result = validate(args.title, args.highlights, args.brand)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
