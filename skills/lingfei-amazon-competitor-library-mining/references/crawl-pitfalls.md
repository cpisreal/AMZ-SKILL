# Amazon 抓取：反爬与解析坑（实测记录）

实测环境：2026-10，抓 `amazon.com` 详情页 / BSR 榜 / 搜索结果页共 141 次请求。

---

## 1. `bm-verify` 软验证页 —— 最容易误判的坑

**现象**：搜索页只返回 ~2,274 字节，解析器抽出 0 个商品。看起来像「选择器写错了」。

**真身**：

```html
<meta http-equiv="refresh" content="5; URL='/s?k=...&bm-verify=AAQAAAAO...'">
```

这是一个 **5 秒后自动跳回原 URL** 的中继页，不是验证码。因为熔断器只认「enter the characters you see below」这类硬验证码文案，它会**悄悄漏过去**。

**判据**（长度必须一起判，否则会误伤正常短页）：

```python
def is_soft_challenge(html):
    return len(html) < 60000 and ("bm-verify" in html
                                  or ("refresh" in html.lower() and "noindex" in html.lower()))
```

**处理**：等 ~8 秒，用**同一个连接**重试原 URL（cookie 要保住）。不要换新连接 —— 换新连接经常又吃一次挑战。

---

## 2. 「打开太快、关页面太快」= 反爬触发的真因

**错误做法**：每次请求 `httpx.get(...)`，即用即弃。每个请求一个新 TLS 连接、无 cookie 延续。
对 amazon 来说这几乎就是「脚本特征」。

**正确做法**：

```python
client = httpx.Client(proxy=PROXY, cookies={"i18n-prefs": "USD", "lc-main": "en_US"},
                      headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"},
                      follow_redirects=True, timeout=40)
client.get("https://www.amazon.com/")      # 预热：像真人一样先落首页拿 cookie
```

**实测效果**：改成持久连接 + 预热后，**141 次请求 0 次软验证**；改之前单次小样就吃了一次。

**节奏**：每次真实请求前随机 sleep **5–8 秒**，绝不并发。宁可慢，不要断。

---

## 3. 代理出口决定币种 / 能否取到 BSR

**现象**：同一个 `amazon.com/dp/...` 页面，价格显示 `S$190.28`（出口在新加坡时）。

**修法**：加 cookie 强制美元：

```python
cookies = {"i18n-prefs": "USD", "lc-main": "en_US"}
```

**注意**：直连（不走代理）在部分网络下会 `SSL: UNEXPECTED_EOF_WHILE_READING`，此时必须走代理。
把代理做成环境变量（`AMZ_PROXY`），不要写死在代码里。

---

## 4. 美元价格是「分」为单位渲染 —— 最危险的静默错误

强制美元后，amazon 把金额渲染成**不带小数点的分**：

| 页面文本 | 真实价格 |
|---|---|
| `$3999` | **$39.99** |
| `$5143` | **$51.43** |
| `$49999` | **$499.99** |

不修的话，结论会变成「一个台面制冰机卖 5,143 美金」——而**所有下游分析都会跟着错**，且不会报任何错。

```python
def parse_price(s):
    t = re.sub(r"[^\d.]", "", s.replace(",", ""))
    if "." in t:            # 有小数点 → 原值
        return float(t)
    if len(t) >= 3:         # 无小数点且 ≥3 位 → 按分
        return round(float(t) / 100, 2)
    return float(t)
```

⚠️ 边界：若某商品价格恰好是 `$999`（真·三位数整数价格）会被误判成 $9.99。这类类目里极少见，
但如果做高价值品类要额外交叉核对（例如用详情页 JSON 里的 `priceAmount`）。

---

## 5. 解析选择器实测结论

| 目标 | 可用选择器 | 备注 |
|---|---|---|
| 搜索结果条目 | `div[data-asin][data-component-type='s-search-result']` | 每页 ~22 条；要有 `data-asin` 且长度 10 |
| SERP 标题 | `h2 span` | — |
| SERP 是否广告 | `span.s-label-popover-default` | — |
| SERP 品牌位 | ❌ **不可用** | 常被「配送日期」「Amazon's Choice」污染 |
| BSR 榜条目 | `div[id^='gridItemRoot']` 等 | 一页只给 **30 条**，翻页用 `?pg=2` |
| BSR 排名 | `span.zg-bdg-text`（`#1` 这种） | 部分条目无排名元素，需容错 |
| 详情页标题 | `#productTitle` | — |
| 详情页品牌 | `#bylineInfo`（`Visit the X Store`） | 兜底：页面文本 `Brand: X` → 标题首词 |
| 详情页 BSR 类目节点 | 正则 `/gp/bestsellers/[a-z\-]+/(\d+)` | 拿来爬榜单 |
| 详情页五点 | `#feature-bullets li` | — |

**类目面包屑**：`#wayfinding-breadcrumbs_feature_div a`。

---

## 6. 观察到的其他现象

- 详情页里「Best Sellers Rank」可能同时列**两个**层级（如 `#5 in Appliances` 与 `#5 in Ice Makers`），
  解析时要取**最细的那个**对应节点。
- 详情页 BSR 文本里的排名与 BSR 榜页上的排名**可能对不上**（页面各自更新节奏不同）。
  要「排名」就用榜页；要「类目节点」才用详情页。
- 同一 ASIN 会在**多个关键词 × 多页**里重复出现。实测 609 条原始命中 → 272 个唯一 ASIN，**重复率 55.3%**。
  「被几个词命中」本身就是很强的竞品强度信号（实测 272 个里只有 82 个被 ≥3 次命中）。
