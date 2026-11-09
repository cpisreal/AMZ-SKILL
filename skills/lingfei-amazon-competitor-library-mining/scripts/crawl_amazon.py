#!/usr/bin/env python3
"""Amazon 抓取层：限速 + 反爬熔断 + 断点续跑 + 页面留证。

三条纪律（这是整条流水线最容易被封的一环）：
  1. 慢 —— 每次请求之间随机 sleep（默认 5-9 秒），绝不并发。
  2. 停 —— 一旦命中验证码/机器人页，立刻熔断抛异常，不再继续打。
  3. 留证 —— 每个页面原文落盘到 pages/，既为断点续跑，也为回溯复算。

用法（库）：
    from crawl_amazon import ThrottledSession, parse_search, parse_bsr, parse_detail
"""
import hashlib
import json
import os
import random
import re
import time

import httpx
from bs4 import BeautifulSoup

# 代理优先级：AMZ_PROXY → HTTPS_PROXY → 直连。不写死任何地址（对外分享包要求）。
PROXY = (os.environ.get("AMZ_PROXY") or os.environ.get("HTTPS_PROXY") or "").strip() or None
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36")

# 强制美国站币种 —— 否则会按出口 IP 所在国显示（实测代理出口新加坡会回 S$）
COOKIES = {"i18n-prefs": "USD", "lc-main": "en_US"}

BLOCK_SIGNS = [
    "enter the characters you see below",
    "to discuss automated access to amazon data",
    "api-services-support@amazon.com",
    "sorry, we just need to make sure you're not a robot",
    "type the characters you see in this image",
]

# 软验证：amazon 的 bm-verify 中继页（5 秒后 meta refresh 回原 URL）。
# 不熔断，但必须：① 等它跳 ② 复用同一连接/cookie 重试一次。
SOFT_SIGNS = ["bm-verify", "meta http-equiv=\"refresh\""]

# 正常页面长度下限（小于这个 = 空壳/挑战页）
MIN_HTML_LEN = 60000


class Blocked(Exception):
    """命中反爬 —— 调用方必须立即停止，不要重试。"""


class SoftChallenge(Exception):
    """命中软验证（bm-verify）—— 等待后同连接重试。"""


def is_blocked(html: str) -> bool:
    low = html[:200000].lower()
    return any(s in low for s in BLOCK_SIGNS)


def is_soft_challenge(html: str) -> bool:
    return len(html) < MIN_HTML_LEN and (
        "bm-verify" in html or ("refresh" in html.lower() and "noindex" in html.lower())
    )


