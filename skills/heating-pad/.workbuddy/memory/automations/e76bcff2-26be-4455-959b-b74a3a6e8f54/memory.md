# 自动化执行记忆 · 加热垫美国站每日简报

## 2026-10-20（首次执行）
- 抓取：Open-Meteo 12 城全部成功，failed_cities 为空；建立 latest.json 基准（明日开始有「较昨日」对比）。
- 判定：备战期。未来 7 天 12 城零降雪，本土最冷 Minneapolis 40.3°F，无城市 ≤20°F；season.weeks_to_cold_peak=13.0 → 起量倒计时 9 周。
- 关键判断：本波是美国本土回暖（Minneapolis 10/21 43.2°F→10/23 58.3°F），属雪前升温，按规则不算回落期。
- 资讯：NWS CPC 10/19 6-10 天展望（中东部偏暖>50%）、NWS 冻警 11 州（10/17-18）、NOAA 10/15 冬季展望（强厄尔尼诺，北部偏暖少雪）。
- 产出：logs/us-heatpad-brief-2026-10-20.md；企业微信日报已推送成功，未触发降雪告警。
- 环境坑位：wecom-cli 在 Python subprocess 下用 .cmd 路径会报文件名语法错误；有效做法是写 payload 到 JSON 文件，再用 `bash -lc 'wecom-cli message aibot send --json "$(cat file.json)"'` 调用（返回值 success=true）。

## 2026-10-21（第二次执行）
- 抓取：12 城全部成功，failed_cities 空；基线 10/20。
- 判定：**备战期 → 爆发期切换**。触发证据：Minneapolis 10/26 出现 0.1" 降雪（changes.snow_added 非空），按「7 天内有雪即爆发期」判定；consecutive_warmup_3d=true 但基线零雪，属雪前升温，不判回落期。起量倒计时按爆发期归零写作「已起量」（气象口径仍为 9 周）。
- 数值：本土最冷 Buffalo 34.6°F、Pittsburgh 35.4°F、Minneapolis 36.0°F；无城市 ≤20°F；最大单城降幅 Minneapolis -4.3°F（未达 5°F）。
- 告警：A1/A2/A3 均 not_fired；但 snow_added 非空 → 单独推送降雪告警一条（Minneapolis 10/26 0.1"）。
- 资讯：NWS Denver/Boulder 10/21（冷锋东移、无冬季风暴警报）；NWS CPC 10/15 冬季展望（极强厄尔尼诺 Niño-3.4 +2.4°C、西向 QBO → 极涡偏强、冷空气南下偏少）。第二、三组关键词命中的多为阿拉斯加冬季风暴与商业媒体口径，仅作弱信号。
- 产出：logs/us-heatpad-brief-2026-10-21.md；企业微信日报 + 降雪告警各一条，均 success=true。
- 复用要点：`wecom-cli message aibot sessions list` 可取 chat_id（授权真人 userid，单聊）；payload 存 state/wecom_payload_*.json。

## 2026-10-22（第三次执行）
- 抓取：12 城全部成功，failed_cities 空；基线 10/21。
- 判定：**爆发期 → 备战期回退**。证据：Minneapolis 10/26 的 0.1" 降雪被新预报移除（changes.snow_removed 非空），snow_in_7d 归零、cold_cities 为空；consecutive_warmup_3d=true 但本波从未真正降雪，按「雪前升温不算回落期」排除回落期。起量倒计时 13−4=9 周。
- 数值：本土最冷 Buffalo 32.8°F、Boston 37.0°F；最大单城降幅 New York −4.0°F（未达 5°F）；Anchorage 25.0°F 属 baseline_only。
- 告警：A1/A2/A3 全 not_fired，未发降雪告警，仅推日报一条 success=true。
- 资讯：NWS 10/21 东岸 Nor'easter（沿岸大风、内陆无雪）+ 太平洋风暴（Sierra/落基山山地雪）；CPC 10/15 冬季展望（极强厄尔尼诺、极涡偏强→北部偏暖少雪）；AccuWeather 10/19 雪量图（Buffalo 55–70"）作弱信号。
- 教训：预报中的「首雪」可在次日被撤销，阶段可能出现爆发期→备战期倒退，需在结论里点名并写明 snow_removed 证据，不要为维持昨日结论硬凑。

