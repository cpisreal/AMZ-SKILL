/**
 * RufusChromeSession
 * Chrome CDP 会话封装，管理 Rufus AI 的浏览器自动化交互
 * 
 * 使用方式:
 *   const session = new RufusChromeSession();
 *   await session.launch();
 *   await session.navigate('https://www.amazon.com/s?k=curtain');
 *   const response = await session.ask('What is blackout curtain?');
 *   await session.close();
 */

import { execSync } from 'child_process';
import { WebSocket } from 'ws';

const DEFAULT_PORT = 9222;
const WAIT_MS = 8000; // Rufus 生成回复的标准等待时间

export class RufusChromeSession {
  constructor(port = DEFAULT_PORT) {
    this.port = port;
    this.ws = null;
    this.pageId = null;
    this.baseUrl = `http://127.0.0.1:${port}`;
  }

  // ─── 公开 API ───────────────────────────────────────

  /**
   * 启动 Chrome 调试模式
   * @param {number} port 调试端口，默认 9222
   */
  async launch(port = this.port) {
    this.port = port;
    this.baseUrl = `http://127.0.0.1:${port}`;

    // 1. 杀掉已有 Chrome
    try {
      execSync('pkill -f "Google Chrome" 2>/dev/null', { stdio: 'ignore' });
      await sleep(1000);
    } catch (_) {}

    // 2. 启动 Chrome 带调试端口
    execSync(
      `open /Applications/Google\\ Chrome.app --args --remote-debugging-port=${this.port} --remote-allow-origins=\\* --user-data-dir=/tmp/chrome-debug 2>&1 &`,
      { stdio: 'ignore' }
    );
    await sleep(4000);

    // 3. 验证 Chrome 已启动
    const version = await this._curl('/json/version');
    if (!version) throw new Error('Chrome 启动失败');
    
    console.log(`[RufusChrome] Chrome 启动成功，端口 ${this.port}`);
    return this;
  }

  /**
   * 导航到指定 URL，并等待页面加载完成
   * @param {string} url 目标页面 URL
   */
  async navigate(url) {
    // 如果已有连接，先关闭
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    // 创建新页面
    const newPage = await this._curl('/json/new', 'PUT');
    if (!newPage?.webSocketDebuggerUrl) throw new Error('创建新页面失败');
    
    this.pageId = newPage.id;
    this.wsUrl = newPage.webSocketDebuggerUrl;

    // 连接 WebSocket
    this.ws = new WebSocket(this.wsUrl);
    await new Promise((res, rej) => {
      this.ws.on('open', res);
      this.ws.on('error', rej);
    });

    // 导航
    await this._send('Page.navigate', { url });
    await sleep(5000); // 等页面加载

    console.log(`[RufusChrome] 已导航到: ${url}`);
    return this;
  }

  /**
   * 向 Rufus 提问并返回回复文本
   * @param {string} question 英文问题
   * @param {number} waitMs 等待时间（毫秒）
   * @returns {Promise<string>} Rufus 回复原文
   */
  async ask(question, waitMs = WAIT_MS) {
    if (!this.ws) throw new Error('未连接，请先调用 navigate()');

    // 1. 聚焦并输入问题
    await this._eval(`
      (function() {
        const ta = document.getElementById("rufus-text-area");
        if (!ta) return "INPUT_NOT_FOUND";
        ta.focus();
        ta.value = "";
        ta.dispatchEvent(new Event("input", { bubbles: true }));
        ta.value = \`${question.replace(/`/g, '\\`')}\`;
        ta.dispatchEvent(new Event("input", { bubbles: true }));
        return "TYPED";
      })()
    `);

    // 2. 按 Enter 提交
    await this._eval(`
      (function() {
        const ta = document.getElementById("rufus-text-area");
        ta.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, cancelable: true, key: "Enter", code: "Enter" }));
        return "SUBMITTED";
      })()
    `);

    // 3. 等待 Rufus 回复
    console.log(`[RufusChrome] 等待 Rufus 回复: "${question.substring(0, 50)}..."`);
    await sleep(waitMs);

    // 4. 抓取回复（从问题位置开始）
    const response = await this._eval(`
      (function() {
        const panel = document.querySelector(".nav-rufus-content");
        if (!panel) return "";
        const text = panel.textContent || "";
        const qMarker = \`${question.substring(0, 40)}\`;
        const pos = text.indexOf(qMarker);
        return pos === -1 ? text.substring(Math.max(0, text.length - 5000)) : text.substring(pos, pos + 5000);
      })()
    `);

    console.log(`[RufusChrome] 收到回复 (${response.length} 字符)`);
    return response;
  }

  /**
   * 关闭 Chrome 会话
   */
  async close() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  // ─── 私有方法 ───────────────────────────────────────

  async _curl(path, method = 'GET') {
    try {
      const url = `${this.baseUrl}${path}`;
      const result = execSync(
        `curl -s ${method === 'PUT' ? '-X PUT' : ''} "${url}"`,
        { encoding: 'utf8', maxBuffer: 10 * 1024 * 1024 }
      );
      return result ? JSON.parse(result) : null;
    } catch (_) {
      return null;
    }
  }

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

  async _eval(expression, returnByValue = true) {
    const r = await this._send('Runtime.evaluate', { expression, returnByValue });
    return r?.result?.value || '';
  }
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

export default RufusChromeSession;
