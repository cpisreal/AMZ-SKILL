#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_prompts_report.py — Sponsored Products Prompts report analyzer.

Input : an Amazon "Sponsored Products Prompts" report (.xlsx or .csv)
Output: analysis.json (all numbers) + report.md (a reading sheet, numbers only)

The script is deliberately judgment-free: it produces readings and flags,
it does NOT decide whether the account is healthy. The judgment rules live in
SKILL.md so the person/agent reading the output makes the call.

Usage
    python3 analyze_prompts_report.py --input report.xlsx --out-dir out/
    python3 analyze_prompts_report.py --input report.xlsx --imp-threshold median --acos-target 0.25
    python3 analyze_prompts_report.py --self-test

Dependencies: openpyxl (only for .xlsx). CSV needs nothing beyond stdlib.
"""

import argparse
import csv
import json
import os
import re
import statistics
import sys
from collections import OrderedDict

# --------------------------------------------------------------------------
# Column mapping. Amazon changes case/wording between exports, so match by
# normalised name first, then by ordered substring rules.
# --------------------------------------------------------------------------

FIELDS = [
    ("date_start", ["start date"]),
    ("date_end", ["end date"]),
    ("campaign", ["campaign name"]),
    ("ad_group", ["ad group name"]),
    ("country", ["country"]),
    ("prompt", ["prompt details", "prompt", "search term"]),
    ("sku", ["advertised sku"]),
    ("asin", ["advertised asin"]),
    ("impressions", ["impressions"]),
    ("clicks", ["clicks"]),
    ("ctr", ["click-thru rate", "click through rate", "ctr"]),
    ("cpc", ["cost per click", "cpc"]),
    ("spend", ["spend"]),
    ("sales", ["7 day total sales", "total sales", "sales"]),
    ("acos", ["total advertising cost of sales", "acos"]),
    ("roas", ["total return on advertising spend", "roas"]),
    ("orders", ["7 day total orders", "total orders"]),
    ("units", ["7 day total units", "total units"]),
    ("sku_sales", ["7 day advertised sku sales"]),
    ("other_sales", ["7 day other sku sales"]),
    ("sku_orders", ["7 day advertised sku orders"]),
    ("other_orders", ["7 day other sku orders"]),
    ("sku_units", ["7 day advertised sku units"]),
    ("other_units", ["7 day other sku units"]),
]

NUMERIC = {"impressions", "clicks", "ctr", "cpc", "spend", "sales", "acos",
           "roas", "orders", "units", "sku_sales", "other_sales",
           "sku_orders", "other_orders", "sku_units", "other_units"}


def norm_key(s):
    s = str(s or "").strip().lower()
    s = s.replace("#", " ").replace("_", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def build_colmap(headers):
    """Map canonical field -> column index. Exact normalised match wins."""
    normed = [norm_key(h) for h in headers]
    colmap = {}
    for field, aliases in FIELDS:
        for alias in aliases:
            if alias in normed:
                colmap[field] = normed.index(alias)
                break
    # Fallback pass for fields still missing: ordered substring rules.
    for field, aliases in FIELDS:
        if field in colmap:
            continue
        for alias in aliases:
            for i, h in enumerate(normed):
                if alias in h and i not in colmap.values():
                    colmap[field] = i
                    break
            if field in colmap:
                break
    return colmap


def parse_num(v):
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return 0.0
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()").replace(",", "").replace("$", "").replace("¥", "").strip()
    pct = s.endswith("%")
    if pct:
        s = s[:-1]
    try:
        x = float(s)
    except ValueError:
        return 0.0
    if pct:
        x = x / 100.0
    return -x if neg else x


def parse_date(v):
    if v is None:
        return None
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d")
    s = str(v).strip()
    m = re.match(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if m:
        return "%s-%02d-%02d" % (m.group(1), int(m.group(2)), int(m.group(3)))
    return s or None


def read_rows(path):
    """Return (headers, list_of_raw_rows). Handles the broken-dimension xlsx case."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".csv", ".txt"):
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            rows = [r for r in reader]
        if not rows:
            raise SystemExit("empty file: %s" % path)
        return rows[0], rows[1:]
    if ext in (".xlsx", ".xlsm"):
        try:
            import openpyxl
        except ImportError:
            raise SystemExit("openpyxl is required for .xlsx input")
        import warnings
        warnings.filterwarnings("ignore")
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.worksheets[0]
        # Amazon exports often carry a wrong <dimension ref="A1">, which makes
        # read_only mode stop after one row. Reset before iterating.
        try:
            ws.reset_dimensions()
        except Exception:
            pass
        it = ws.iter_rows(values_only=True)
        try:
            headers = list(next(it))
        except StopIteration:
            raise SystemExit("empty sheet: %s" % path)
        data = [list(r) for r in it]
        return headers, data
    raise SystemExit("unsupported input type: %s" % ext)


