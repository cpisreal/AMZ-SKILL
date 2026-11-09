#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_uk_snow.py — 美国 12 城未来 7 天降雪 / 最低温抓取器

数据源：Open-Meteo 免费 API（无需 API Key）
    https://api.open-meteo.com/v1/forecast
参数：
    daily=snowfall_sum,temperature_2m_min
    temperature_unit=fahrenheit
    timezone=America/New_York  (逐城市各自时区，见 references/us_locations.md)

输出：
    JSON 到 stdout（同时写入 --out 指定文件），结构见 SKILL.md「脚本输出契约」

说明：
    文件名沿用 fetch_uk_snow.py 以兼容既有定时任务；脚本内部已切到美国站 12 城。
    「英国站」相关字样仅为历史命名，不代表本脚本抓取英国数据。

用法：
    python fetch_uk_snow.py                     # 输出到 stdout + 默认状态文件
    python fetch_uk_snow.py --out data/today.json
    python fetch_uk_snow.py --state-dir .state  # 指定昨日快照目录
    python fetch_uk_snow.py --offline            # 不发网络请求，用上次快照自检解析逻辑
"""

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

# ---------------------------------------------------------------------------
# 城市清单（12 城）。lat/lon 见 references/us_locations.md，保持两处一致。
# ---------------------------------------------------------------------------
CITIES = [
    {"name": "New York",        "state": "NY", "lat": 40.7128, "lon": -74.0060, "tz": "America/New_York",    "weight": 1.0},
    {"name": "Chicago",         "state": "IL", "lat": 41.8781, "lon": -87.6298, "tz": "America/Chicago",     "weight": 1.2},
    {"name": "Denver",          "state": "CO", "lat": 39.7392, "lon": -104.9903, "tz": "America/Denver",     "weight": 1.0},
    {"name": "Minneapolis",     "state": "MN", "lat": 44.9778, "lon": -93.2650, "tz": "America/Chicago",     "weight": 1.3},
    {"name": "Boston",          "state": "MA", "lat": 42.3601, "lon": -71.0589, "tz": "America/New_York",    "weight": 1.1},
    {"name": "Detroit",         "state": "MI", "lat": 42.3314, "lon": -83.0458, "tz": "America/Detroit",     "weight": 1.1},
    {"name": "Cleveland",       "state": "OH", "lat": 41.4993, "lon": -81.6944, "tz": "America/New_York",    "weight": 1.0},
    {"name": "Pittsburgh",      "state": "PA", "lat": 40.4406, "lon": -79.9959, "tz": "America/New_York",    "weight": 1.0},
    {"name": "Milwaukee",       "state": "WI", "lat": 43.0389, "lon": -87.9065, "tz": "America/Chicago",     "weight": 1.0},
    {"name": "Buffalo",         "state": "NY", "lat": 42.8864, "lon": -78.8784, "tz": "America/New_York",    "weight": 1.1},
    {"name": "Salt Lake City",  "state": "UT", "lat": 40.7608, "lon": -111.8910, "tz": "America/Denver",     "weight": 0.9},
    {"name": "Anchorage",       "state": "AK", "lat": 61.2181, "lon": -149.9003, "tz": "America/Anchorage",  "weight": 0.7},
]

API = "https://api.open-meteo.com/v1/forecast"
DAYS = 8                 # 取 8 天：丢掉已发生的「今天」，只留未来 7 天
WINDOW = 7
# 阶段判定阈值（与 SKILL.md 保持一致，改一处必须改另一处）
SNOW_ANY_IN = 0.1        # 英寸：>0.1 视为「有雪日」
COLD_BURST_F = 20.0      # °F：多城最低温 <= 20 即爆发期
COLD_BURST_CITY_N = 2    # 「多城」的门槛城市数
DROP_ALERT_F = 5.0       # °F：任一城市较昨日跌 >= 5 即临门期
WARM_BACK_F = 10.0       # °F：未来 3 天逐日回升且累计 >= 10 即回暖


def sf(v, nd=1):
    """安全 float"""
    try:
        return round(float(v), nd)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 气候基准：12 城逐月「平均最低温」°F（1991-2020 NOAA/NCEI 气候常年值，取整）
# 用途：估算「距寒冷高峰还有几周」——加热垫需求高峰 ≈ 1 月（全年最低温月）
# 若启用 live 模式，脚本会用 Open-Meteo Archive 覆盖此表（见 --live-climate）
# ---------------------------------------------------------------------------
CLIMATE_TMIN_F = {
    #                 J   F   M   A   M   J   J   A   S   O   N   D
    "New York":      [27, 29, 35, 44, 54, 64, 69, 68, 61, 50, 41, 32],
    "Chicago":       [22, 26, 34, 44, 54, 64, 69, 68, 60, 48, 37, 27],
    "Denver":        [18, 20, 26, 32, 42, 51, 58, 56, 47, 35, 25, 18],
    "Minneapolis":   [8, 13, 24, 36, 48, 58, 63, 61, 52, 39, 26, 13],
    "Boston":        [24, 26, 32, 41, 50, 60, 66, 65, 57, 47, 38, 29],
    "Detroit":       [20, 22, 29, 39, 49, 59, 64, 62, 54, 43, 33, 24],
    "Cleveland":     [23, 25, 31, 41, 51, 60, 65, 64, 57, 46, 37, 28],
    "Pittsburgh":    [22, 24, 30, 39, 48, 57, 62, 61, 54, 43, 34, 26],
    "Milwaukee":     [16, 20, 28, 38, 47, 57, 63, 62, 54, 42, 31, 21],
    "Buffalo":       [19, 20, 26, 36, 47, 57, 62, 61, 54, 43, 33, 25],
    "Salt Lake City":[23, 27, 34, 40, 48, 56, 63, 62, 52, 41, 30, 23],
    "Anchorage":     [9, 11, 17, 27, 37, 46, 52, 49, 41, 28, 16, 11],
}
PEAK_MONTH = 1           # 需求高峰月（全年最冷月）
WEEKS_PER_MONTH = 4.345


def climate_normals(live=False, timeout=25):
    """返回 {city: [12 个月平均最低温]}。live=True 时用 Open-Meteo Archive 拉最近 5 年实测。"""
    if not live:
        return dict(CLIMATE_TMIN_F)
    out = {}
    for city in CITIES:
        q = (
            "https://archive-api.open-meteo.com/v1/archive"
            f"?latitude={city['lat']}&longitude={city['lon']}"
            "&start_date=2020-01-01&end_date=2024-12-31"
            "&daily=temperature_2m_min&temperature_unit=fahrenheit"
            f"&timezone={urllib.parse.quote(city['tz'])}"
        )
        try:
            req = urllib.request.Request(q, headers={"User-Agent": "heating-pad-skill/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = json.loads(r.read().decode("utf-8"))
            dates = raw["daily"]["time"]
            mins = raw["daily"]["temperature_2m_min"]
            buckets = {m: [] for m in range(1, 13)}
            for dstr, v in zip(dates, mins):
                if v is None:
                    continue
                buckets[int(dstr[5:7])].append(v)
            out[city["name"]] = [
                round(sum(buckets[m]) / len(buckets[m])) if buckets[m] else CLIMATE_TMIN_F[city["name"]][m - 1]
                for m in range(1, 13)
            ]
        except Exception:  # noqa: BLE001  拉取失败就退回静态表
            out[city["name"]] = CLIMATE_TMIN_F[city["name"]]
    return out


def weeks_to_cold_peak(normals, today=None):
    """基于气候常年值估算「距寒冷高峰还有几周」，并给出预测高峰日期。

    做法：把 12 个月摊成 52 个周点插值，从今天出发向前找最近一次
    「温度跌到全冬中位以下且继续走低」的拐点，即需求高峰起点。
    简化实现：取各城全年最冷月（normals 最小月）作为高峰月；若已过该月
    则视为下一轮（+12 个月）。多城取加权中位数，避免单城噪声。
    """
    today = today or dt.date.today()
    # 先算出「相对全年最冷月」的加权平均偏移，作为整体季节位相
    offsets = []
    for city in CITIES:
        arr = normals.get(city["name"]) or CLIMATE_TMIN_F[city["name"]]
        peak = min(range(1, 13), key=lambda m: arr[m - 1])
        offsets.append((peak - today.month, city.get("weight", 1.0), peak))
    total_w = sum(w for _, w, _ in offsets) or 1.0
    avg_off = sum(o * w for o, w, _ in offsets) / total_w
    # 统一到 -6..+6 区间（跨年处理）
    avg_off = (avg_off + 6) % 12 - 6
    weeks = round(avg_off * WEEKS_PER_MONTH, 1)
    peak_months = sorted({p for _, _, p in offsets})
    return {
        "weeks_to_cold_peak": weeks,
        "peak_months": peak_months,
        "peak_label": "1 月（年度最冷月）" if peak_months == [1] else f"{peak_months} 月",
        "method": "12 城气候常年值加权中位相位 + 全年最冷月推算",
    }


def fetch_city(city, timeout=25):
    """抓单个城市 7 天预报，返回标准化 dict。失败时返回带 error 的 dict，不抛异常。"""
    q = (
        f"{API}?latitude={city['lat']}&longitude={city['lon']}"
        f"&daily=snowfall_sum,temperature_2m_min"
        f"&temperature_unit=fahrenheit&precipitation_unit=inch"
        f"&forecast_days={DAYS}&timezone={urllib.parse.quote(city['tz'])}"
    )
    req = urllib.request.Request(q, headers={"User-Agent": "heating-pad-skill/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
        return {"city": city["name"], "state": city["state"], "error": f"{type(e).__name__}: {e}"}
    except json.JSONDecodeError as e:
        return {"city": city["name"], "state": city["state"], "error": f"bad json: {e}"}

    d = raw.get("daily") or {}
    dates = d.get("time") or []
    snows = d.get("snowfall_sum") or []
    mins = d.get("temperature_2m_min") or []
    days = []
    for i, day in enumerate(dates):
        days.append({
            "date": day,
            "snow_in": sf(snows[i]) if i < len(snows) else None,
            "tmin_f": sf(mins[i]) if i < len(mins) else None,
        })
    # 丢掉今天（已过去的天气对「未来 7 天备战」无意义），只保留未来 7 天
    today_iso = dt.date.today().isoformat()
    fut = [x for x in days if x["date"] > today_iso][:WINDOW] or days[:WINDOW]
    valid_mins = [x["tmin_f"] for x in days if x["tmin_f"] is not None]
    valid_snow = [x["snow_in"] for x in fut if x["snow_in"] is not None]
    return {
        "city": city["name"],
        "state": city["state"],
        "tz": city["tz"],
        "days": fut,
        "snow_total_in": sf(sum(valid_snow), 2) if valid_snow else None,
        "tmin_7d_f": sf(min(valid_mins)) if valid_mins else None,
        "snow_days": [x["date"] for x in fut if (x["snow_in"] or 0) >= SNOW_ANY_IN],
        "snow_peak_in": sf(max(valid_snow), 2) if valid_snow else 0.0,
    }


def load_prev(state_dir):
    """读取「昨日基准」快照。

    优先用 state_dir/latest.json；若 latest.json 就是今天生成的（说明今天已跑过、
    再跑会拿自己比自己，delta 恒为 0），则退回最新的 state/YYYY-MM-DD.json（日期 < 今天）。
    """
    today_iso = dt.date.today().isoformat()

    def _read(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                prev = json.load(f)
            return prev, prev.get("generated_at")
        except (OSError, json.JSONDecodeError):
            return None, None

    p = os.path.join(state_dir, "latest.json")
    if os.path.isfile(p):
        prev, gen = _read(p)
        if prev and prev.get("date") != today_iso:
            return prev, gen

    # latest.json 缺失或已是今天 → 找日期早于今天的最新快照
    snaps = []
    for name in os.listdir(state_dir):
        if not name.endswith(".json") or name in ("latest.json", "today.json", "alerts.json"):
            continue
        stem = name[:-5]
        try:
            dt.date.fromisoformat(stem)
        except ValueError:
            continue
        if stem < today_iso:
            snaps.append(stem)
    for stem in sorted(snaps, reverse=True):
        prev, gen = _read(os.path.join(state_dir, f"{stem}.json"))
        if prev:
            return prev, gen
    return None, None


def build_changes(cities, prev):
    """生成 changes：逐城最低温/降雪较昨日变化 + 全站汇总标记。"""
    changes = {
        "baseline_date": None,
        "tmin_drops": [],       # 降幅榜（负值=变冷）
        "tmin_rises": [],       # 升幅榜
        "snow_added": [],       # 新出现降雪的城市
        "snow_removed": [],     # 降雪消失的城市
        "max_single_city_drop_f": 0.0,
        "any_city_drop_ge_5f": False,
        "consecutive_warmup_3d": False,
        "multi_city_low_20f": False,
        "snow_in_7d": False,
    }
    ok = [c for c in cities if "error" not in c]
    changes["snow_in_7d"] = any(c.get("snow_days") for c in ok)
    cold_cities = [c["city"] for c in ok if (c.get("tmin_7d_f") or 99) <= COLD_BURST_F]
    changes["multi_city_low_20f"] = len(cold_cities) >= COLD_BURST_CITY_N
    changes["cold_cities"] = cold_cities
    # 回落期判据：某城未来 7 天最低温曲线出现「连续 3 天逐日回升且累计 >= 10°F」
    for c in ok:
        m = [d["tmin_f"] for d in c.get("days", []) if d.get("tmin_f") is not None]
        for i in range(len(m) - 3):
            seg = m[i:i + 4]
            rising = all(seg[j + 1] > seg[j] for j in range(3))
            if rising and (seg[-1] - seg[0]) >= WARM_BACK_F:
                changes["consecutive_warmup_3d"] = True
                changes["warmup_city"] = c["city"]
                break

    if not prev:
        changes["baseline_date"] = None
        changes["note"] = "无昨日快照，changes 为空基准首跑"
        return changes

    changes["baseline_date"] = prev.get("date") or prev.get("generated_at")
    pmap = {f"{p['city']}": p for p in prev.get("cities", []) if "error" not in p}
    today_snow = {c["city"]: (c.get("snow_days") or []) for c in ok}
    for c in ok:
        p = pmap.get(c["city"])
        if not p:
            continue
        d = {
            "city": c["city"],
            "state": c["state"],
            "tmin_prev_f": p.get("tmin_7d_f"),
            "tmin_now_f": c.get("tmin_7d_f"),
            "delta_f": None,
            "snow_prev_in": p.get("snow_total_in"),
            "snow_now_in": c.get("snow_total_in"),
            "snow_delta_in": None,
        }
        if d["tmin_prev_f"] is not None and d["tmin_now_f"] is not None:
            d["delta_f"] = sf(d["tmin_now_f"] - d["tmin_prev_f"])
        if d["snow_prev_in"] is not None and d["snow_now_in"] is not None:
            d["snow_delta_in"] = sf(d["snow_now_in"] - d["snow_prev_in"], 2)
        if d["delta_f"] is not None:
            if d["delta_f"] < 0:
                changes["tmin_drops"].append(d)
            elif d["delta_f"] > 0:
                changes["tmin_rises"].append(d)
        prev_days = set(p.get("snow_days") or [])
        now_days = set(today_snow.get(c["city"], []))
        if now_days - prev_days:
            changes["snow_added"].append({"city": c["city"], "days": sorted(now_days - prev_days)})
        if prev_days - now_days:
            changes["snow_removed"].append({"city": c["city"], "days": sorted(prev_days - now_days)})

    changes["tmin_drops"].sort(key=lambda x: x["delta_f"])
    changes["tmin_rises"].sort(key=lambda x: -x["delta_f"])
    if changes["tmin_drops"]:
        changes["max_single_city_drop_f"] = changes["tmin_drops"][0]["delta_f"]
        changes["any_city_drop_ge_5f"] = abs(changes["max_single_city_drop_f"]) >= DROP_ALERT_F
    return changes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="JSON 输出路径（同时打印到 stdout）")
    ap.add_argument("--state-dir", default=None, help="昨日快照目录，默认 ./state")
    ap.add_argument("--no-save-state", action="store_true", help="不写 latest.json（调试用）")
    ap.add_argument("--live-climate", action="store_true",
                    help="用 Open-Meteo Archive 拉最近 5 年气候基准（较慢，约 +12 次请求）")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    state_dir = args.state_dir or os.path.join(here, "..", "state")
    state_dir = os.path.abspath(state_dir)
    os.makedirs(state_dir, exist_ok=True)

    cities = [fetch_city(c) for c in CITIES]
    failed = [c["city"] for c in cities if "error" in c]
    prev, _ = load_prev(state_dir)
    changes = build_changes(cities, prev)

    today = dt.date.today().isoformat()
    normals = climate_normals(live=args.live_climate)
    season = weeks_to_cold_peak(normals)
    result = {
        "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "market": "US",
        "source": "open-meteo.com",
        "date": today,
        "window_days": WINDOW,
        "window_start": today,
        "season": season,
        "units": {"snow": "inch", "temperature": "fahrenheit"},
        "thresholds": {
            "snow_any_in": SNOW_ANY_IN,
            "cold_burst_f": COLD_BURST_F,
            "drop_alert_f": DROP_ALERT_F,
            "warm_back_f": WARM_BACK_F,
        },
        "cities": cities,
        "failed_cities": failed,
        "changes": changes,
        # 阶段判定的机读结论（人读结论仍由模型结合 WebSearch 判断）
        "signals": {
            "snow_in_7d": changes["snow_in_7d"],
            "multi_city_low_20f": changes["multi_city_low_20f"],
            "cold_cities": changes.get("cold_cities", []),
            "any_city_drop_ge_5f": changes["any_city_drop_ge_5f"],
            "consecutive_warmup_3d": changes["consecutive_warmup_3d"],
            "coldest_city": next(                ({"city": c["city"], "tmin_f": c["tmin_7d_f"]} for c in
                 sorted([x for x in cities if "error" not in x and x.get("tmin_7d_f") is not None],
                        key=lambda x: x["tmin_7d_f"])), None),
            "snow_cities": [{"city": c["city"], "state": c["state"], "days": c["snow_days"],
                             "total_in": c["snow_total_in"], "peak_in": c.get("snow_peak_in")}
                            for c in cities if "error" not in c and c.get("snow_days")],
        },
    }

    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    if not args.no_save_state:
        with open(os.path.join(state_dir, "latest.json"), "w", encoding="utf-8") as f:
            f.write(text)
        with open(os.path.join(state_dir, f"{today}.json"), "w", encoding="utf-8") as f:
            f.write(text)
    print(text)
    if failed:
        print(f"[warn] {len(failed)} 城抓取失败: {', '.join(failed)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
