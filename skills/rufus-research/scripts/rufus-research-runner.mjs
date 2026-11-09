/**
 * RufusResearchRunner
 * Rufus 调研流程编排器
 *
 * 使用方式:
 *   const runner = new RufusResearchRunner({
 *     topic: 'curtain',
 *     saveDir: '~/workspace/rufus-curtain-research',
 *   });
 *   await runner.run(questions); // questions 是问题列表
 */

import { WebSocket } from 'ws';
import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));

const WAIT_MS = 8000;

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * @param {string} dir 目录路径
 */
function ensureDir(dir) {
  const expanded = dir.replace('~', process.env.HOME || '/Users/xiaolingfei');
  if (!fs.existsSync(expanded)) {
    fs.mkdirSync(expanded, { recursive: true });
  }
  return expanded;
}

export class RufusResearchRunner {
  /**
   * @param {object} options
   * @param {string} options.topic 调研主题（如 curtain）
   * @param {string} options.saveDir 保存目录
   */
  constructor(options = {}) {
    this.topic = options.topic || 'research';
    this.saveDir = ensureDir(options.saveDir || `~/workspace/rufus-${this.topic}-research`);
    this.ws = null;
    this.pageId = null;
    this.responses = [];
  }

  // ─── 主流程 ───────────────────────────────────────

  /**
   * 执行完整调研流程
   * @param {string[]} questions 问题列表（英文）
   * @returns {Promise<object[]>} 每个问题的分析结果
   */
  async run(questions) {
    console.log(`\n========== Rufus 调研开始: ${this.topic} ==========\n`);

    // 1. 启动 Chrome
    await this._launchChrome();

    // 2. 导航 Amazon
    await this._navigateAmazon();

    // 3. 逐个提问
    const results = [];
    for (let i = 0; i < questions.length; i++) {
      const q = questions[i];
      console.log(`\n--- Q${i + 1}/${questions.length}: ${q.substring(0, 60)}...`);

      const raw = await this._askRufus(q);
      const parsed = this._parse(raw, q);

      // 保存本地
      await this._saveLocally(i + 1, q, raw, parsed);
      results.push(parsed);
      this.responses.push({ question: q, raw, parsed });

      await sleep(2000);
    }

    // 4. 保存汇总报告
    await this._saveSummary(questions, results);

    // 5. 关闭
    await this.close();

    console.log(`\n========== Rufus 调研完成: ${this.topic} ==========`);
    console.log(`📁 报告已保存至: ${this.saveDir}`);
    return results;
  }

  async close() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  // ─── Chrome 操作 ──────────────────────────────────

  async _launchChrome(port = 9222) {
    try { execSync('pkill -f "Google Chrome" 2>/dev/null', { stdio: 'ignore' }); } catch (_) {}
    await sleep(1000);

    execSync(
      `open /Applications/Google\\ Chrome.app --args --remote-debugging-port=${port} --remote-allow-origins=\\* --user-data-dir=/tmp/chrome-debug 2>&1 &`,
      { stdio: 'ignore' }
    );
    await sleep(4000);

    const version = execSync(`curl -s http://127.0.0.1:${port}/json/version`, { encoding: 'utf8' });
    if (!version) throw new Error('Chrome 启动失败');
    console.log('[Chrome] 启动成功');
  }

  async _navigateAmazon(url = 'https://www.amazon.com/s?k=curtain&s=review-rank') {
    if (this.ws) { this.ws.close(); this.ws = null; }

    const newPage = JSON.parse(execSync(`curl -s -X PUT http://127.0.0.1:9222/json/new`, { encoding: 'utf8' }));
    this.pageId = newPage.id;
    this.wsUrl = newPage.webSocketDebuggerUrl;

    this.ws = new WebSocket(this.wsUrl);
    await new Promise((res, rej) => {
      this.ws.on('open', res);
      this.ws.on('error', rej);
    });

    await this._send('Page.navigate', { url });
    await sleep(5000);
    console.log('[Amazon] 导航成功');
  }