## 2026-10-24（第五次执行）
- 抓取：12 城全部成功，failed_cities 空；基线 10/23。
- 判定：**临门期（未切换，第 2 日）**。A3 命中（Salt Lake City 45.5→38.0，−7.5°F；Denver −5.3°F）→ a3_takes_p0=true，P0 仍为提预算抢排名。snow_in_7d=false、cold_cities 空 → 不判爆发期；consecutive_warmup_3d=true（Minneapolis）但本波零雪，不判回落期。
- 数值：本土最冷 Boston 33.4°F（A1 差 1.4°F 未触发）、Buffalo 37.1°F、SLC 38.0°F；Anchorage 24.8°F 属 baseline_only。起量倒计时 13−4=9 周。
- 告警：A1/A2 not_fired、A3 fired → 日报 + A3 告警各一条 success=true；snow_in_7d=false → 无降雪告警。
- 资讯：NWS Great Falls 10/23 12:31 MDT 北落基山冬季天气提示（West Yellowstone 一带 1"、高海拔局地 12–18"，山地雪不进城）；AccuWeather 10/19 雪量图（Buffalo 55–70"、SLC 50–65"）弱信号；强厄尔尼诺口径下北部偏暖、中西部周末高 15–25°F。
- 教训：A3 可从东北岸（10/23 NY）切到西部山地（10/24 SLC/Denver）连续命中，P0 会连续两日相同——不必为「有新意」换 P0，规则优先。

## 2026-10-26（第七次执行）
- 抓取：12 城全部成功，failed_cities 空；基线 10/25。
- 判定：**备战期（未切换，第 2 日）**。snow_in_7d=true 但仅 Anchorage（10/30–10/31 各 0.1"，累计 0.2"）→ 按「Anchorage 不单独触发」不判爆发期；max_single_city_drop_f=-2.4（Denver 41.1→38.7）→ 不判临门期；本土零雪 → 不判回落期。起量倒计时 13−4=9 周。
- 数值：Boston 32.9°F 本土最冷（A1 差 0.9°F 未触发）、SLC/Pittsburgh 37.6°F；无城 ≤20°F；Buffalo 逆势升温 +3.8°F。
- 告警：A1/A2/A3 全 not_fired；降雪告警机械条件命中（snow_added=Anchorage 10/30）→ 发「参考城」告警一条，success=true。
- 资讯：NOAA 10/15 冬季展望（强厄尔尼诺、五大湖/东北偏暖少雪，官方不报季节雪量）；AccuWeather 10/24–25 本季首场冬季风暴打 High Plains 六州、明尼苏达西部较大降雪（弱信号）；NWS Fairbanks 10/24 阿拉斯加冬季风暴警报（对应 Anchorage 降雪）。
- 产出：logs/us-heatpad-brief-2026-10-26.md；企业微信日报 + 降雪告警各一条 success=true。
- 复用：state/wecom_daily.json、state/wecom_snow.json（msg_type markdown + markdown.content），`bash -lc` 传参稳定。

## 2026-10-27（第八次执行）
- 抓取：12 城全部成功，failed_cities 空；基线 10/26。
- 判定：**备战期 → 爆发期切换**。触发证据：Denver 11/02 出现 0.2" 降雪（changes.snow_added 含 Denver 与 Anchorage），按「7 天内有雪即爆发期」判定；Anchorage 不单独触发但 Denver 为本土城；cold_cities 空、consecutive_warmup_3d=false → 不判回落期。起量倒计时按爆发期写「已起量」，注明气象口径 13−4=9 周。
- 数值：Boston 32.9→28.9°F（−4.0）为本日最大降幅且本土最冷，A1 命中（≤32°F）；A2 not_fired、A3 not_fired（max_single_city_drop_f=−4.0）。Anchorage 27.2°F 属 baseline_only。
- 告警：A1 fired → 单独推「冰点告警」一条；snow_in_7d=true 且 snow_added 非空 → 另推「降雪告警」一条（Denver 11/02 0.2"）。日报 + 两条告警共 3 条，全部 success=true。
- 资讯：NOAA CPC 10/24 Days 8–14 展望（11/1–7 科罗拉多落基山至丹佛 Front Range 重雪轻风险）与脚本 Denver 首雪互相印证；NWS WPC 10/26 04:34 EDT 平原雪带 T–0.5"、局地 1–2"、喀斯喀特/北落基山雪线降至 3000–5000ft；CPC 10/15 冬季+11 月展望强厄尔尼诺北部偏暖；Arcfield 10/26 提 11 月上中旬极涡扰动（罕见，弱信号）。
- 产出：logs/us-heatpad-brief-2026-10-27.md；wecom payload 复用 state/wecom_daily.json、wecom_snow.json、wecom_alert.json。
- 复用：`bash -lc 'wecom-cli message aibot send --json "$(cat state/xxx.json)"'` 三条连续发送稳定。

