#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""采集：零注册搜索（ddgs）+ Reddit 归档（Arctic Shift）拉帖子与评论。

隐私与可移植性：
  - 代理走环境变量 HTTPS_PROXY / HTTP_PROXY（用户自己配置科学上网，脚本不内置任何代理）。
  - 无任何硬编码路径、用户名、key。
  - 输出到调用方指定的目录。
"""
import json
import os
import sys
import time
import urllib.request
import urllib.parse

ARCTIC_BASE = "https://arctic-shift.photon-reddit.com/api"

# 默认通用社区（可被 --subreddits 覆盖）
DEFAULT_SUBS = ["BuyItForLife", "Frugal", "AskReddit"]


def arctic(path, params, timeout=30):
    """请求 Arctic Shift，自动走环境变量代理。返回 (data, error)。"""
    url = ARCTIC_BASE + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "reddit-voice-mining/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode())
            return body.get("data"), body.get("error")
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def ddgs_search(query, max_results=8, timeout=20):
    """零注册搜索。代理走环境变量。"""
    from ddgs import DDGS
    out = []
    try:
        with DDGS(timeout=timeout) as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                out.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
    except Exception as e:  # noqa: BLE001
        print(f"  [搜索失败] {query}: {str(e)[:80]}", flush=True)
    return out


def expand_reddit_queries(keyword):
    """把品类词展开成多角度 Reddit 检索词（通用，跨品类）。"""
    return [
        keyword,                      # 品类词本身
        f"best {keyword}",            # 推荐
        f"{keyword} worth it",        # 决策
        f"{keyword} problem",         # 痛点
        f"{keyword} review",          # 评测
    ]


def collect(keyword, subreddits, limit, n_queries, out_dir):
    """采集全流程，返回数据字典。"""
    os.makedirs(out_dir, exist_ok=True)
    queries = expand_reddit_queries(keyword)
    print(f"[1/3] 采集 Reddit（subreddit={len(subreddits)} × 查询={len(queries)}）", flush=True)

    posts = {}
    n_req = 0
    for sub in subreddits:
        for q in queries:
            data, err = arctic("/posts/search",
                               {"subreddit": sub, "query": q, "limit": limit, "sort": "desc"})
            n_req += 1
            if err:
                print(f"  [跳过] r/{sub} '{q}': {str(err)[:60]}", flush=True)
            for p in (data or []):
                pid = p.get("id")
                if not pid or pid in posts:
                    continue
                posts[pid] = {
                    "id": pid,
                    "subreddit": p.get("subreddit"),
                    "title": p.get("title", ""),
                    "selftext": (p.get("selftext") or "")[:2000],
                    "num_comments": p.get("num_comments", 0),
                    "score": p.get("score", 0),
                }
            time.sleep(0.8)
            if n_req % 15 == 0:
                print(f"  ...{n_req} 请求，累计帖子 {len(posts)}", flush=True)

    # 拉评论
    total_comments = 0
    for i, (pid, p) in enumerate(posts.items()):
        if p["num_comments"] <= 0:
            p["comments"] = []
            continue
        data, _ = arctic("/comments/search", {"link_id": "t3_" + pid, "limit": 100})
        comments = []
        for c in (data or []):
            body = (c.get("body") or "").strip()
            if body:
                comments.append({"author": c.get("author"), "score": c.get("score", 0), "body": body[:1500]})
        p["comments"] = comments
        total_comments += len(comments)
        time.sleep(0.5)
        if (i + 1) % 25 == 0:
            print(f"  ...拉评论 {i+1}/{len(posts)}，累计 {total_comments}", flush=True)

    print(f"  Reddit 完成：帖子 {len(posts)}，评论 {total_comments}", flush=True)

    # ddgs 行业侧搜索
    print(f"[2/3] 采集行业侧搜索（{n_queries} 个角度）", flush=True)
    industry_queries = [
        f"best {keyword} 2026",
        f"{keyword} market size",
        f"{keyword} brands",
        f"{keyword} problems",
        f"{keyword} trend",
    ][:n_queries]
    search_results = []
    for q in industry_queries:
        hits = ddgs_search(q)
        for h in hits:
            h["query"] = q
        search_results.extend(hits)
        time.sleep(0.8)

    # 结果自检：防止静默失败
    if len(posts) == 0:
        print("  ⚠️ 警告：Reddit 帖子为 0。请检查代理是否生效（HTTPS_PROXY）或关键词是否正确。", flush=True)

    print(f"[3/3] 保存数据", flush=True)
    result = {
        "keyword": keyword,
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "posts": list(posts.values()),
        "search_results": search_results,
        "stats": {
            "total_posts": len(posts),
            "total_comments": total_comments,
            "total_search": len(search_results),
        },
    }
    path = os.path.join(out_dir, "data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"  已保存 {path}（{os.path.getsize(path)/1024:.0f} KB）", flush=True)
    return result


if __name__ == "__main__":
    kw = sys.argv[1] if len(sys.argv) > 1 else "cat food"
    subs = DEFAULT_SUBS
    limit = 15
    n_q = 5
    out = "output"
    collect(kw, subs, limit, n_q, out)