  async _askRufus(question) {
    const escaped = question.replace(/`/g, '\\`').replace(/\$/g, '\\$');

    await this._eval(`
      (function() {
        const ta = document.getElementById("rufus-text-area");
        if (!ta) return "INPUT_NOT_FOUND";
        ta.focus();
        ta.value = "";
        ta.dispatchEvent(new Event("input", { bubbles: true }));
        ta.value = \`${escaped}\`;
        ta.dispatchEvent(new Event("input", { bubbles: true }));
        return "TYPED";
      })()
    `);

    await this._eval(`
      (function() {
        const ta = document.getElementById("rufus-text-area");
        ta.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, cancelable: true, key: "Enter", code: "Enter" }));
      })()
    `);

    console.log(`  等待 Rufus 回复 (${WAIT_MS}ms)...`);
    await sleep(WAIT_MS);

    const result = await this._eval(`
      (function() {
        const panel = document.querySelector(".nav-rufus-content");
        if (!panel) return "";
        const text = panel.textContent || "";
        const marker = \`${question.substring(0, 40)}\`;
        const pos = text.indexOf(marker);
        return pos === -1 ? text.substring(Math.max(0, text.length - 5000)) : text.substring(pos, pos + 5000);
      })()
    `);

    return result || '';
  }

  // ─── 解析 ────────────────────────────────────────

  /**
   * 解析 Rufus 回复，提取结构化数据
   * @param {string} raw 原始回复文本
   * @param {string} question 原始问题
   * @returns {object}
   */
  _parse(raw, question) {
    const lines = raw.split('\n').map(l => l.trim()).filter(Boolean);

    // 提取 Rufus 追问建议
    const followUps = [];
    const followUpMarkers = ['Show ', 'Best ', 'How to ', 'What ', 'Can you ', 'How much ', 'Tips for '];
    for (const line of lines) {
      if (followUpMarkers.some(m => line.includes(m)) && line.length > 10 && line.length < 100) {
        followUps.push(line.substring(0, 100));
      }
    }

    // 提取提及的品牌（常见窗帘品牌）
    const brandMatches = raw.match(/(NICETOWN|MIULEE|Yakamok|Melodieux|MICROFA|TG|Apollo|Amazon Basics)/gi) || [];
    const brands = [...new Set(brandMatches.map(b => b))];

    // 提取价格区间
    const priceMatch = raw.match(/\$\d+[\-–]?\$\d+|\$\d+\s*(per pair|each)/gi) || [];
    const prices = [...new Set(priceMatch.map(p => p.toLowerCase()))];

    return {
      question,
      raw,
      followUps: followUps.slice(0, 5),
      brands,
      prices,
      rawLength: raw.length,
    };
  }

  // ─── 保存本地 ────────────────────────────────────

  async _saveLocally(qNum, question, raw, parsed) {
    const filename = `Q${qNum}-${this.topic}.md`.replace(/[^a-zA-Z0-9.\-]/g, '_');
    const filepath = path.join(this.saveDir, filename);

    let content = `# Rufus Q${qNum}: ${question}\n\n`;
    content += `**Customer question:** ${question}\n\n---\n\n`;
    content += `**Rufus 完整回复原文：**\n\n${raw}\n\n---\n\n`;
    content += `**Rufus 追问建议（Follow-ups）：**\n`;
    for (const fu of parsed.followUps) {
      content += `- ${fu}\n`;
    }
    content += `\n**提及的品牌：** ${parsed.brands.join(', ') || '无'}\n`;
    content += `**价格区间：** ${parsed.prices.join(', ') || '无'}\n`;

    fs.writeFileSync(filepath, content, 'utf8');
    console.log(`  ✅ 已保存: ${filepath}`);
  }

  async _saveSummary(questions, results) {
    const summaryPath = path.join(this.saveDir, `SUMMARY-${this.topic}.md`);

    // 统计所有 follow-ups
    const allFollowUps = results.flatMap(r => r.followUps);
    const followUpCounts = {};
    for (const fu of allFollowUps) {
      const key = fu.substring(0, 50);
      followUpCounts[key] = (followUpCounts[key] || 0) + 1;
    }
    const topFollowUps = Object.entries(followUpCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20)
      .map(([fu, count]) => ({ fu, count }));

    // 统计所有品牌
    const allBrands = results.flatMap(r => r.brands);
    const brandCounts = {};
    for (const b of allBrands) {
      brandCounts[b] = (brandCounts[b] || 0) + 1;
    }
    const topBrands = Object.entries(brandCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([brand, count]) => ({ brand, count }));

    let content = `# Rufus 调研汇总报告: ${this.topic}\n\n`;
    content += `**调研时间：** ${new Date().toISOString().split('T')[0]}\n`;
    content += `**问题数量：** ${questions.length}\n\n`;
    content += `---\n\n`;
    content += `## 高频 Follow-up 追问（买家搜索词来源）\n\n`;
    for (const { fu, count } of topFollowUps) {
      content += `- ${fu} ${count > 1 ? `(${count}次)` : ''}\n`;
    }
    content += `\n---\n\n`;
    content += `## 竞品品牌提及统计\n\n`;
    for (const { brand, count } of topBrands) {
      content += `- ${brand}: ${count}次\n`;
    }
    content += `\n---\n\n`;
    content += `## 各问题 Rufus 回复概要\n\n`;
    for (let i = 0; i < results.length; i++) {
      const r = results[i];
      content += `### Q${i + 1}: ${r.question}\n\n`;
      content += `- 回复长度: ${r.rawLength} 字符\n`;
      content += `- 追问建议: ${r.followUps.length} 条\n`;
      content += `- 提及品牌: ${r.brands.join(', ') || '无'}\n`;
      content += `- 价格区间: ${r.prices.join(', ') || '无'}\n\n`;
    }
    content += `---\n\n`;
    content += `*报告生成于 ${new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })}*\n`;

    fs.writeFileSync(summaryPath, content, 'utf8');
    console.log(`  ✅ 汇总报告已保存: ${summaryPath}`);
  }

  // ─── WebSocket 工具 ───────────────────────────────

  async _send(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = Date.now();
      this.ws.send(JSON.stringify({ id, method, params }));
      const handler = (data) => {
        const msg = JSON.parse(data);
        if (msg.id === id) {
          this.ws.off('message', handler);
          resolve(msg.result);
        }
      };
      this.ws.on('message', handler);
      this.ws.on('error', reject);
    });
  }

  async _eval(expression) {
    const r = await this._send('Runtime.evaluate', { expression, returnByValue: true });
    return r?.result?.value || '';
  }
}

export default RufusResearchRunner;
