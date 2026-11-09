# -*- coding: utf-8 -*-
"""第 3 步：爬目标 ASIN 的 Listing。

命中了词，还得知道「这些词跟我的链接相不相关」。所以这一步抓回标题、五点描述、正文描述、
类目、品牌 —— 这堆文本就是第 4 步打分的「标准答案」。

为什么一定要爬、不能凭 ASIN 号猜：Jev 判相关度靠的是拿搜索词跟商品的**文字描述**比。
bullet ice maker（子弹冰）和 nugget ice maker（冰珠）只差一个词，但冰型完全不同，
不给它标题和五点，它没法下判断。

🔴 坑二：爬 Listing 时如果网络走海外节点，price 字段可能抓到别的币种（新加坡元 S$ 等）。
        它跟关键词相关度无关，但别拿它去做定价判断。
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

MARKETS = {"com": "www.amazon.com", "co.uk": "www.amazon.co.uk", "de": "www.amazon.de",
           "co.jp": "www.amazon.co.jp", "ca": "www.amazon.ca", "fr": "www.amazon.fr",
           "it": "www.amazon.it", "es": "www.amazon.es"}


def fetch_listing(asin: str, market: str = "com", proxy: str | None = None,
                  timeout: int = 25, retries: int = 2) -> dict:
    host = MARKETS.get(market, MARKETS["com"])
    url = f"https://{host}/dp/{asin}"
    proxies = {"http": proxy, "https": proxy} if proxy else None
    headers = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9",
               "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
    last = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=headers, proxies=proxies, timeout=timeout)
            if r.status_code == 200 and "captcha" not in r.text[:4000].lower():
                return _parse(r.text, asin, url)
            last = f"HTTP {r.status_code}" + ("（疑似验证码页）" if "captcha" in r.text[:4000].lower() else "")
        except Exception as e:                     # noqa: BLE001
            last = str(e)[:160]
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(
        f"抓取 {asin} 失败：{last}。\n"
        f"  可以：① 加 --proxy 走干净出口；② 用 --listing-json 直接喂一份已抓好的 JSON。")


def _parse(html: str, asin: str, url: str) -> dict:
    s = BeautifulSoup(html, "lxml")

    def txt(sel, sep=" "):
        el = s.select_one(sel)
        return re.sub(r"\s+", " ", el.get_text(sep)).strip() if el else ""

    title = txt("#productTitle") or txt("h1#title") or txt("span#productTitle")
    bullets = []
    for li in s.select("#feature-bullets li span.a-list-item"):
        t = re.sub(r"\s+", " ", li.get_text(" ")).strip()
        if t and t not in bullets:
            bullets.append(t)
    if not bullets:
        bullets = [re.sub(r"\s+", " ", li.get_text(" ")).strip()
                   for li in s.select("#feature-bullets li") if li.get_text(strip=True)]
    if not bullets:
        for li in s.select("#productFactsDesktopExpander li, #productFactsDesktop_feature_div li, "
                           "div[data-feature-name='productFactsDesktop'] li"):
            t = re.sub(r"\s+", " ", li.get_text(" ")).strip()
            if t and t not in bullets:
                bullets.append(t)
    desc = txt("#productDescription") or txt("#aplus_feature_div") or txt("#bookDescription_feature_div")

    crumbs = [re.sub(r"\s+", " ", a.get_text()).strip()
              for a in s.select("#wayfinding-breadcrumbs_container a, #wayfinding-breadcrumbs_feature_div a, "
                                ".a-breadcrumb a, #nav-subnav .nav-a-content")]
    crumbs = [c for c in dict.fromkeys(crumbs) if c]
    if not crumbs:
        bc = s.select_one("#wayfinding-breadcrumbs_container, #wayfinding-breadcrumbs_feature_div")
        if bc:
            crumbs = [x.strip() for x in bc.get_text(" ").split() if x.strip()]

    # 结构化数据兜底（Amazon 页面基本都带 JSON-LD，比 CSS 选择器稳）
    ld_brand, ld_cat = "", ""
    for sc in s.select("script[type='application/ld+json']"):
        try:
            data = json.loads(sc.string or "{}")
        except Exception:                          # noqa: BLE001
            continue
        for node in (data if isinstance(data, list) else [data]):
            if not isinstance(node, dict):
                continue
            if node.get("@type") == "Product":
                b = node.get("brand")
                if isinstance(b, dict):
                    b = b.get("name")
                ld_brand = ld_brand or (b or "")
                cp = node.get("category") or ""
                if cp:
                    ld_cat = ld_cat or re.sub(r"\s+", " ", str(cp)).strip()
            if node.get("@type") == "BreadcrumbList":
                items = sorted(node.get("itemListElement") or [],
                               key=lambda x: x.get("position", 0))
                names = [i.get("name") or (i.get("item") or {}).get("name") for i in items]
                ld_cat = ld_cat or " > ".join([n for n in names if n])
    if not crumbs and ld_cat:
        crumbs = [x.strip() for x in re.split(r"\s*>\s*", ld_cat) if x.strip()]

    brand = (txt("#bylineInfo") or txt("a#bylineInfo") or txt("tr.po-brand td.a-span9")
             or txt("#brand") or txt("a.contributorNameID") or ld_brand)
    brand = re.sub(r"^(Visit the |Brand:\s*)", "", brand).replace(" Store", "").strip()

    detail = (txt("#detailBullets_feature_div") + " " + txt("#productDetails_detailBullets_sections1")
              + " " + txt("#productDetails_techSpec_section_1") + " " + txt("#detailBulletsWrapper_feature_div"))
    bsr = ""
    m = re.search(r"#([\d,]+)\s+in\s+([A-Za-z &]+)", detail)
    if not m:
        m = re.search(r"#([\d,]+)\s+in\s+([A-Za-z &]{2,40})",
                      re.sub(r"\s+", " ", s.get_text(" ")))
    if m:
        bsr = f"#{m.group(1)} in {m.group(2).strip()}"

    price_raw = ""
    for sel in (".a-price .a-offscreen", "#corePrice_feature_div .a-offscreen",
                "#corePriceDisplay_desktop_feature_div .a-offscreen", "#priceblock_ourprice",
                "span.priceToPay .a-offscreen", "#apex_desktop .a-offscreen"):
        price_raw = txt(sel)
        if price_raw:
            break
    currency = ""
    cm = re.search(r"(US\$|S\$|C\$|A\$|CDN\$|AU\$|€|£|¥|￥)", price_raw)
    if cm:
        currency = cm.group(1)

    return {
        "asin": asin, "url": url, "title": title,
        "bullets": bullets[:8], "description": desc,
        "category": " > ".join(crumbs), "brand": brand, "bsr": bsr,
        "price_raw": price_raw, "currency": currency,
    }


def listing_text(l: dict) -> str:
    """把 Listing 拼成喂给 Jev 的 state 文本"""
    parts = [
        f"商品 ASIN：{l.get('asin','')}",
        f"标题：{l.get('title','')}",
        f"品牌：{l.get('brand','')}",
        f"类目：{l.get('category','')}",
    ]
    if l.get("bullets"):
        parts.append("五点描述：\n" + "\n".join(f"- {b}" for b in l["bullets"]))
    if l.get("description"):
        parts.append("商品描述：" + l["description"][:2500])
    return "\n".join(p for p in parts if p.split("：", 1)[-1].strip())


def currency_warning(l: dict, expected="US$") -> str | None:
    cur = l.get("currency") or ""
    if cur and cur != expected:
        return (f"⚠️  抓到的是 {cur} 计价（不是 {expected}）——网络可能走了海外节点。"
                f"价格与关键词相关度无关，但别拿它做定价判断。")
    return None


def load_local(path: Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data if isinstance(data, list) else [data]