def load_records(path):
    headers, raw = read_rows(path)
    colmap = build_colmap(headers)
    missing = [f for f, _ in FIELDS if f not in colmap and f not in
               ("sku_sales", "other_sales", "sku_orders", "other_orders",
                "sku_units", "other_units", "roas", "acos", "units", "orders")]
    if "prompt" not in colmap:
        raise SystemExit("no Prompt column found. headers=%s" % headers)
    records = []
    for r in raw:
        if not any(str(c).strip() for c in r if c is not None):
            continue

        def get(field, default=None):
            i = colmap.get(field)
            if i is None or i >= len(r):
                return default
            return r[i]

        rec = {
            "date_start": parse_date(get("date_start")),
            "date_end": parse_date(get("date_end")),
            "campaign": (str(get("campaign") or "")).strip(),
            "ad_group": (str(get("ad_group") or "")).strip(),
            "country": (str(get("country") or "")).strip(),
            "prompt": re.sub(r"\s+", " ", (str(get("prompt") or ""))).strip(),
            "sku": (str(get("sku") or "")).strip(),
            "asin": (str(get("asin") or "")).strip(),
        }
        for f in NUMERIC:
            rec[f] = parse_num(get(f))
        records.append(rec)
    return records, colmap, headers, missing


# --------------------------------------------------------------------------
# Tagging rules (first match wins for intents, multi-hit for features)
# --------------------------------------------------------------------------

DEFAULT_INTENTS = [
    ("品牌决策", r"\b(vs\.?|versus|compare|comparison|difference between|better than|"
                 r"why choose|which brand|brand name|reviews? of)\b"),
    ("痛点担忧", r"\b(noise|noisy|soundproof|slip|slippery|water|waterproof|"
                 r"stain|scratch|dust|allerg\w*|odor|smell|fade|fading|wrinkl\w*|"
                 r"shrink|tear|pet hair|fur|mold|mildew)\b"),
    ("材质属性", r"\b(velvet|linen|cotton|polyester|spandex|leather|suede|"
                 r"thermal|blackout|insulat\w*|stretch|elastic|thick|thin|soft|"
                 r"fabric|material|reversible|quilted|plush|breathable)\b"),
    ("易用维护", r"\b(wash|washable|washing|clean|cleaning|machine|dryer|dry clean|"
                 r"install\w*|assembl\w*|easy|easy to|fit|fits|fitting|size|sizes|"
                 r"inch|inches|measure|dimension\w*)\b"),
    ("场景人群", r"\b(pets?|dogs?|cats?|kids?|child|children|baby|babies|toddler|"
                 r"family|families|bedroom|living room|dining|outdoor|patio|balcony|"
                 r"winter|summer|spring|autumn|fall|dorm|apartment|rental|office)\b"),
    ("通用疑问", r"^(does|do|is|are|can|could|will|would|should|what|how|why|which|whom)\b"),
]

DEFAULT_FEATURES = OrderedDict([
    ("尺寸", r"\d+\s*(inch|inches|in\b|\"|cm)|fits up to|\bsize\b|dimension|measure"),
    ("材质", r"\b(velvet|linen|cotton|polyester|spandex|leather|suede|thermal|"
             r"blackout|insulat\w*|stretch|elastic|fabric|material)\b"),
    ("人群", r"\b(pets?|dogs?|cats?|kid|kids|child|children|baby|toddler|family|families)\b"),
    ("场景", r"\b(winter|summer|bedroom|living room|dining|outdoor|patio|office|dorm|apartment|rental)\b"),
    ("担忧", r"\b(noise|noisy|slip|slippery|water|waterproof|stain|scratch|dust|"
             r"allerg\w*|odor|smell|fade|wrinkl\w*|shrink|tear|mold)\b"),
])


def compile_rules(intents, features):
    ci = [(name, re.compile(rx, re.I)) for name, rx in intents]
    cf = [(name, re.compile(rx, re.I)) for name, rx in features.items()]
    return ci, cf