## 2026-10-28（第九次执行）
- 抓取：12 城全部成功，failed_cities 空；基线 10/27。
- 判定：**爆发期 → 备战期回退**。证据：Denver 11/02 的 0.2" 首雪被新预报移除（snow_removed 含 Denver 与 Anchorage 多日），本土 11 城零雪、cold_cities 空；consecutive_warmup_3d=false → 不判回落期；max_single_city_drop_f=−2.6 → 不判临门期。起量倒计时 13−4=9 周。
- 数值：本土最冷 Boston 31.9°F（−0.1°C）、Denver 35.7°F、SLC 38.5°F；仅参考城 Anchorage 11/03 有 2.5" 雪；Anchorage 26.1°F 属 baseline_only。
- 告警：A1/A2/A3 全 not_fired。注意 Boston tmin_7d_f=31.9 是「含今日」口径，check_alerts 按 days[]（10/29 起，最低 41.7）判定，不触发 A1——不要手工拿 tmin_7d 去改判。
- 资讯：NWS Seattle AFD 10/26（喀斯喀特/奥林匹克本季首场大范围山地雪、雪线 4000–4500→3000–3500 ft、仅山口）；NWS 警报源 10/27 07:52 UTC 全美无冬季风暴警报；NOAA 10/15 冬季展望（强厄尔尼诺、北部偏少雪，AccuWeather 估 Boston/Chicago 仅常年一半）；WGN 10/26 东部脊 10/26–11/8 大幅偏暖（弱信号）。
- 产出：logs/us-heatpad-brief-2026-10-28.md。
- **推送失败**：`send` 返回 errcode 850003「authorization expired」（机器人「消息」使用权限过期），按规则停止全部企业微信调用、不重试不重连，日报与降雪告警均未送达；已在对话内打印简报原文并原文给出授权链接。下次执行前需先确认该权限是否已续期。

## 2026-10-29（第十次执行）
- 抓取：12 城全部成功，failed_cities 空；基线 10/28。
- 判定：**备战期 → 爆发期切换**。证据：Denver 11/02 首雪回归 0.1"（snow_added 含 Denver、Anchorage），按「7 天内有雪即爆发期」判定；cold_cities 空、consecutive_warmup_3d=true 但本波从未真正降雪 → 不判回落期。起量倒计时写「已起量」，注明气象口径 13−4=9 周。
- 数值：Milwaukee 47.8→39.8（−8.0，本日最大降幅）、Minneapolis 42.6→36.7（−5.9）、Detroit 48.0→42.1（−5.9）；本土最冷 Boston 31.8°F（tmin_7d 含今日口径）、Minneapolis 36.7°F；无城 ≤20°F；Anchorage 10/30–11/04 累计 6.8"、11/01 峰值 4.7"，属参考城。
- 告警：A1/A2 not_fired、A3 fired（a3_takes_p0=true）→ P0 提预算抢排名；snow_added 非空 → 降雪告警条件命中。应发 日报 + 降雪告警 + A3 告警共 3 条。
- **推送失败**：`send` 返回 errcode 850003「authorization expired」（机器人「消息」权限过期，与 10/28 同因未续期）。按规则停止全部企业微信调用、不重试不重连，三条全部未送达；已在对话内完整打印简报原文并给出授权链接。权限恢复后需补推 10/28、10/29 两日。
- 资讯：NWS CPC 10/23 Week-2 Hazards（10/31–11/02 Central Rockies 至 Front Range 重雪轻风险，与 Denver 首雪互证）；The Weather 10/28 强冷锋周四过五大湖/俄亥俄谷、锋后加拿大冷气团；CPC 10/15 冬季+11 月展望（强厄尔尼诺、Niño3.4 局地 +4.0°C、五大湖偏暖偏干）；Judah Cohen/FOX Weather 称 11 月初或现史上最早最大极涡扰动（弱信号）。
- 产出：logs/us-heatpad-brief-2026-10-29.md（CJK 265 字，符合 ≤350）。