class ThrottledSession:
    """限速 + 熔断 + 落盘的抓取会话。"""

    def __init__(self, cache_dir="pages", min_delay=5.0, max_delay=9.0,
                 timeout=40, max_requests=600, verbose=True, warmup=True):
        self.cache_dir = cache_dir
        self.min_delay, self.max_delay = min_delay, max_delay
        self.timeout = timeout
        self.max_requests = max_requests
        self.verbose = verbose
        self.n = 0
        self.cache_hits = 0
        self.soft_hits = 0
        os.makedirs(cache_dir, exist_ok=True)
        # 🔴 关键：持久连接 + cookie jar。每次新建连接（"打开太快关太快"）
        # 正是触发 bm-verify 反爬的主因；保持一个会话能大幅降低挑战率。
        self.client = httpx.Client(
            proxy=PROXY, timeout=timeout, follow_redirects=True,
            headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"},
            cookies=dict(COOKIES),
        )
        # 预热：像真人一样先访问首页，拿到 session-id 之类的基础 cookie
        if warmup:
            try:
                self.client.get("https://www.amazon.com/")
                self.n += 1
                self._log("  [warmup] 首页握手完成")
            except Exception as e:
                self._log(f"  [warmup] 失败（继续）：{type(e).__name__}")

    def _key(self, url: str) -> str:
        return hashlib.sha1(url.encode()).hexdigest()[:16]

    def _log(self, msg):
        if self.verbose:
            print(msg, flush=True)

    def get(self, url: str, label: str = "") -> str:
        """取页面 HTML。命中【有效】缓存直接返回（不发请求）。"""
        path = os.path.join(self.cache_dir, self._key(url) + ".html")
        meta = os.path.join(self.cache_dir, self._key(url) + ".url")
        if os.path.exists(path):
            cached = open(path, encoding="utf-8", errors="ignore").read()
            if len(cached) >= MIN_HTML_LEN:          # 空壳/挑战页缓存视为无效
                self.cache_hits += 1
                self._log(f"  [cache] {label or url[:70]}")
                return cached

        if self.n >= self.max_requests:
            raise RuntimeError(f"达到请求上限 {self.max_requests}，停手（防封）")

        for attempt in range(4):
            wait = random.uniform(self.min_delay, self.max_delay)
            self._log(f"  [sleep {wait:4.1f}s] {label or url[:70]}"
                      + (f"  (第 {attempt+1} 次)" if attempt else ""))
            time.sleep(wait)
            try:
                r = self.client.get(url)
                self.n += 1
                if is_blocked(r.text):
                    raise Blocked(f"命中反爬验证码：{url[:90]}")
                if is_soft_challenge(r.text):
                    self.soft_hits += 1
                    self._log(f"  ⚠️ 软验证(bm-verify) 第{attempt+1}次 → 等 8s 同连接重试")
                    time.sleep(8)                    # 等它 meta refresh 窗口过去
                    continue
                if r.status_code == 503:
                    time.sleep(20 * (attempt + 1))
                    continue
                r.raise_for_status()
                if len(r.text) < MIN_HTML_LEN:
                    self._log(f"  ⚠️ 页面过短（{len(r.text)}B），视为异常重试")
                    continue
                open(path, "w", encoding="utf-8").write(r.text)
                open(meta, "w", encoding="utf-8").write(url)
                return r.text
            except Blocked:
                raise
            except httpx.HTTPError as e:
                self._log(f"  ⚠️ {type(e).__name__}: {e}")
                time.sleep(8 * (attempt + 1))
        raise RuntimeError(f"抓取失败（含软验证重试）：{url[:90]}")


# ---------------- 解析 ----------------

def _num(s):
    if not s:
        return None
    s = re.sub(r"[^\d.]", "", s.replace(",", ""))
    try:
        return float(s) if s else None
    except ValueError:
        return None


def parse_price(s):
    """解析价格。

    ⚠️ 坑：带上 `i18n-prefs=USD` cookie 强制美元后，amazon 会把金额渲染成
    **不带小数点的「分」**（实测 `$3999` = $39.99、`$5143` = $51.43）。
    带小数点时按原值，无小数点且 ≥3 位数字时按分处理。
    """
    if not s:
        return None
    t = re.sub(r"[^\d.]", "", s.replace(",", ""))
    if not t:
        return None
    try:
        if "." in t:
            return float(t)
        if len(t) >= 3:
            return round(float(t) / 100, 2)
        return float(t)
    except ValueError:
        return None


def _brand_from(soup, html: str, title: str | None):
    """品牌三重兜底：byline 链接 → 页面文本 `Brand: X` → 标题首词。"""
    e = soup.select_one("#bylineInfo")
    if e:
        t = re.sub(r"\s+", " ", e.get_text(" ")).strip()
        t = t.replace("Visit the ", "").replace(" Store", "").replace("Brand:", "").strip()
        if t:
            return t
    m = re.search(r"Brand\s*[:：]\s*([A-Za-z0-9][A-Za-z0-9 \-&\.]{1,28})",
                  re.sub(r"\s+", " ", soup.get_text(" ")))
    if m:
        cand = m.group(1).strip()
        for stop in (" Model", " Product", " Color", " Item", " Included", " Dimensions"):
            if stop in cand:
                cand = cand.split(stop)[0].strip()
        if cand:
            return cand
    if title:
        w = title.split()[0]
        if w.lower() not in {"ice", "the", "new", "countertop", "portable", "nugget", "amazon"}:
            return w
    return None