def tag_intent(text, compiled):
    for name, rx in compiled:
        if rx.search(text):
            return name
    return "其他"


# --------------------------------------------------------------------------
# Aggregation & metrics
# --------------------------------------------------------------------------

def div(a, b):
    return (a / b) if b else None


def pct(x):
    return None if x is None else round(x * 100, 1)


def aggregate(records, key="prompt"):
    agg = OrderedDict()
    for r in records:
        k = r[key]
        if k not in agg:
            agg[k] = {"impressions": 0.0, "clicks": 0.0, "spend": 0.0,
                      "sales": 0.0, "orders": 0.0, "units": 0.0, "rows": 0}
        a = agg[k]
        for f in ("impressions", "clicks", "spend", "sales", "orders", "units"):
            a[f] += r[f]
        a["rows"] += 1
    return agg


def metrics(a):
    return {
        "impressions": a["impressions"],
        "clicks": a["clicks"],
        "spend": round(a["spend"], 2),
        "sales": round(a["sales"], 2),
        "orders": a["orders"],
        "ctr": div(a["clicks"], a["impressions"]),
        "cpc": div(a["spend"], a["clicks"]),
        "acos": div(a["spend"], a["sales"]),
        "roas": div(a["sales"], a["spend"]),
    }


def health(records):
    n = len(records)
    tot = {f: sum(r[f] for r in records) for f in
           ("impressions", "clicks", "spend", "sales", "orders", "units")}
    prompts = {r["prompt"] for r in records if r["prompt"]}
    asins = {r["asin"] for r in records if r["asin"]}
    campaigns = {r["campaign"] for r in records if r["campaign"]}
    skus = {r["sku"] for r in records if r["sku"]}
    sales_rows = sum(1 for r in records if r["sales"] > 0)
    dates = sorted({r["date_start"] for r in records if r["date_start"]})
    end_dates = sorted({r["date_end"] for r in records if r["date_end"]})
    countries = sorted({r["country"] for r in records if r["country"]})
    per_prompt_rows = {}
    for r in records:
        per_prompt_rows[r["prompt"]] = per_prompt_rows.get(r["prompt"], 0) + 1
    rows_per_prompt = sorted(per_prompt_rows.values()) if per_prompt_rows else [0]
    return {
        "rows": n,
        "unique_prompts": len(prompts),
        "unique_asins": len(asins),
        "unique_skus": len(skus),
        "unique_campaigns": len(campaigns),
        "sales_rows": sales_rows,
        "sales_row_share": div(sales_rows, n),
        "rows_per_prompt_mean": div(n, len(prompts)),
        "rows_per_prompt_median": statistics.median(rows_per_prompt),
        "rows_per_prompt_max": max(rows_per_prompt),
        "date_min": dates[0] if dates else None,
        "date_max": (end_dates[-1] if end_dates else (dates[-1] if dates else None)),
        "countries": countries,
        "impressions": tot["impressions"],
        "clicks": tot["clicks"],
        "spend": round(tot["spend"], 2),
        "sales": round(tot["sales"], 2),
        "orders": tot["orders"],
        "ctr": div(tot["clicks"], tot["impressions"]),
        "cpc": div(tot["spend"], tot["clicks"]),
        "acos": div(tot["spend"], tot["sales"]),
        "roas": div(tot["sales"], tot["spend"]),
    }


def _curve(items):
    """items: list of dicts with 'spend' and 'sales'. Returns cumulative marks + curve."""
    items = sorted(items, key=lambda v: v["spend"], reverse=True)
    tot_spend = sum(v["spend"] for v in items) or 1.0
    tot_sales = sum(v["sales"] for v in items) or 1.0
    cs = ss = 0.0
    curve = []
    marks = {}
    for i, v in enumerate(items, 1):
        cs += v["spend"]
        ss += v["sales"]
        share = i / len(items)
        curve.append({"rank_share": round(share, 4),
                      "spend_share": round(cs / tot_spend, 4),
                      "sales_share": round(ss / tot_sales, 4)})
        for m in (0.1, 0.2, 0.5):
            if m not in marks and share >= m - 1e-9:
                marks[m] = {"rank_share": round(share, 4),
                            "spend_share": round(cs / tot_spend, 4),
                            "sales_share": round(ss / tot_sales, 4)}
    return {"marks": marks, "curve": curve, "n": len(items)}


def concentration(agg):
    """Prompt-level concentration — the decision unit."""
    return _curve(list(agg.values()))