## 2026-10-25（第六次执行）
- 抓取：12 城全部成功，failed_cities 空；基线 10/24。
- 判定：**临门期 → 备战期回退**。证据：A3 未再命中（max_single_city_drop_f=-2.0，Buffalo 37.1→35.1°F 未达 5°F），snow_in_7d=true 但仅 Anchorage（10/31 0.2"）→ 按「Anchorage 不单独触发阶段变更」不判爆发期；consecutive_warmup_3d=true（SLC）但本波零雪不判回落期。起量倒计时 13−4=9 周。
- 数值：本土最冷 Boston tmin_7d 31.6°F（−0.2°C）、Buffalo 35.1°F；无城 ≤20°F；Anchorage 27.5°F 属 baseline_only。
- 告警：A1/A2/A3 全 not_fired。降雪告警机械条件命中（snow_in_7d && snow_added=Anchorage）→ 按 Step 六字面发送一条「参考口径」告警（标注参考城、无需动作），success=true。
- 资讯：NWS weather.gov 10/25（冷锋东扫，五大湖—东岸锋后秋季凉温+大风，无冬季风暴警报）；NYT 引 NOAA（未来 7 天约 2560 万人遇冰点下低温，弱信号；注意该交互页 URL 为 2025 路径，谨慎引用）。第二、三组关键词命中多为手册/1 月旧闻，弃用。
- 产出：logs/us-heatpad-brief-2026-10-25.md；企业微信日报 + 降雪参考告警各一条 success=true。
- 复用：wecom payload 用 `msg_type:"markdown"` + `markdown.content` 嵌套结构（沿用 10/24 格式）；chat_id 固定 woxiB5OgAAyu7R562lFGrOCwW64E19tw。
- 抓取：12 城全部成功，failed_cities 空；基线 10/22。
- 判定：**备战期 → 临门期**。触发证据：New York 最低温 41.0→36.0°F（-5.0°F）命中 any_city_drop_ge_5f；snow_in_7d=false、cold_cities 空 → 不判爆发期；consecutive_warmup_3d=true 但本波零雪，不判回落期。起量倒计时仍按公式 13−4=9 周（临门期由急降温触发，非日历）。
- 数值：本土最冷 Boston 32.7°F、Buffalo 33.8°F、Pittsburgh 34.3°F、NY 36.0°F；无城市 ≤32.0°F（A1 差 0.7°F 未触发）；Anchorage 25.4°F 属 baseline_only。
- 告警：A1/A2 not_fired、A3 fired（a3_takes_p0=true）→ P0 由「抢排名」接管；已单独推送 A3 急降告警一条。snow_in_7d=false → 无降雪告警。
- 资讯：NWS 10/22 东北岸高压阻塞、夜间晴空霜冻结冰、下周初冷锋（DC News Now 引 NWS）；NOAA 10/15 冬季展望（极强厄尔尼诺、北部偏暖少雪、极涡南下偏少，AP 10/17 报道）；Weather Co 10/22 北落基山周五冬季天气提示（作弱信号）。
- 产出：logs/us-heatpad-brief-2026-10-23.md；企业微信日报 + A3 告警均 success=true。
- 复用：wecom-cli 用 `bash -lc 'wecom-cli message aibot send --json "$(cat state/wecom_*.json)"'` 稳定成功（payload 存 state/wecom_daily.json、wecom_alert.json）。

## 2026-10-30（第十一次执行）
- 抓取：12 城全部成功，failed_cities 空；基线 10/29。
- 判定：**爆发期 → 临门期**。证据：Denver 11/02 首雪撤销（snow_removed 含 Denver 11/02、Anchorage 10/30 与 11/04）、本土零雪、cold_cities 空 → 爆发期失效；A3 命中（Pittsburgh −7.6、Cleveland −7.2、Buffalo −6.6）→ 临门期。consecutive_warmup_3d=true 但本波零雪 → 不判回落期。起量倒计时 13−4=9 周。
- 数值：本土最冷 Buffalo 35.7°F（2.1°C）、Boston 38.2、Detroit 39.1；A1/A2 not_fired；A3 fired → a3_takes_p0=true，P0 提预算抢排名。
- 告警：A3 一条 + 降雪告警（Anchorage 11/05 0.3"，参考城）机械条件命中。
- 资讯：NWS Cleveland/NYC/Bismarck 10/30 无任何 watch/warning/advisory；NWS Grand Rapids 10/30 太平洋风暴+白令海风暴；NOAA 10/15 强厄尔尼诺展望；CIC 10/25 MJO phase 3、北美积雪覆盖落后常年。
- 产出：logs/us-heatpad-brief-2026-10-30.md（CJK 329）。
- **推送失败**：`auth show --status`=authorized，但 `message aibot sessions list` 返回 850003 authorization expired（机器人消息权限连续第 3 日未续期）。已停止全部企业微信调用、不重试不重连，简报原文与 help_message 已打印到会话。待补推 10/28、10/29、10/30。

## 2026-10-31（第十二次执行）
- 抓取：12 城全部成功，failed_cities 空；基线 10/30。
- 判定：**临门期（未切换，第 2 日）**。A3 命中（Boston 38.2→31.1，−7.1°F）→ a3_takes_p0=true，P0 提预算抢排名；A1 同时命中（Boston 11/01 31.1°F ≤32），A2 not_fired。本土 11 城零雪、cold_cities 空、consecutive_warmup_3d=true 但本波零雪 → 不判爆发期/回落期。起量倒计时 13−4=9 周。
- 数值：本土最冷 Boston 31.1°F（−0.5°C）、New York 35.6、Minneapolis 36.8、Buffalo 37.1；参考城 Anchorage 11/01+11/04 各 0.2"（累计 0.4"）、tmin 30.0°F 属 baseline_only；Denver 逆势 +4.3°F。
- 资讯：NWS CPC 10/28 15:00 EDT 6–10 天（11/03–11/07）中大西洋至五大湖偏暖 >70%、8–14 天（11/05–11/11）全美偏暖；NWS 三办公室 10/29 Sierra 冬季天气提示（雪线 6000–7000 ft，最高峰 12"，仅山地）；NOAA 10/15 冬季展望强厄尔尼诺北部偏暖；CIC 10/25 北美积雪覆盖落后常年。
- 告警：A3 + A1 应各发一条，加降雪告警（Anchorage 11/04 0.2"，参考城）与日报，共 4 条。
- 产出：logs/us-heatpad-brief-2026-10-31.md（CJK 302）。
- **推送失败**：`auth show --status`=authorized，但 `message aibot sessions list` 返回 850003（机器人「消息」权限连续第 4 日未续期）。已停止全部企业微信调用、不重试不重连，简报原文与 help_message 已打印到会话。待补推 10/28–10/31 共 4 日；权限恢复前不要再逐条试发。

