/* 技能库 本地编辑服务
 * 作用：启动后访问 http://localhost:8917
 *  - 页面注入编辑器（/__editor.js）
 *  - GET  /api/data  读取技能库.html 里的 DATA JSON
 *  - POST /api/data  把新的 DATA 写回 技能库.html（首次保存前自动备份）
 */
const http = require('http');
const fs = require('fs');
const path = require('path');

const FILE = path.join(__dirname, '技能库.html');
const EDITOR = path.join(__dirname, 'editor.js');
const PORT = 8917;
const MARK = 'const DATA = ';
let backedUp = false;

function extract(html) {
  const lines = html.split('\n');
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].startsWith(MARK)) {
      const end = lines[i].lastIndexOf(';');
      if (end > MARK.length) return { lineNo: i, json: lines[i].slice(MARK.length, end) };
    }
  }
  return null;
}

function send(res, code, body, type) {
  res.writeHead(code, {
    'Content-Type': type + '; charset=utf-8',
    'Cache-Control': 'no-store, no-cache, must-revalidate',
    'Pragma': 'no-cache'
  });
  res.end(body);
}

const server = http.createServer((req, res) => {
  const url = req.url.split('?')[0];
  if (req.method === 'GET' && (url === '/' || url === '/index.html')) {
    let html = fs.readFileSync(FILE, 'utf8');
    // 仅当访问 ?edit=1 时才注入编辑器；普通访问不再出现编辑模式
    const wantsEdit = /(^|[?&])edit=1(&|$)/.test(req.url);
    if (wantsEdit && !html.includes('__EB_INLINE__') && !html.includes('/__editor.js')) {
      html = html.replace('</body>', '<script src="/__editor.js"></script>\n</body>');
    }
    return send(res, 200, html, 'text/html');
  }
  if (req.method === 'GET' && url === '/__editor.js') {
    return send(res, 200, fs.readFileSync(EDITOR, 'utf8'), 'text/javascript');
  }
  if (url === '/api/data') {
    if (req.method === 'GET') {
      const found = extract(fs.readFileSync(FILE, 'utf8'));
      if (!found) return send(res, 500, JSON.stringify({ ok: false, error: '未找到 DATA 行' }), 'application/json');
      return send(res, 200, JSON.stringify({ ok: true, data: JSON.parse(found.json) }), 'application/json');
    }
    if (req.method === 'POST') {
      let body = '';
      req.on('data', c => { body += c; if (body.length > 5e6) req.destroy(); });
      req.on('end', () => {
        try {
          const data = JSON.parse(body);
          if (!data || !Array.isArray(data.packs)) throw new Error('数据缺少 packs 数组');
          let html = fs.readFileSync(FILE, 'utf8');
          const found = extract(html);
          if (!found) throw new Error('未找到 DATA 行');
          // 每次保存前滚动备份（保留最近 10 份）
          const stamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);
          fs.writeFileSync(path.join(__dirname, '技能库.backup-' + stamp + '.html'), html, 'utf8');
          const allBak = fs.readdirSync(__dirname)
            .filter(f => /^技能库\.backup-\d+\.html$/.test(f)).sort();
          while (allBak.length > 10) {
            fs.unlinkSync(path.join(__dirname, allBak.shift()));
          }
          const lines = html.split('\n');
          lines[found.lineNo] = MARK + JSON.stringify(data) + ';';
          fs.writeFileSync(FILE, lines.join('\n'), 'utf8');
          send(res, 200, JSON.stringify({ ok: true, savedAt: new Date().toLocaleTimeString('zh-CN') }), 'application/json');
        } catch (e) {
          send(res, 400, JSON.stringify({ ok: false, error: e.message }), 'application/json');
        }
      });
      return;
    }
  }
  send(res, 404, 'not found', 'text/plain');
});

server.listen(PORT, () => {
  console.log('技能库编辑服务已启动: http://localhost:' + PORT);
  console.log('原文件: ' + FILE);
});