def concentration_by_row(records):
    """Row-level concentration — kept because it is what a spreadsheet sort shows,
    and because a previously published version of this analysis quoted this level."""
    return _curve([{"spend": r["spend"], "sales": r["sales"]} for r in records])


def campaign_structure(records):
    agg = aggregate(records, key="campaign")
    items = sorted(agg.items(), key=lambda kv: kv[1]["spend"], reverse=True)
    tot = sum(v["spend"] for _, v in items) or 1.0
    top10 = sum(v["spend"] for _, v in items[:10])
    return {
        "n_campaigns": len(items),
        "top10_spend_share": round(top10 / tot, 4),
        "max_campaign_spend": round(items[0][1]["spend"], 2) if items else 0,
        "top10": [{"campaign": k, "spend": round(v["spend"], 2),
                   "sales": round(v["sales"], 2),
                   "acos": div(v["spend"], v["sales"])} for k, v in items[:10]],
    }


def by_country(records):
    out = []
    for k, a in sorted(aggregate(records, key="country").items(),
                       key=lambda kv: kv[1]["spend"], reverse=True):
        m = metrics(a)
        m["country"] = k
        out.append(m)
    return out


def intent_breakdown(records, prompt_agg, compiled):
    tags = {p: tag_intent(p, compiled) for p in prompt_agg}
    groups = OrderedDict()
    for p, a in prompt_agg.items():
        t = tags[p]
        g = groups.setdefault(t, {"prompts": 0, "impressions": 0.0, "clicks": 0.0,
                                  "spend": 0.0, "sales": 0.0, "orders": 0.0,
                                  "units": 0.0, "rows": 0})
        g["prompts"] += 1
        for f in ("impressions", "clicks", "spend", "sales", "orders", "units"):
            g[f] += a[f]
        g["rows"] += a["rows"]
    tot_imp = sum(g["impressions"] for g in groups.values()) or 1.0
    tot_spend = sum(g["spend"] for g in groups.values()) or 1.0
    tot_sales = sum(g["sales"] for g in groups.values()) or 1.0
    out = []
    for name, g in sorted(groups.items(), key=lambda kv: kv[1]["impressions"], reverse=True):
        imp_share = g["impressions"] / tot_imp
        spend_share = g["spend"] / tot_spend
        sales_share = g["sales"] / tot_sales
        out.append({
            "group": name,
            "prompts": g["prompts"],
            "impressions": g["impressions"],
            "imp_share": round(imp_share, 4),
            "spend_share": round(spend_share, 4),
            "sales_share": round(sales_share, 4),
            "ctr": div(g["clicks"], g["impressions"]),
            "acos": div(g["spend"], g["sales"]),
            "imp_vs_sales": round(imp_share / sales_share, 2) if sales_share else None,
            "sales_vs_imp": round(sales_share / imp_share, 2) if imp_share else None,
        })
    tagged = sum(g["prompts"] for n, g in groups.items() if n != "其他")
    return {"groups": out, "coverage": round(tagged / len(prompt_agg), 4),
            "n_prompts": len(prompt_agg)}


def quadrants(prompt_agg, imp_threshold, acos_target):
    items = []
    for p, a in prompt_agg.items():
        m = metrics(a)
        items.append({"prompt": p, "impressions": m["impressions"],
                      "clicks": m["clicks"], "spend": m["spend"],
                      "sales": m["sales"], "ctr": m["ctr"], "acos": m["acos"]})
    imp_thr = statistics.median([i["impressions"] for i in items]) if imp_threshold == "median" else float(imp_threshold)
    cells = OrderedDict((k, {"n": 0, "impressions": 0.0, "spend": 0.0, "sales": 0.0})
                        for k in ("高曝光·高效", "高曝光·低效", "低曝光·高效", "低曝光·低效"))
    for i in items:
        hi_imp = i["impressions"] >= imp_thr
        if i["sales"] > 0 and i["acos"] is not None:
            eff = i["acos"] < acos_target
        else:
            eff = False
        key = ("高曝光·" if hi_imp else "低曝光·") + ("高效" if eff else "低效")
        i["cell"] = key
        c = cells[key]
        c["n"] += 1
        c["impressions"] += i["impressions"]
        c["spend"] += i["spend"]
        c["sales"] += i["sales"]
    tot = {"n": len(items),
           "impressions": sum(i["impressions"] for i in items) or 1.0,
           "spend": sum(i["spend"] for i in items) or 1.0,
           "sales": sum(i["sales"] for i in items) or 1.0}
    for k, c in cells.items():
        c["share_of_prompts"] = round(c["n"] / tot["n"], 4) if tot["n"] else None
        c["imp_share"] = round(c["impressions"] / tot["impressions"], 4)
        c["spend_share"] = round(c["spend"] / tot["spend"], 4)
        c["sales_share"] = round(c["sales"] / tot["sales"], 4)
        c["spend"] = round(c["spend"], 2)
        c["sales"] = round(c["sales"], 2)
    return {"imp_threshold": imp_thr, "acos_target": acos_target,
            "cells": cells, "total": {"n": tot["n"], "spend": round(tot["spend"], 2),
                                      "sales": round(tot["sales"], 2)},
            "items": items}