## 2026-11-01（第十三次执行）
- 抓取：12 城全部成功，failed_cities 空；基线 10/31。season.weeks_to_cold_peak 由 13.0 降到 8.7（跨月推进），起量倒计时 8.7−4=4.7 周——首次进入 5 周内的实质备战窗口。
- 判定：**临门期 → 备战期回退**。证据：A3 未再命中（max_single_city_drop_f=−2.3，Anchorage），本土 11 城零雪、cold_cities 空；consecutive_warmup_3d=true 但本波零雪不判回落期。P0 换回 Listing 补词（备战期不能写提预算）。
- 数值：本土最冷 Boston tmin_7d 31.5°F（days[] 最低 40.1，A1 按 days[] 判定仍 not_fired）、Buffalo 38.5；参考城 Anchorage 11/04 0.7"+11/06 0.1"+11/07 0.4"=1.2"；最大升温 Minneapolis 36.8→44.6（+7.8）。
- 资讯：NWS CPC 10/28 6–10 天（11/03–11/07）中大西洋至五大湖偏暖 >70%、8–14 天（11/05–11/11）全美偏暖；NOAA CPC 10/15 11 月展望北部三分之二偏暖、五大湖信号最强、强厄尔尼诺主导；worldnaturaldisasters 10/30 08:52 UTC 统计全美仅阿拉斯加 1 条冬季风暴警报（本土零）；NWS Sierra 10/31–11/01 山地雪（雪线 7000 ft）；FOX/severe-weather 提 11 月第二周极涡或史上最早大规模扰动（弱信号）。
- 告警：A1/A2/A3 全 not_fired（页脚「今日 A1/A2/A3 均未触发」）；降雪告警机械条件命中但仅参考城 Anchorage，未能发送。
- 产出：logs/us-heatpad-brief-2026-11-01.md（CJK 322）。
- **推送失败**：`auth show --status`=authorized，`message aibot send` 直接返回 850003（机器人「消息」权限连续第 5 日未续期）。已停止全部企业微信调用、不重试不重连（含降雪告警未发），简报原文与 help_message 已逐字打印到会话。待补推 10/28–11/01 共 5 日。
- 复用：payload 存 state/wecom_daily.json、wecom_snow.json；发送命令 `bash -lc 'wecom-cli message aibot send --json "$(cat state/xxx.json)"'` 结构正常，失败仅因权限。

## 2026-11-02（第十四次执行）
- 抓取：12 城全部成功，failed_cities 空；基线 11/01。
- 判定：**备战期 → 临门期切换**。证据：A3 命中（Salt Lake City 43.0→35.3，−7.7°F）→ any_city_drop_ge_5f=true；snow_in_7d=true 但仅 Anchorage（11/06 0.2"，参考城不触发）；consecutive_warmup_3d=true 但本波零雪 → 不判回落期。P0 由 A3 接管为提预算抢排名。
- 数值：本土最冷 SLC 35.3°F（1.8°C）；Boston tmin_7d 29.5°F（含今日口径，days[] 最低 45.5，A1 not_fired）；Anchorage 26.8°F baseline_only，snow_removed 11/04 与 11/07；升温 Cleveland +4.6°F。起量倒计时 8.7−4=4.7 周（第二日保持 5 周内窗口）。
- 资讯：NOAA 10/15 冬季展望（极强厄尔尼诺、41 州偏暖、极涡更稳寒潮偏少）；OpenSnow/星島 10/16（SLC 为唯一降雪高于常年的大型都会区，与 SLC 急降互证）；其余搜索命中多为 2025-12/2026-01 旧闻弃用。
- 告警：A1/A2 not_fired、A3 fired → 应发日报 + A3 告警共 2 条；降雪告警未命中（snow_added 空、昨日基线有 Anchorage 雪 1.2"）。
- 产出：logs/us-heatpad-brief-2026-11-02.md（CJK 334）。
- **推送失败**：`auth show --status`=authorized，但 `message aibot sessions list` 返回 850003（机器人「消息」权限连续第 6 日未续期）。按规则停止全部企业微信调用、不重试不重连，简报原文与最新 help_message 授权链接已打印到会话。待补推 10/28–11/02 共 6 日；权限恢复前不要再逐条试发。

