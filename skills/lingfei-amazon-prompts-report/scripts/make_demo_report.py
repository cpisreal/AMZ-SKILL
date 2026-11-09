#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_demo_report.py — build a synthetic "Sponsored Products Prompts" report.

Why this exists: nobody should test the pipeline on a client's real export, and
a real export must never be shipped inside a skill package. This generator
produces a file with the same 24 columns and the same pathologies as a real
account, using an **invented product category and invented numbers** (a small
appliance, deliberately unrelated to any client).

The pathologies it reproduces:
  * a handful of generic questions soak up tens of thousands of impressions
    with almost no clicks (the "black hole")
  * long-tail, very specific prompts get a handful of impressions and convert
    at a few dollars of ACOS (the "hidden money")
  * one prompt appears in many rows (campaign x ASIN x day), so the row-level
    numbers look worse than the prompt-level ones
  * most rows have zero sales

Usage
    python3 make_demo_report.py --out demo_report.xlsx
    python3 make_demo_report.py --out demo_report.csv --format csv --prompts 400
"""

import argparse
import csv
import os
import random
import sys

HEADERS = [
    "Start Date", "End Date", "Campaign Name", "Ad Group Name", "Country",
    "Prompt details", "Advertised SKU", "Advertised ASIN", "Impressions",
    "Clicks", "Click-Thru Rate (CTR)", "Cost Per Click (CPC)", "Spend",
    "7 Day Total Sales ", "Total Advertising Cost of Sales (ACOS) ",
    "Total Return on Advertising Spend (ROAS)", "7 Day Total Orders (#)",
    "7 Day Total Units (#)", "7 Day Advertised SKU Orders (#)",
    "7 Day Other SKU Orders (#)", "7 Day Advertised SKU Units (#)",
    "7 Day Other SKU Units (#)", "7 Day Advertised SKU Sales ",
    "7 Day Other SKU Sales ",
]

# Deliberately invented vocabulary: a small appliance, not the client's category.
GENERIC = [
    "does it work well", "is it worth buying", "can it run all night",
    "does it really work", "is this a good product", "can it last long",
    "does it look good on a desk", "is it easy to use", "does it come in other colors",
    "can it be returned", "does it use much power", "is it quiet at night",
    "does it need a filter", "does it make the air dry",
]
MATERIAL = [
    "stainless steel {c} with a sealed tank", "plastic {c} with a removable base",
    "ceramic filter {c} for hard water", "bpa free {c} for a nursery",
    "{c} with a washable mesh filter",
]
SCENE = [
    "{c} for a bedroom with a baby", "{c} for a small apartment in winter",
    "{c} for a room with two cats", "{c} for an office desk",
    "{c} for a rental room without windows", "{c} for a basement",
]
SIZE = [
    "{c} with a 4 litre tank for a small room", "{c} that fits under a 30 inch desk",
    "{c} for a room up to 500 square feet", "{c} with a 2 litre tank for travel",
    "{c} that covers 40 square metres",
]
WORRY = [
    "{c} that does not leak on a wood floor", "{c} that does not smell after a week",
    "{c} that does not leave white dust", "{c} with a filter that is easy to rinse",
    "{c} that does not wake you up at night",
]
BRAND = [
    "why choose this brand of {c}", "brand a vs brand b {c}",
    "which {c} brand is better", "{c} reviews compared",
]
CATEGORIES = ["humidifier", "air purifier", "dehumidifier"]
MODIFIERS = ["", "", "", " in white", " in grey", " for a large room",
             " with a remote", " for a nursery", " with a timer", " for two rooms"]


def build_rows(seed=20261024, n_prompts=420, days=30):
    rnd = random.Random(seed)
    rows = []

    def add(prompt, imp, ctr, spend, sales, campaign, sku, asin, day):
        clicks = max(0, int(round(imp * ctr)))
        rows.append({
            "Start Date": "2026-09-%02d" % (1 + day % 30),
            "End Date": "2026-09-%02d" % (1 + day % 30),
            "Campaign Name": campaign,
            "Ad Group Name": "Ad group 1",
            "Country": "United States",
            "Prompt details": prompt,
            "Advertised SKU": sku,
            "Advertised ASIN": asin,
            "Impressions": imp,
            "Clicks": clicks,
            "Click-Thru Rate (CTR)": round(ctr, 4),
            "Cost Per Click (CPC)": round(spend / clicks, 2) if clicks else 0,
            "Spend": round(spend, 2),
            "7 Day Total Sales ": round(sales, 2),
            "Total Advertising Cost of Sales (ACOS) ": round(spend / sales, 4) if sales else None,
            "Total Return on Advertising Spend (ROAS)": round(sales / spend, 2) if spend else None,
            "7 Day Total Orders (#)": int(sales // 45) if sales else 0,
            "7 Day Total Units (#)": int(sales // 45) if sales else 0,
            "7 Day Advertised SKU Orders (#)": int(sales // 45) if sales else 0,
            "7 Day Other SKU Orders (#)": 0,
            "7 Day Advertised SKU Units (#)": int(sales // 45) if sales else 0,
            "7 Day Other SKU Units (#)": 0,
            "7 Day Advertised SKU Sales ": round(sales, 2),
            "7 Day Other SKU Sales ": 0,
        })

    # 1) black holes: a few prompts with huge impressions and almost no clicks
    hole_imp = [38100, 15420, 9310, 4120, 3480, 2410, 1380, 1150]
    hole_sales = [0, 0, 22.49, 17.99, 30.20, 0, 26.10, 0]
    for p, imp, sales in zip(GENERIC[:8], hole_imp, hole_sales):
        spend = round(rnd.uniform(8, 42), 2)
        for day in range(rnd.randint(2, 6)):
            add(p, max(1, imp // 4), rnd.uniform(0.0002, 0.006), spend / 4, sales / 4,
                "CAMP-%02d" % rnd.randint(1, 40), "SKU-%03d" % rnd.randint(1, 60),
                "B0%08d" % rnd.randint(1, 400), day)

    # 2) prompts that both get volume and convert (the "hold it, don't touch it" cell)
    for p, imp, sales in [
        ("stainless steel air purifier with a sealed tank", 8700, 505.0),
        ("humidifier for a bedroom with a baby", 6100, 400.0),
        ("dehumidifier for a basement up to 500 square feet", 4900, 295.0),
        ("humidifier with a 4 litre tank for a small room", 4200, 250.0),
        ("air purifier with a washable mesh filter", 3600, 185.0),
    ]:
        clicks = int(imp * rnd.uniform(0.02, 0.05))
        spend = round(clicks * rnd.uniform(0.5, 0.9), 2)
        for day in range(4):
            add(p, imp // 4, clicks / max(1, imp // 4), spend / 4, sales / 4,
                "CAMP-%02d" % rnd.randint(1, 40), "SKU-%03d" % rnd.randint(1, 60),
                "B0%08d" % rnd.randint(1, 400), day)

    # 3) hidden money: specific long-tail, tiny impressions, high conversion
    pool = []
    for _ in range(n_prompts):
        kind = rnd.choices(["material", "scene", "size", "worry", "brand", "generic"],
                           weights=[22, 12, 12, 10, 3, 41])[0]
        cat = rnd.choice(CATEGORIES)
        tpl = rnd.choice({"material": MATERIAL, "scene": SCENE, "size": SIZE,
                          "worry": WORRY, "brand": BRAND, "generic": GENERIC}[kind])
        pool.append((tpl.replace("{c}", cat) + rnd.choice(MODIFIERS), kind))
    for p, kind in pool:
        if kind in ("generic",):
            imp = rnd.choice([0, 1, 2, 3, 5, 8, 12, 30, 80, 200, 600])
            ctr = rnd.uniform(0.0005, 0.008)
            sales = 0.0 if rnd.random() < 0.97 else round(rnd.uniform(12, 40), 2)
        else:
            imp = rnd.choice([0, 1, 2, 3, 5, 10, 26, 40, 77, 120, 400])
            ctr = rnd.uniform(0.02, 0.14)
            sales = 0.0 if rnd.random() < 0.86 else round(rnd.uniform(15, 95), 2)
        spend = round(max(0.02, imp * ctr * rnd.uniform(0.5, 1.2)), 2) if imp else 0.0
        for day in range(rnd.choices([1, 1, 1, 2, 3], weights=[60, 15, 10, 10, 5])[0]):
            add(p, max(0, imp // 1), ctr, spend, sales,
                "CAMP-%02d" % rnd.randint(1, 60), "SKU-%03d" % rnd.randint(1, 80),
                "B0%08d" % rnd.randint(1, 600), day)
    return rows


def write_csv(rows, path):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADERS)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_xlsx(rows, path):
    try:
        import openpyxl
    except ImportError:
        raise SystemExit("openpyxl is needed for xlsx output; use --format csv instead")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sponsored_Products_Prompts_repo"
    ws.append(HEADERS)
    for r in rows:
        ws.append([r[h] for h in HEADERS])
    wb.save(path)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate a synthetic Prompts report for testing.")
    ap.add_argument("--out", default="demo_report.xlsx")
    ap.add_argument("--format", choices=["xlsx", "csv"], default=None)
    ap.add_argument("--prompts", type=int, default=420)
    ap.add_argument("--seed", type=int, default=20261024)
    args = ap.parse_args(argv)

    fmt = args.format or ("csv" if args.out.lower().endswith(".csv") else "xlsx")
    rows = build_rows(seed=args.seed, n_prompts=args.prompts)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    if fmt == "csv":
        write_csv(rows, args.out)
    else:
        write_xlsx(rows, args.out)
    print("wrote %s (%s, %d rows, %d unique prompts)"
          % (args.out, fmt, len(rows), len({r["Prompt details"] for r in rows})))
    return 0


if __name__ == "__main__":
    sys.exit(main())
