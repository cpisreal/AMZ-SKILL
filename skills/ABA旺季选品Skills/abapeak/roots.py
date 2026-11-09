# -*- coding: utf-8 -*-
"""口径 ①：词根匹配边界。

**为什么不能用 `LIKE '%men%'`**：那会命中 `women`、`women's`、`omen`、`garment`、`amendment`。
一个词根越短，噪音越大 —— 这是整套分析里最容易静默出错的一步（结果看着像对的，其实混进了别的品类）。

正确做法：**词边界匹配**。

🔴 **RE2 陷阱（真踩过）**：DuckDB 的 `regexp_matches` 用的是 **RE2**，
**不支持 lookbehind `(?<!...)` 和 lookahead `(?=...)`** —— 写了会直接
`Invalid Input Error: invalid perl operator: (?<`。

所以边界必须写成**消费式**字符类：
    前后不是字母  →  `(^|[^a-z])` … `([^a-z]|$)`
而不是 `(?<![a-z])` … `(?![a-z])`。

> 消费式写法会不会漏掉相邻的第二次出现？会（引擎从上次 match.end() 继续扫），
> 但**布尔判定永远正确** —— 只要词里出现过一次就算命中，而我们要的正是布尔值。
> 只有「统计出现次数」才会受影响，本工具不做这件事。

同一个 pattern 字符串同时喂给 DuckDB 和 Python `re`，保证两边口径一致。
"""
from __future__ import annotations

import re

# 复数后缀：s / es
_PLURAL = r"(?:s|es)?"
# 词根长度 >= 这个值 → 认定"作为前缀很安全"，只查左边界
PREFIX_SAFE_MIN = 6


def _root_pattern(root: str, boundary: str) -> str:
    esc = re.escape(root).replace(r"\ ", r"[\s\-]+")
    body = esc + _PLURAL
    if boundary == "loose":
        return body
    if boundary == "left":
        return r"(^|[^a-z])" + body
    return r"(^|[^a-z])" + body + r"([^a-z]|$)"     # both


def resolve_boundary(root: str, mode: str, override=None) -> str:
    """决定某个词根用哪种边界。

    🔴 **两边都查（both）会把正当词也剔掉** —— 实测 `christmaslights`、
    `christmastime`、`3 ftchristmas tree`、`christmasdecor` 这类**连写搜索词**
    都是有真实商业价值的，被 both 一刀切掉。

    而真正要防的假命中（`boxmasters` 里嵌着 `xmas`、`women`/`omen`/`garment` 里嵌着 `men`）
    **左边一个字符是字母就够挡了** —— 所以左边界才是主力。

    右边界只对**短词根**才必要（防止把 `men` 当成 `menswear`/`mental`/`mention` 的前缀）。
    默认规则：词根长度 >= PREFIX_SAFE_MIN(6) → 只查左边界；更短的 → 两边都查。
    """
    if mode == "loose":
        return "loose"
    if override:
        return override
    if mode == "strict":
        return "both"
    return "left" if len(root) >= PREFIX_SAFE_MIN else "both"


def build_pattern(roots, mode: str = "auto", boundaries=None) -> str:
    """把词根列表编成一个 RE2 兼容的 regex（DuckDB 与 Python 通用）。

    mode:
      "auto"   （默认）长词根只查左边界、短词根两边都查 —— 推荐
      "strict" 一律两边都查 —— 会剔掉 christmaslights 这类连写词，慎用
      "loose"  不查边界，等价 `LIKE '%root%'` —— 只用来复现别人用 LIKE 算的数
    boundaries: 可选 dict，{词根: "left"|"both"|"loose"} 逐词根覆盖。

    >>> build_pattern(["christmas"], mode="auto")
    '(^|[^a-z])(?:christmas)(?:s|es)?'
    >>> build_pattern(["men"], mode="auto")
    '(^|[^a-z])(?:men)(?:s|es)?([^a-z]|$)'
    """
    if isinstance(roots, str):
        roots = [r for r in roots.split(",")]
    boundaries = boundaries or {}
    alts = []
    for r in roots:
        r = (r or "").strip().lower()
        if not r:
            continue
        b = resolve_boundary(r, mode, boundaries.get(r))
        alts.append(_root_pattern(r, b))
    if not alts:
        raise ValueError("roots 里没有有效词")
    if len(alts) == 1:
        return alts[0]
    # 多个词根各自带不同边界 → 直接并列（本工具只做布尔判定，消费边界字符无副作用）
    return "|".join(alts)


def build_where(column_sql: str, roots, mode: str = "auto", boundaries=None) -> str:
    """给 SQL 用的 WHERE 片段（column_sql 是已经加好双引号的列名）。"""
    return (f"regexp_matches(lower({column_sql}), "
            f"'{build_pattern(roots, mode, boundaries)}')")


def make_matcher(roots, mode: str = "auto", boundaries=None):
    """返回 term -> bool 的 Python 判定函数（与 SQL 侧同 pattern）。"""
    rx = re.compile(build_pattern(roots, mode, boundaries))
    return lambda term: bool(rx.search((term or "").lower()))


def explain(roots, mode: str = "auto", samples=None) -> str:
    """打印词根闸门的正反例。samples 可由规则包用 `_root_probes` 覆盖。"""
    rx = re.compile(build_pattern(roots, mode))
    if samples is None:
        samples = ["christmas tree", "christmaslights", "christmastime", "christmas-tree",
                   "3 ftchristmas tree", "boxmasters",            # ← 含 xmas 的真假命中
                   "women pajamas", "omen decor", "garment steamer", "menswear"]
    lines = [f"词根 {roots}　口径 {mode}", f"pattern  {build_pattern(roots, mode)}", ""]
    for s in samples:
        lines.append(f"  {'✅ 命中' if rx.search(s) else '⛔ 不命中'}  {s}")
    return "\n".join(lines)