## 2026-11-03（第十五次执行）
- 抓取：12 城全部成功，failed_cities 空；基线 11/02。
- 判定：**临门期（未切换，第 2 日）**。A3 命中（Denver 40.4→32.9，−7.5°F；Cleveland −4.3）→ a3_takes_p0=true，P0 提预算抢排名；A1 not_fired（Denver 32.9 距冰点 0.9°F）、A2 not_fired。snow_in_7d=true 但仅 Anchorage 0.5"（11/04 0.1+11/07 0.2+11/09 0.2，参考城不触发爆发期）；consecutive_warmup_3d=false → 不判回落期。
- 数值：本土最冷 Denver 32.9°F（0.5°C）、SLC 36.1、Buffalo 36.9；Boston 大幅回暖 29.5→40.1（+10.6）。起量倒计时 8.7−4=4.7 周。
- 资讯：NWS CPC 10/28 6–10 天（11/03–07）中大西洋至五大湖偏暖 >70%、8–14 天全美偏暖（经 Orbis/energyreader 转述 CPC 原文）；worldnaturaldisasters 10/30 08:52 UTC 统计全美仅阿拉斯加 1 条冬季风暴警报（Susitna Valley，NWS Anchorage 10/29 发布，7–15"）；NOAA 2026-27 冬季展望强厄尔尼诺、北部偏暖；AccuWeather 报 SLC 50–65" 雪、东北/中西部偏少（弱信号）。
- 告警：应发日报 + A3 告警 + 降雪参考告警（Anchorage）共 3 条。
- 产出：logs/us-heatpad-brief-2026-11-03.md（CJK 308）。
- **推送失败**：`auth show --status`=authorized，但 `message aibot sessions list` 返回 850003（机器人「消息」权限连续第 7 日未续期）。已停止全部企业微信调用、不重试不重连，简报原文与最新 help_message 授权链接已打印到会话。待补推 10/28–11/03 共 7 日。

## 2026-11-05（第十七次执行）
- 抓取：12 城全部成功，failed_cities 空；基线 11/04。
- 判定：**临门期（未切换，第 3 日）**。A3 命中（Minneapolis 38.8→31.6，−7.2°F）→ a3_takes_p0=true，P0 续为提预算抢排名；A1 同日命中（Minneapolis 11/06 31.6°F ≤32）。snow_in_7d=true 但仅参考城 Anchorage（11/07 0.1+11/09 0.2+11/10 0.6=0.9"，snow_added 非空）→ 不判爆发期；consecutive_warmup_3d=true（SLC）但本波零雪 → 不判回落期。起量倒计时 8.7−4=4.7 周。
- 数值：本土最冷 Minneapolis 31.6°F（-0.2°C）、Denver 34.1、SLC/Milwaukee/Chicago 36 上下；无城 ≤20°F；Boston ↓4.0、Buffalo ↓3.6。
- 资讯：NWS WPC 11/04 09Z（东岸冷温+伊利/安大略湖效应雪、Four Corners 上层低压中落基山山区增雪、锋后冷空气再强化）；severe-weather.eu 10月更新（super El Niño：西南/南部平原偏多雪、五大湖/东北北部偏少，弱信号）；snow-forecast 10/29（El Niño 11 月达峰，弱信号）。第二组关键词命中多为术语手册/1 月旧闻弃用。
- 告警：A3 fired、A1 fired、A2 not_fired；降雪告警机械条件命中（参考城 Anchorage）。应发日报 + A3 + A1 + 降雪参考共 4 条。
- 产出：logs/us-heatpad-brief-2026-11-05.md（CJK 265）。
- **推送失败**：`auth show --status`=authorized，但 `message aibot sessions list` 返回 850003（机器人「消息」权限连续第 9 日未续期）。按规则停止全部企业微信调用、不重试不重连，简报原文与最新 help_message 已打印到会话。待补推 10/28–11/05 共 9 日。

## 2026-11-04（第十六次执行）
- 抓取：12 城全部成功，failed_cities 空；基线 11/03。
- 判定：**临门期（未切换，第 2 日）**。A3 命中（Milwaukee 42.4→35.8，−6.6°F；Chicago −5.8）→ a3_takes_p0=true，P0 续为提预算抢排名；A1 not_fired（Denver 32.4°F 距冰点 0.4°F）、A2 not_fired。本体 12 城零降雪（Anchorage 11/04、11/07、11/09 的雪被新预报撤销，snow_removed 非空）→ 不判爆发期；consecutive_warmup_3d=true 但本波零雪 → 不判回落期。
- 数值：本土最冷 Denver 32.4°F（0.2°C）、Salt Lake City 35.7、Milwaukee 35.8；参考城 Anchorage 19.0°F 属 baseline_only；回暖 Buffalo +6.9、Boston +6.8。起量倒计时 8.7−4=4.7 周。
- 资讯：NWS weather.gov 11/04 首页头条（冷锋逼近密西西比河谷、暴雨+孤立强对流、佛州东南持续降雨，本土无冬季风暴）；NWS CPC 11/02 15:00 EST Week-2 灾害展望（11/10–16，重雪仅喀斯喀特/内华达/落基山高海拔，东部无重降水，仅大风轻风险）；三组主关键词与两组补充搜索命中多为中国天气/拉美旧闻，弃用。
- 告警：A1/A2 not_fired、A3 fired；snow_in_7d=false → 无降雪告警。应发日报 + A3 各 1 条。
- 产出：logs/us-heatpad-brief-2026-11-04.md（CJK 274）。
- **推送失败**：`auth show --status`=authorized，`message aibot send` 返回 850003（机器人「消息」权限连续第 8 日未续期）。按规则停止全部企业微信调用、不重试不重连（A3 告警未发），简报原文与最新 help_message 已打印到会话。待补推 10/28–11/04 共 8 日。