def feature_breakdown(prompt_agg, compiled_features, base_ctr, base_acos):
    rows = []
    tot_imp = sum(a["impressions"] for a in prompt_agg.values()) or 1.0
    for name, rx in compiled_features:
        n = 0
        imp = clicks = spend = sales = 0.0
        for p, a in prompt_agg.items():
            if rx.search(p):
                n += 1
                imp += a["impressions"]
                clicks += a["clicks"]
                spend += a["spend"]
                sales += a["sales"]
        ctr = div(clicks, imp)
        acos = div(spend, sales)
        rows.append({
            "feature": name, "prompts": n,
            "impressions": imp,
            "imp_share": round(imp / tot_imp, 4),
            "ctr": ctr, "acos": acos,
            "ctr_vs_base": round(ctr / base_ctr, 2) if (ctr and base_ctr) else None,
            "spend": round(spend, 2), "sales": round(sales, 2),
        })
    rows.sort(key=lambda r: r["imp_share"], reverse=True)
    return rows


def extremes(prompt_agg, imp_threshold, acos_target, top_n=8):
    items = quadrants(prompt_agg, imp_threshold, acos_target)["items"]
    winners = [i for i in items if i["sales"] > 0 and i["impressions"] <= 100]
    winners.sort(key=lambda i: i["sales"], reverse=True)
    losers = [i for i in items if i["impressions"] >= 1000]
    losers.sort(key=lambda i: (i["acos"] is None, -(i["acos"] or 0)))
    return {"long_tail_winners": winners[:top_n], "high_volume_losers": losers[:top_n]}


def data_quality(records, colmap, missing):
    blank_prompt = sum(1 for r in records if not r["prompt"])
    dup = len(records) - len({(r["prompt"], r["campaign"], r["asin"],
                               r["date_start"], r["date_end"]) for r in records})
    zero_imp = sum(1 for r in records if r["impressions"] == 0)
    return {"blank_prompt_rows": blank_prompt, "duplicate_rows": dup,
            "zero_impression_rows": zero_imp,
            "missing_optional_columns": missing}


def prompt_table(records, prompt_agg, compiled_intents, imp_threshold, acos_target):
    """Per-prompt reading sheet — this is the list the article's action section is built from."""
    q = quadrants(prompt_agg, imp_threshold, acos_target)
    cells = {i["prompt"]: i["cell"] for i in q["items"]}
    rows = []
    for p, a in prompt_agg.items():
        m = metrics(a)
        rows.append({
            "prompt": p,
            "rows_in_report": a["rows"],
            "impressions": int(m["impressions"]),
            "clicks": int(m["clicks"]),
            "ctr": m["ctr"],
            "spend": m["spend"],
            "sales": m["sales"],
            "orders": m["orders"],
            "acos": m["acos"],
            "intent": tag_intent(p, compiled_intents),
            "cell": cells.get(p, ""),
        })
    rows.sort(key=lambda r: (-r["sales"], -r["impressions"]))
    return rows