def parse_search(html: str) -> list[dict]:
    """搜索结果页 → 商品卡片列表。

    只抽「发现层」需要的字段（ASIN/位次/标题/是否广告）。
    品牌、类目、五点这些要去详情页拿（见 parse_detail），
    因为 SERP 卡片里的「品牌位」实测常被配送日期 / Amazon's Choice 角标污染。
    """
    soup = BeautifulSoup(html, "lxml")
    out = []
    for pos, div in enumerate(soup.select("div[data-asin][data-component-type='s-search-result']"), 1):
        asin = div.get("data-asin")
        if not asin or len(asin) != 10:
            continue
        t = div.select_one("h2 span") or div.select_one("h2 a span") or div.select_one("h2")
        title = re.sub(r"\s+", " ", t.get_text(" ")).strip() if t else None
        if not title:
            continue
        p = div.select_one("div[data-cy='price-recipe'] span.a-offscreen") or \
            div.select_one("span.a-price span.a-offscreen")
        price = parse_price(p.get_text()) if p else None
        r = div.select_one("span.a-icon-alt")
        rating = _num(r.get_text().split()[0]) if r else None
        rv = div.select_one("span[aria-label][class*='s-underline-text']") or \
            div.select_one("a[aria-label*='rating'] span") or \
            div.select_one("span.a-size-base.s-underline-text")
        reviews = _num(rv.get_text()) if rv else None
        spon = div.select_one("span.s-label-popover-default, span.puis-label-popover-default") is not None
        out.append({"asin": asin, "pos": pos, "title": title,
                    "price": price, "rating": rating, "reviews": reviews,
                    "sponsored": bool(spon)})
    return out


def parse_bsr(html: str) -> list[dict]:
    """BSR 榜页 → 榜单商品列表（带排名）。"""
    soup = BeautifulSoup(html, "lxml")
    out, seen = [], set()
    for div in soup.select("div[id^='gridItemRoot'], div.zg-grid-general-faceout, div.p13n-sc-uncoverable-faceout"):
        a = div.select_one("a[href*='/dp/']")
        if not a:
            continue
        m = re.search(r"/dp/([A-Z0-9]{10})", a.get("href", ""))
        if not m or m.group(1) in seen:
            continue
        aid = m.group(1)
        seen.add(aid)
        rk = div.select_one("span.zg-bdg-text") or div.select_one("span.zg-badge-text")
        t = div.select_one("div[class*='_cDEzb_p13n-sc-css-line-clamp'], span > div")
        out.append({"asin": aid, "rank_text": rk.get_text(strip=True) if rk else None,
                    "title": re.sub(r"\s+", " ", t.get_text(" ")).strip()[:160] if t else None})
    return out


def parse_detail(html: str) -> dict:
    """详情页 → 结构化 Listing（标题/品牌/类目/价格/评分/五点/BSR）。"""
    soup = BeautifulSoup(html, "lxml")

    def one(sel):
        e = soup.select_one(sel)
        return re.sub(r"\s+", " ", e.get_text(" ")).strip() if e else None

    crumbs = [a.get_text(strip=True) for a in
              soup.select("#wayfinding-breadcrumbs_feature_div a")]
    body = re.sub(r"\s+", " ", soup.get_text(" "))
    bsr = None
    m = re.search(r"Best Sellers Rank\s*(.{0,220})", body)
    if m:
        bsr = m.group(1)[:220]
    bullets = [re.sub(r"\s+", " ", li.get_text(" ")).strip()
               for li in soup.select("#feature-bullets li")]
    bullets = [b for b in bullets if b][:6]
    title = one("#productTitle")
    return {
        "title": title,
        "brand": _brand_from(soup, html, title),
        "category": " > ".join(crumbs) if crumbs else None,
        "price": parse_price(one("span.a-price span.a-offscreen")),
        "rating": _num((one("#acrPopover") or "").split()[0]) if one("#acrPopover") else None,
        "bullets": bullets,
        "bsr_text": bsr,
    }


def extract_bsr_node(html: str) -> str | None:
    """从详情页里找最细一级 BSR 类目节点 ID（用于爬榜单）。"""
    soup = BeautifulSoup(html, "lxml")
    m = re.search(r"/gp/bestsellers/[a-z\-]+/(\d+)", html)
    return m.group(1) if m else None