## 2026-11-06（第十八次执行）
- 抓取：12 城全部成功，failed_cities 空；基线 11/05。
- 判定：**临门期 → 爆发期切换**。触发证据：本土首雪首次进入 7 天窗口——Cleveland 11/11 0.2"+11/12 0.1"（合计 0.3"）、Buffalo 11/12 0.1"，`changes.snow_added` 含 Cleveland/Buffalo/Anchorage；cold_cities 空、consecutive_warmup_3d=true 但本波刚出现雪（非「已下过雪」）→ 不判回落期。
- 数值：本土累计 0.4"、最强单日 Cleveland 11/11 0.2"；本土最冷 Denver 32.4°F（A1 差 0.4°F 未触发）、SLC 33.3°F；无城 ≤20°F；参考城 Anchorage 11/09–11/12 累计 2.2"、tmin 20.7°F（baseline_only）。起量倒计时按爆发期「已起量」，气象口径 8.7−4=4.7 周。
- 告警：A1/A2 not_fired、A3 fired（Cleveland 44.2→37.6，−6.6°F）→ a3_takes_p0=true，P0 提预算抢排名；snow_added 非空 → 降雪告警条件命中（Cleveland 11/11、Buffalo 11/12）。
- 资讯：NWS Buffalo 11/05 16:05 EST 五大湖预报（伊利湖以东低压槽驻留、周日西北风 15–25 kt、waterspouts → 湖效应雪条件成型），与脚本 Cleveland/Buffalo 首雪互证；NBC Chicago 11/05（NOAA 认可 11 月初极涡扰动或为史上最早 SSW，但强厄尔尼诺仍让五大湖冬温偏暖）；Old Farmer's Almanac 11 月（五大湖/中西部偏冷 3–5°F、湖效应带 11 月 2–3 ft，弱信号）；Ohio Ag Weather 11/05 称下周偏干无强冷（与脚本相反，未采用）。
- 产出：logs/us-heatpad-brief-2026-11-06.md（CJK 251）。
- **推送失败**：`auth show --status`=authorized，但 `message aibot sessions list` 返回 850003（机器人「消息」权限连续第 10 日未续期）。按规则停止全部企业微信调用、不重试不重连，日报 + A3 告警 + 降雪告警共 3 条均未送达；简报原文与最新 help_message 已打印到会话。待补推 10/28–11/06 共 10 日；权限恢复前不要再逐条试发。

## 2026-11-07（第十九次执行）
- 抓取：12 城全部成功，failed_cities 空；基线 11/06。
- 判定：**爆发期（未切换，第 2 日）**。本土雪窗从 2 城 0.4" 扩到 6 城 5.9"——Chicago 11/13 2.5"、Detroit 11/12–13 1.3"、Pittsburgh 11/12–13 1.2"、Milwaukee 11/12 0.5"、Boston 11/13 0.3"、Cleveland 11/12 0.1"；Anchorage 1.6"（参考城）。Cleveland 11/11 与 Buffalo 11/12 旧雪被撤销（snow_removed），但新增城更多，净扩张。cold_cities 空、consecutive_warmup_3d=true 但本波有雪 → 不判回落期。
- 数值：本土最冷 Minneapolis 30.1°F、Milwaukee 30.8、Chicago 31.2；无城 ≤20°F；最大降幅 Chicago −5.3°F。起量倒计时按爆发期「已起量」（气象 8.7−4=4.7 周）。
- 告警：A3 fired（Chicago 36.5→31.2，−5.3）→ a3_takes_p0=true，P0 广告抢位；A1 fired（Minneapolis 31.5 / Chicago 31.6 ≤32）；A2 not_fired；snow_added 非空 → 降雪告警条件命中。应发日报 + 降雪 + A3 + A1 共 4 条。
- 资讯：NWS WPC 11/06 18:58Z（冷锋周六夜入太平洋西北、雪线 6500→4000–5000 ft、华盛顿山口 Minor Impact）；NWS 口径五大湖湿雪+新英格兰内陆周日湿雪（山地为主）；NWS State College 11/06（宾州周六起首次连续低于常年、阿勒格尼湖效应湿雪仅薄层）；FOX Weather/CPC（极涡 11/8 或创最早扰动，但北部偏暖至 12 月，冷空气传导需数周）。
- 产出：logs/us-heatpad-brief-2026-11-07.md（CJK 263）。
- **推送失败**：`auth show --status`=authorized，但 `message aibot send` 返回 850003（机器人「消息」权限连续第 11 日未续期）。按规则停止全部企业微信调用、不重试不重连，日报 + 降雪 + A3 + A1 共 4 条全部未送达；简报原文与最新 help_message 已打印到会话。待补推 10/28–11/07 共 11 日。