def write_prompt_csv(rows, path):
    import csv as _csv
    cols = ["prompt", "rows_in_report", "impressions", "clicks", "ctr", "spend",
            "sales", "orders", "acos", "intent", "cell"]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def run(input_path, imp_threshold, acos_target, rules_path=None, top_n=8):
    records, colmap, headers, missing = load_records(input_path)
    if not records:
        raise SystemExit("no data rows parsed from %s" % input_path)
    intents, features = DEFAULT_INTENTS, DEFAULT_FEATURES
    if rules_path:
        with open(rules_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        intents = [(r["name"], r["regex"]) for r in cfg.get("intents", [])] or intents
        if cfg.get("features"):
            features = OrderedDict((r["name"], r["regex"]) for r in cfg["features"])
    compiled_intents, compiled_features = compile_rules(intents, features)

    prompt_agg = aggregate(records, "prompt")
    h = health(records)
    result = {
        "source": os.path.basename(input_path),
        "columns_found": sorted(colmap.keys()),
        "health": h,
        "concentration": {"prompt": concentration(prompt_agg),
                          "row": concentration_by_row(records)},
        "campaign_structure": campaign_structure(records),
        "by_country": by_country(records),
        "intent": intent_breakdown(records, prompt_agg, compiled_intents),
        "quadrants": {k: v for k, v in quadrants(prompt_agg, imp_threshold, acos_target).items() if k != "items"},
        "features": feature_breakdown(prompt_agg, compiled_features, h["ctr"], h["acos"]),
        "extremes": extremes(prompt_agg, imp_threshold, acos_target, top_n),
        "data_quality": data_quality(records, colmap, missing),
    }
    rows = prompt_table(records, prompt_agg, compiled_intents, imp_threshold, acos_target)
    return result, rows


# --------------------------------------------------------------------------
# Markdown rendering (numbers only — judgment stays with the reader)
# --------------------------------------------------------------------------

def f2(x, dash="—"):
    if x is None:
        return dash
    if isinstance(x, float):
        return ("%.2f" % x).rstrip("0").rstrip(".")
    return str(x)


def pc(x):
    return "—" if x is None else "%.1f%%" % (x * 100)


def render_md(res):
    h = res["health"]
    L = []
    a = L.append
    a("# Prompts 报表读数表")
    a("")
    a("源文件 `%s` · 日期 %s ~ %s · 站点 %s" % (res["source"], h["date_min"], h["date_max"],
                                                "/".join(h["countries"]) or "—"))
    a("")
    a("> 这是**读数**，不是结论。每一节下面写的是口径，判读规则见 SKILL.md。")
    a("")
    a("## 一、体检")
    a("")
    a("| 指标 | 值 |")
    a("|---|---|")
    a("| 行数 | %s |" % h["rows"])
    a("| 唯一提问 | %s |" % h["unique_prompts"])
    a("| 唯一 ASIN / SKU / 活动 | %s / %s / %s |" % (h["unique_asins"], h["unique_skus"], h["unique_campaigns"]))
    a("| 有销售的行 | %s（%s） |" % (h["sales_rows"], pc(h["sales_row_share"])))
    a("| 每条提问平均占行数（中位 / 最大） | %s / %s |" % (f2(h["rows_per_prompt_median"]), h["rows_per_prompt_max"]))
    a("| 曝光 / 点击 | %s / %s |" % (int(h["impressions"]), int(h["clicks"])))
    a("| 花费 / 销售 | %s / %s |" % (f2(h["spend"]), f2(h["sales"])))
    a("| CTR / CPC | %s / %s |" % (pc(h["ctr"]), f2(h["cpc"])))
    a("| ACOS / ROAS | %s / %s |" % (pc(h["acos"]), f2(h["roas"])))
    a("")
    a("## 二、集中度（按花费排序的累计占比）")
    a("")
    a("两种粒度都列出来。**判断用「按提问」那一张**（提问才是决策单位）；")
    a("「按行」那一张是 Excel 直接排序看到的结果，同一句话被拆成多行时会虚增头部。")
    a("")
    a("| 粒度 | 排到 | 累计花费占比 | 累计销售占比 | 开口 |")
    a("|---|---|---|---|---|")
    for level, label in (("prompt", "按提问"), ("row", "按行")):
        marks = res["concentration"][level]["marks"]
        for m in (0.1, 0.2, 0.5):
            mk = marks.get(str(m)) or marks.get(float(m))
            if not mk:
                continue
            gap = mk["spend_share"] - mk["sales_share"]
            a("| %s | 前 %s | %s | %s | %+.1f pt |" % (label, pc(mk["rank_share"]),
                                                       pc(mk["spend_share"]),
                                                       pc(mk["sales_share"]), gap * 100))
    cs = res["campaign_structure"]
    a("")
    a("活动层：%s 个活动，花费前十合计占 %s，第一名活动花费 %s。" %
      (cs["n_campaigns"], pc(cs["top10_spend_share"]), f2(cs["max_campaign_spend"])))
    a("")
    a("## 三、意图分层")
    a("")
    a("覆盖 %s 条提问，规则命中率 %s。" % (res["intent"]["n_prompts"], pc(res["intent"]["coverage"])))
    a("")
    a("| 组 | 提问数 | 曝光占比 | 花费占比 | 销售占比 | CTR | ACOS | 曝光÷销售 |")
    a("|---|---|---|---|---|---|---|---|")
    for g in res["intent"]["groups"]:
        a("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            g["group"], g["prompts"], pc(g["imp_share"]), pc(g["spend_share"]),
            pc(g["sales_share"]), pc(g["ctr"]), pc(g["acos"]), f2(g["imp_vs_sales"])))
    a("")
    a("## 四、四象限")
    a("")
    q = res["quadrants"]
    a("横线 = 曝光 %s（%s），竖线 = ACOS %s。" % (
        f2(q["imp_threshold"]), "中位数" if q["imp_threshold"] in ("median",) else "指定阈值",
        pc(q["acos_target"])))
    a("")
    a("| 格 | 提问数 | 曝光占比 | 花费占比 | 销售占比 |")
    a("|---|---|---|---|---|")
    for k, c in q["cells"].items():
        a("| %s | %s | %s | %s | %s |" % (k, c["n"], pc(c["imp_share"]),
                                          pc(c["spend_share"]), pc(c["sales_share"])))
    a("")
    a("## 五、文本特征（可多命中）")
    a("")
    a("| 特征 | 命中提问 | 曝光占比 | CTR | CTR÷全场 | ACOS | 花费 | 销售 |")
    a("|---|---|---|---|---|---|---|---|")
    for r in res["features"]:
        a("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["feature"], r["prompts"], pc(r["imp_share"]), pc(r["ctr"]),
            f2(r["ctr_vs_base"]), pc(r["acos"]), f2(r["spend"]), f2(r["sales"])))
    a("")
    a("## 六、结构补一刀")
    a("")
    a("| 站点 | 花费 | 销售 | ACOS |")
    a("|---|---|---|---|")
    for c in res["by_country"]:
        a("| %s | %s | %s | %s |" % (c["country"], f2(c["spend"]), f2(c["sales"]), pc(c["acos"])))
    a("")
    a("## 七、极值样本")
    a("")
    a("**低曝光高分（曝光 ≤ 100，按销售降序）**")
    a("")
    a("| 提问 | 曝光 | CTR | 花费 | 销售 | ACOS |")
    a("|---|---|---|---|---|---|")
    for i in res["extremes"]["long_tail_winners"]:
        a("| %s | %s | %s | %s | %s | %s |" % (i["prompt"], int(i["impressions"]),
                                               pc(i["ctr"]), f2(i["spend"]),
                                               f2(i["sales"]), pc(i["acos"])))
    a("")
    a("**高曝光低分（曝光 ≥ 1000，按 ACOS 降序）**")
    a("")
    a("| 提问 | 曝光 | CTR | 花费 | 销售 | ACOS |")
    a("|---|---|---|---|---|---|")
    for i in res["extremes"]["high_volume_losers"]:
        a("| %s | %s | %s | %s | %s | %s |" % (i["prompt"], int(i["impressions"]),
                                               pc(i["ctr"]), f2(i["spend"]),
                                               f2(i["sales"]), pc(i["acos"])))
    a("")
    a("## 八、数据质量")
    a("")
    dq = res["data_quality"]
    a("| 项 | 值 |")
    a("|---|---|")
    a("| 提问为空的行 | %s |" % dq["blank_prompt_rows"])
    a("| 完全重复的行 | %s |" % dq["duplicate_rows"])
    a("| 曝光为 0 的行 | %s |" % dq["zero_impression_rows"])
    a("| 未找到的可选列 | %s |" % (", ".join(dq["missing_optional_columns"]) or "无"))
    a("")
    return "\n".join(L)