## 2026-11-08（第二十次执行）
- 抓取：12 城全部成功，failed_cities 空；基线 11/07。
- 判定：**爆发期（未切换，第 3 日）**。本土雪窗连续第 2 日扩张至 7 城 8.0"——Pittsburgh 3.1"（+1.9）、Chicago 1.6"、Buffalo 1.5"、Detroit 1.1"、Cleveland 0.3"、Milwaukee 0.3"、NY 0.1"；Anchorage 0.4"（参考城）。cold_cities 仅 Anchorage、consecutive_warmup_3d=false。起量倒计时按爆发期「已起量」（气象 8.7−4=4.7 周）。
- 数值：本土 tmin_7d 最冷 Milwaukee 30.6、Minneapolis 31.2、Chicago 31.3（A1 按 days[] 判 not_fired）；最大本土降幅 Denver −2.3°F；A3 fired 但仅为参考城 Anchorage（20.7→13.6，−7.1）。
- 告警：A1/A2 not_fired、A3 fired；snow_added 非空 → 降雪告警条件命中。应发日报 + 降雪 + A3 共 3 条。
- 资讯：NWS weather.gov 11/8 首页（北极锋 Snow Squalls Upper Midwest→五大湖持续至周五、暴雪/冬季风暴/大风警报）；ECMWF 11/6 经 AFP（史上最早极涡扰动确认、传导需数周、11 月厄尔尼诺仍偏暖）；NWS Paducah 11/6 Freeze Warning（IL/IN/KY/MO，31°F）；Orbis 11/7 周报（太平洋风暴链、五大湖 late-week 湖效应降水）。
- 产出：logs/us-heatpad-brief-2026-11-08.md。
- **推送失败**：`auth show --status`=authorized，但 `message aibot send` 三条均返回 850003（机器人「消息」权限连续第 12 日未续期）。按规则停止全部企业微信调用、不重试不重连，简报原文与授权链接已打印到会话。待补推 10/28–11/08 共 12 日；权限恢复前不要再逐条试发。

## 2026-11-09（第二十一次执行）
- 抓取：12 城全部成功，failed_cities 空；基线 11/08。
- 判定：**爆发期（未切换，第 4 日）**。本土 6 城雪在窗（Chicago 0.5"、Cleveland 1.0"、Buffalo 1.2"、Pittsburgh 0.7"、Detroit 0.3"、Milwaukee 0.1"=3.8"），Anchorage 1.9"（参考城）。雪窗较昨日收窄（8.0"→3.8"，Pittsburgh −2.4"、Chicago −1.1"、Detroit −0.8"，多城雪日被撤销），snow_added 非空（Cleveland 11/13、Buffalo 11/15、Anchorage 11/11+12）→ 仍按「有雪即爆发期」。cold_cities 仅 Anchorage、consecutive_warmup_3d=true（SLC）但本波有雪不判回落期。起量倒计时「已起量」（气象 8.7−4=4.7 周）。
- 数值：本土最冷 Minneapolis tmin_7d 30.9°F（11/13 跌破冰点）、Milwaukee 33.7、SLC 34.5；最大本土降幅 Cleveland −1.1°F，A3 not_fired。
- 告警：A1 fired（Minneapolis 11/13 30.9≤32）、A2/A3 not_fired；snow_added 非空 → 降雪告警条件命中（本土城市）。应发日报 + A1 + 降雪共 3 条。
- 资讯：NWS weather.gov 11/9 头条（北极冷锋横扫五大湖—东北—中大西洋，阵雪+雪飑+大风，与脚本雪窗互证）；severe-weather.eu 10 月更新（超级厄尔尼诺下五大湖/东北全季雪量偏少，弱信号）；第三组关键词命中 NOAA CPC 9/17 展望（强厄尔尼诺北部偏暖）。
- 产出：logs/us-heatpad-brief-2026-11-09.md。
- **推送失败**：`auth show --status`=authorized，但 `message aibot send` 返回 850003（机器人「消息」权限连续第 13 日未续期）。按规则停止全部企业微信调用、不重试不重连（日报 + A1 + 降雪共 3 条均未发），简报原文与最新 help_message 已打印到会话。待补推 10/28–11/09 共 13 日。payload 已备好：state/wecom_daily.json、wecom_alert_a1.json、wecom_snow.json。