# --------------------------------------------------------------------------
# Self-test: synthetic data, checks the aggregation invariants
# --------------------------------------------------------------------------

def _synthetic_records():
    base = {"date_start": "2026-09-01", "date_end": "2026-09-30",
            "country": "United States", "sku": "SKU1", "asin": "B0TEST",
            "orders": 0.0, "units": 0.0, "acos": 0.0, "roas": 0.0,
            "sku_sales": 0.0, "other_sales": 0.0, "sku_orders": 0.0,
            "other_orders": 0.0, "sku_units": 0.0, "other_units": 0.0}
    rows = []

    def add(prompt, imp, clk, spend, sales, camp="C1"):
        r = dict(base)
        r.update({"prompt": prompt, "impressions": float(imp), "clicks": float(clk),
                  "spend": float(spend), "sales": float(sales), "campaign": camp,
                  "ad_group": "AG1"})
        rows.append(r)

    # one prompt split across 3 rows -> must aggregate to 1
    add("is it quiet at night", 10000, 5, 2.0, 0.0, "C1")
    add("is it quiet at night", 20000, 15, 8.0, 10.0, "C2")
    add("is it quiet at night", 531, 4, 7.43, 15.0, "C1")
    # long tail winner
    add("humidifier with a 4 litre tank for a small room", 2, 2, 2.17, 74.40, "C3")
    add("humidifier for a bedroom with a baby", 26, 3, 2.40, 0.0, "C3")
    add("why choose this brand of humidifier", 5, 1, 0.30, 40.0, "C4")
    return rows


def self_test():
    recs = _synthetic_records()
    prompt_agg = aggregate(recs, "prompt")
    assert len(prompt_agg) == 4, "expected 4 unique prompts, got %d" % len(prompt_agg)
    quiet = prompt_agg["is it quiet at night"]
    assert quiet["rows"] == 3
    assert abs(quiet["impressions"] - 30531) < 1e-6
    assert abs(quiet["sales"] - 25.0) < 1e-6
    h = health(recs)
    assert abs(h["spend"] - (2.0 + 8.0 + 7.43 + 2.17 + 2.40 + 0.30)) < 1e-6
    assert h["unique_prompts"] == 4
    assert h["sales_rows"] == 4
    ci, cf = compile_rules(DEFAULT_INTENTS, DEFAULT_FEATURES)
    ints = intent_breakdown(recs, prompt_agg, ci)
    assert sum(g["prompts"] for g in ints["groups"]) == 4
    assert abs(sum(g["imp_share"] for g in ints["groups"]) - 1.0) < 0.01
    q = quadrants(prompt_agg, 3000, 0.3)
    assert sum(c["n"] for c in q["cells"].values()) == 4
    assert abs(q["cells"]["低曝光·高效"]["sales"] - (74.40 + 40.0)) < 1e-6
    feats = feature_breakdown(prompt_agg, cf, h["ctr"], h["acos"])
    assert len(feats) == 5
    # rule order is "specific beats generic": a named pain wins over a question opener
    assert tag_intent("can it work without noise", ci) == "痛点担忧"
    assert tag_intent("filter is easy to rinse", ci) == "易用维护"
    assert tag_intent("does it work for a room with two cats", ci) == "场景人群"
    assert tag_intent("does it come in grey", ci) == "通用疑问"
    print("self-test OK: 4 prompts / aggregation / intent coverage / quadrants / features")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Analyze an Amazon Sponsored Products Prompts report.")
    ap.add_argument("--input", help="report .xlsx or .csv")
    ap.add_argument("--out-dir", default="out", help="directory for analysis.json and report.md")
    ap.add_argument("--imp-threshold", default="3000",
                    help="impression cut for quadrants: a number, or 'median'")
    ap.add_argument("--acos-target", type=float, default=0.30, help="ACOS cut for quadrants, e.g. 0.3")
    ap.add_argument("--rules", help="JSON file overriding intent/feature regex rules")
    ap.add_argument("--top", type=int, default=8, help="rows in the extremes tables")
    ap.add_argument("--self-test", action="store_true", help="run built-in checks on synthetic data")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if not args.input:
        ap.error("--input is required unless --self-test is used")

    res, rows = run(args.input, args.imp_threshold, args.acos_target, args.rules, args.top)
    os.makedirs(args.out_dir, exist_ok=True)
    jpath = os.path.join(args.out_dir, "analysis.json")
    mpath = os.path.join(args.out_dir, "report.md")
    cpath = os.path.join(args.out_dir, "prompts.csv")
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    with open(mpath, "w", encoding="utf-8") as f:
        f.write(render_md(res))
    write_prompt_csv(rows, cpath)
    h = res["health"]
    print("rows=%d prompts=%d spend=%.2f sales=%.2f acos=%s" % (
        h["rows"], h["unique_prompts"], h["spend"], h["sales"],
        "%.1f%%" % (h["acos"] * 100) if h["acos"] else "n/a"))
    print("written:", jpath, mpath, cpath)
    return 0


if __name__ == "__main__":
    sys.exit(main())
