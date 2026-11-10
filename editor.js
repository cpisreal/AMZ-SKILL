/* 技能库 内嵌编辑器 v2 —— 由 edit-server.js 提供 /api/data 保存接口
 * 功能：编辑模式开关 / 卡片行内改文字 / 卡片增删 / 完整字段面板 / 标题副标题修改
 */
(function () {
  /* 诊断：脚本任何报错直接显示在页面上 */
  window.onerror = function (msg, src, line) {
    if (String(src).indexOf('editor') < 0 && document.getElementById('ebErr')) return;
    var d = document.createElement('div');
    d.style.cssText = 'position:fixed;left:12px;top:12px;z-index:9999;background:#fee;border:1px solid #d9534f;color:#a00;padding:10px 14px;border-radius:8px;font-size:12px;max-width:420px';
    d.textContent = '编辑器脚本错误: ' + msg + ' @line ' + line;
    document.body.appendChild(d);
  };
  if (document.getElementById('ebFab')) return;   // 防重复加载
  try {
    if (!DATA || !Array.isArray(DATA.packs)) return;
  } catch (e) { return; }

  /* ---------- 样式 ---------- */
  var css = `
  #ebFab{position:fixed;right:22px;bottom:22px;z-index:220;border:1px solid var(--line);
    background:#fff;border-radius:999px;padding:10px 18px;font-size:13px;font-weight:600;
    color:var(--ink2);box-shadow:var(--shadow-h);display:flex;align-items:center;gap:7px;animation:ebPulse 2.4s ease 2}
  #ebFab:hover{color:var(--ink);border-color:#c3cfe4}
  body.eb-on #ebFab{background:var(--brand);border-color:var(--brand);color:#fff;animation:none}
  @keyframes ebPulse{0%,100%{box-shadow:var(--shadow-h)}50%{box-shadow:0 0 0 6px rgba(31,79,216,.18),var(--shadow-h)}}
  .eb-bar{position:fixed;left:0;right:0;bottom:0;z-index:215;background:#132b57;color:#fff;
    display:none;align-items:center;justify-content:center;gap:10px;padding:10px 16px;font-size:13px}
  body.eb-on .eb-bar{display:flex}
  body.eb-on main{padding-bottom:84px}
  .eb-bar b{font-weight:700;margin-right:6px}
  .eb-tip{opacity:.75;font-size:12px}
  .eb-btn{border:1px solid rgba(255,255,255,.35);background:rgba(255,255,255,.12);color:#fff;
    border-radius:8px;padding:6px 13px;font-size:12.5px}
  .eb-btn:hover{background:rgba(255,255,255,.22)}
  .eb-tools{position:absolute;top:8px;right:8px;display:none;gap:5px;z-index:5}
  body.eb-on .eb-tools{display:flex}
  .eb-tbtn{width:28px;height:28px;border:1px solid var(--line);background:#fff;border-radius:7px;
    font-size:13px;line-height:1;color:var(--ink2);display:grid;place-items:center}
  .eb-tbtn:hover{border-color:var(--brand);color:var(--brand)}
  .eb-tbtn.del:hover{border-color:#d9534f;color:#d9534f}
  .eb-add{display:none;margin-left:auto;border:1px dashed var(--line);background:transparent;
    border-radius:8px;padding:4px 12px;font-size:12px;color:var(--ink3)}
  body.eb-on .eb-add{display:inline-block}
  .eb-add:hover{color:var(--brand);border-color:var(--brand)}
  .eb-secdel{margin-left:8px;font-size:10.5px;font-weight:600;color:#d9534f;background:#fff;
    border:1px solid #eec2c0;border-radius:5px;padding:1px 8px;cursor:pointer;vertical-align:middle}
  .eb-secdel:hover{background:#fdf1f0}
  body.eb-on .card h3, body.eb-on .card .tagline{outline:1px dashed rgba(31,79,216,.55);outline-offset:2px;border-radius:4px;cursor:text}
  body.eb-on .card h3:hover, body.eb-on .card .tagline:hover{outline-color:var(--brand);background:var(--brand-soft)}
  body.eb-on .card [contenteditable="true"]:focus{outline:2px solid var(--brand);background:#fff}
  .eb-mask{position:fixed;inset:0;background:rgba(14,24,40,.42);z-index:290;display:none}
  .eb-mask.on{display:block}
  .eb-panel{position:fixed;right:0;top:0;bottom:0;width:min(600px,100%);background:#fff;z-index:291;
    box-shadow:-12px 0 40px rgba(12,24,44,.16);transform:translateX(103%);transition:transform .26s cubic-bezier(.22,.8,.3,1);
    display:flex;flex-direction:column}
  .eb-panel.on{transform:translateX(0)}
  .eb-head{padding:20px 24px 14px;border-bottom:1px solid var(--line);flex:none}
  .eb-head h2{margin:0;font-size:18px;font-weight:700}
  .eb-head p{margin:4px 0 0;font-size:12.5px;color:var(--ink3)}
  .eb-body{flex:1;overflow-y:auto;padding:16px 24px 24px}
  .eb-f{margin-bottom:13px}
  .eb-f label{display:block;font-size:12px;font-weight:700;color:var(--ink3);margin-bottom:5px;letter-spacing:.5px}
  .eb-f input,.eb-f textarea,.eb-f select{width:100%;border:1px solid var(--line);border-radius:9px;
    padding:8px 11px;font-size:13px;outline:none;background:#fff;transition:.15s}
  .eb-f textarea{min-height:64px;resize:vertical;line-height:1.6}
  .eb-f input:focus,.eb-f textarea:focus,.eb-f select:focus{border-color:var(--brand);
    box-shadow:0 0 0 3px rgba(31,79,216,.10)}
  details.eb-raw summary{font-size:12px;color:var(--ink3);cursor:pointer;user-select:none;margin:14px 0 8px}
  details.eb-raw textarea{min-height:200px;font-family:ui-monospace,Consolas,monospace;font-size:11.5px}
  .eb-foot{flex:none;border-top:1px solid var(--line);padding:13px 24px;display:flex;gap:9px;justify-content:flex-end}
  .eb-foot button{border:1px solid var(--line);background:#fff;border-radius:9px;padding:9px 18px;font-size:13px}
  .eb-foot .pri{background:var(--brand);border-color:var(--brand);color:#fff;font-weight:700}
  .eb-foot .danger{color:#d9534f;border-color:#eec2c0}
  .eb-foot .danger:hover{background:#fdf1f0}`;
  var style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  /* ---------- 面板骨架 ---------- */
  var mask = document.createElement('div');
  mask.className = 'eb-mask';
  var panel = document.createElement('div');
  panel.className = 'eb-panel';
  panel.innerHTML = `
    <div class="eb-head"><h2 id="ebTitle">编辑技能</h2><p id="ebSub"></p></div>
    <div class="eb-body">
      <div class="eb-f"><label>名称 *</label><input id="ebName"></div>
      <div class="eb-f"><label>英文名 / 技能 ID（用于 workbuddy:// 调用）</label><input id="ebNameEn"></div>
      <div class="eb-f"><label>分类</label><select id="ebCat"></select>
        <div class="eb-f" style="margin-top:7px" id="ebNewCatWrap" hidden><input id="ebNewCat" placeholder="输入新分类名称"></div></div>
      <div class="eb-f"><label>一句话简介（卡片摘要）</label><textarea id="ebTagline"></textarea></div>
      <div class="eb-f"><label>标签（逗号分隔，清空即删除全部标签）</label><input id="ebTags" placeholder="关键词, 广告, 选品"></div>
      <div class="eb-f"><label>需要准备 · 输入（每行一条，删行即删除该条）</label><textarea id="ebInputs"></textarea></div>
      <div class="eb-f"><label>会拿到什么 · 产出（每行一条，删行即删除该条）</label><textarea id="ebOutputs"></textarea></div>
      <div class="eb-f"><label>这个技能解决什么 · 背景说明（清空即不在详情页显示）</label><textarea id="ebAbout" style="min-height:90px"></textarea></div>
      <div class="eb-f"><label>命令行 / 用法（清空即不显示）</label><textarea id="ebUsage" style="min-height:80px;font-family:ui-monospace,Consolas,monospace"></textarea></div>
      <div class="eb-f"><label>备注（可选）</label><textarea id="ebNote" style="min-height:52px"></textarea></div>
      <details class="eb-raw"><summary>高级：编辑该技能的完整 JSON</summary>
        <div class="eb-f"><textarea id="ebRaw" spellcheck="false"></textarea></div></details>
    </div>
    <div class="eb-foot">
      <button id="ebDel" class="danger">删除此技能</button>
      <span style="flex:1"></span>
      <button id="ebCancel">取消</button>
      <button id="ebSave" class="pri">保存并写入文件</button>
    </div>`;
  document.body.appendChild(mask);
  document.body.appendChild(panel);

  var fab = document.createElement('button');
  fab.id = 'ebFab';
  fab.type = 'button';
  fab.innerHTML = '✏️ <span>编辑模式 v3</span>';
  var bar = document.createElement('div');
  bar.className = 'eb-bar';
  bar.innerHTML = '<b>编辑模式</b>' +
    '<span class="eb-tip">点卡片上的标题 / 简介文字可直接修改，选中文字删除即可</span>' +
    '<button class="eb-btn" id="ebBarAdd" type="button">＋ 新增技能</button>' +
    '<button class="eb-btn" id="ebBarTitle" type="button">改标题/副标题</button>' +
    '<button class="eb-btn" id="ebBarExit" type="button">退出编辑</button>';
  document.body.appendChild(fab);
  document.body.appendChild(bar);

  function $id(id) { return document.getElementById(id); }
  var editIdx = -1;
  var dirty = false;

  function toast(msg) {
    if (window.toast) return window.toast(msg);
    var t = document.createElement('div');
    t.textContent = msg;
    t.style.cssText = 'position:fixed;left:50%;bottom:70px;transform:translateX(-50%);z-index:400;background:#132b57;color:#fff;padding:9px 16px;border-radius:9px;font-size:13px';
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 1900);
  }

  /* ---------- 保存 ---------- */
  var saveTimer = null;
  function scheduleSave(reason) {
    dirty = true;
    clearTimeout(saveTimer);
    saveTimer = setTimeout(function () { push(reason); }, 900);
  }
  function push(reason) {
    return fetch('/api/data', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(DATA)
    }).then(function (r) { return r.json(); }).then(function (j) {
      if (!j.ok) throw new Error(j.error || '保存失败');
      dirty = false;
      toast(reason + '（' + j.savedAt + ' 已写入文件）');
    }).catch(function (e) {
      dirty = true;
      toast('写入失败：' + e.message + '（请用「打开技能库.bat」或 localhost:8917 打开本页）');
    });
  }

  /* ---------- 行内编辑 ---------- */
  function enableInline(cardEl, i) {
    var p = DATA.packs[i];
    if (!p) return;
    var h3 = cardEl.querySelector('h3');
    var tag = cardEl.querySelector('.tagline');
    [h3, tag].forEach(function (el) {
      if (!el) return;
      el.setAttribute('contenteditable', 'true');
      el.setAttribute('spellcheck', 'false');
      /* 阻止冒泡：编辑模式下点文字只编辑，不触发页面"开详情抽屉/开面板" */
      el.__ebClick = function (e) { e.stopPropagation(); };
      el.__ebKey = function (e) {
        e.stopPropagation();
        if (e.key === 'Enter') { e.preventDefault(); el.blur(); }
      };
      el.addEventListener('click', el.__ebClick);
      el.addEventListener('keydown', el.__ebKey);
    });
    if (h3) h3.addEventListener('blur', function () {
      var v = h3.textContent.trim();
      if (v && v !== p.name) { p.name = v; scheduleSave('名称已更新'); }
    });
    if (tag) tag.addEventListener('blur', function () {
      var v = tag.textContent.trim();
      if (v !== (p.tagline || '')) { p.tagline = v; scheduleSave('简介已更新'); }
    });
  }
  function disableInline(cardEl) {
    cardEl.querySelectorAll('[contenteditable]').forEach(function (el) {
      el.removeAttribute('contenteditable');
      if (el.__ebClick) el.removeEventListener('click', el.__ebClick);
      if (el.__ebKey) el.removeEventListener('keydown', el.__ebKey);
      delete el.__ebClick; delete el.__ebKey;
    });
  }

  /* ---------- 卡片工具按钮 ---------- */
  function injectTools() {
    document.querySelectorAll('#main .card').forEach(function (cardEl) {
      var i = +cardEl.dataset.id;
      if (!cardEl.querySelector('.eb-tools')) {
        var tools = document.createElement('div');
        tools.className = 'eb-tools';
        tools.innerHTML = '<button class="eb-tbtn" title="编辑全部字段" type="button">✏️</button>' +
          '<button class="eb-tbtn del" title="删除整个技能卡片" type="button">🗑</button>';
        tools.children[0].onclick = function (e) { e.stopPropagation(); openForm(i); };
        tools.children[1].onclick = function (e) {
          e.stopPropagation();
          if (!confirm('确定删除「' + (DATA.packs[i].name || '') + '」整张卡片吗？')) return;
          DATA.packs.splice(i, 1);
          render();
          if (document.body.classList.contains('eb-on')) injectTools();
          scheduleSave('技能已删除');
          setTimeout(function () { push('技能已删除'); }, 50);
        };
        cardEl.appendChild(tools);
      }
      enableInline(cardEl, i);
    });
    document.querySelectorAll('.group-head').forEach(function (head) {
      if (head.querySelector('.eb-add')) return;
      var cat = head.querySelector('h2').textContent;
      var btn = document.createElement('button');
      btn.className = 'eb-add';
      btn.type = 'button';
      btn.textContent = '＋ 添加到此分类';
      btn.onclick = function () { openForm(-1, cat); };
      head.appendChild(btn);
    });
  }
  function removeTools() {
    document.querySelectorAll('.eb-tools').forEach(function (x) { x.remove(); });
    document.querySelectorAll('.eb-add').forEach(function (x) { x.remove(); });
    document.querySelectorAll('#main .card').forEach(disableInline);
  }

  /* render 由页面生成卡片，包装一层：编辑模式下每次渲染后重新挂编辑控件 */
  try {
    var origRender = render;
    render = function () {
      origRender();
      if (document.body.classList.contains('eb-on')) injectTools();
    };
  } catch (e) {}

  /* ---------- 详情抽屉：编辑模式下给各段落加"删除此段"按钮 ---------- */
  function ebOn() { return document.body.classList.contains('eb-on'); }
  var origOpenDrawerRef = null;
  try {
    origOpenDrawerRef = openDrawer;
    var SEC_FIELD = {
      '这个技能解决什么': 'about',
      '命令行 / 用法': 'usage',
      '需要准备': 'inputs',
      '会拿到什么': 'outputs_list'
    };
    var origSection = section;
    section = function (title, body) {
      var html = origSection(title, body);
      if (ebOn() && SEC_FIELD[title]) {
        html = html.replace('<h4>',
          '<h4><button class="eb-secdel" type="button" data-ebfield="' + SEC_FIELD[title] + '">✕ 删除此段</button>');
      }
      return html;
    };
  } catch (e) {}

  /* 抽屉内"删除此段"点击（事件委托，抽屉内容每次重绘都生效） */
  document.addEventListener('click', function (e) {
    var b = e.target.closest ? e.target.closest('.eb-secdel') : null;
    if (!b) return;
    e.stopPropagation(); e.preventDefault();
    var p = null;
    try { p = state.current; } catch (err) {}   /* state 是页面 let 声明，不在 window 上 */
    if (!p) return;
    var f = b.getAttribute('data-ebfield');
    if (f === 'inputs' || f === 'outputs_list') delete p[f];
    else p[f] = '';
    dirty = true;
    render();
    if (ebOn() && origOpenDrawerRef) {
      var idx = -1;
      for (var k = 0; k < DATA.packs.length; k++) if (DATA.packs[k] === p) { idx = k; break; }
      if (idx >= 0) origOpenDrawerRef(idx);
    }
    scheduleSave('段落已删除');
    setTimeout(function () { push('段落已删除'); }, 50);
  });

  /* 编辑模式下点卡片 = 打开详情抽屉（抽屉里有"删除此段"按钮；点标题/简介文字则是行内改字） */

  /* ---------- 模式开关 ---------- */
  function setMode(on) {
    document.body.classList.toggle('eb-on', on);
    if (on) {
      injectTools();
      /* 环境自检：测试 contenteditable 能否聚焦 */
      var t = document.createElement('div');
      t.contentEditable = 'true';
      t.style.cssText = 'position:fixed;left:-9999px;top:0;height:8px;width:8px';
      document.body.appendChild(t);
      try { t.focus(); } catch (e) {}
      var ok = (document.activeElement === t);
      t.remove();
      if (ok) toast('编辑模式已开启：点卡片标题/简介的虚线框文字，直接改字');
      else toast('编辑模式已开启，但当前环境禁止文字编辑——请用 Chrome/Edge 打开 localhost:8917，或在预览面板里点“在浏览器打开”');
    } else removeTools();
  }
  fab.addEventListener('click', function () { setMode(!document.body.classList.contains('eb-on')); });
  $id('ebBarExit').onclick = function () {
    if (dirty) { push('已保存全部修改'); }
    setMode(false);
  };
  $id('ebBarAdd').onclick = function () {
    var c = prompt('新技能归入哪个分类？', (DATA.cats || [])[0] || '');
    if (c === null) return;
    openForm(-1, c.trim());
  };
  $id('ebBarTitle').onclick = function () {
    var t = prompt('页面主标题', DATA.title || '');
    if (t === null) return;
    DATA.title = t.trim();
    var el = document.getElementById('title');
    if (el) el.textContent = DATA.title;
    document.title = DATA.title;
    var s = prompt('副标题（来源说明，留空保持不变）', DATA.source || '');
    if (s !== null && s.trim()) {
      DATA.source = s.trim();
      var sub = document.getElementById('subtitle');
      if (sub) sub.textContent = '从 ' + DATA.source + ' 整理 · 可搜索 / 可复制 / 可直接调用';
    }
    scheduleSave('标题已更新');
    setTimeout(function () { push('标题已更新'); }, 50);
  };

  /* ---------- 完整字段面板 ---------- */
  function fillCatOptions() {
    var set = [];
    (DATA.cats || []).concat(DATA.packs.map(function (p) { return p.cat; })).forEach(function (c) {
      if (c && set.indexOf(c) < 0) set.push(c);
    });
    $id('ebCat').innerHTML = set.map(function (c) {
      return '<option>' + c.replace(/</g, '&lt;') + '</option>';
    }).join('') + '<option value="__new__">＋ 新分类…</option>';
  }

  function openForm(idx, presetCat) {
    editIdx = idx;
    var isNew = idx < 0;
    var p = isNew
      ? { name: '新技能', cat: presetCat || (DATA.cats || [])[0] || '未分类', tagline: '', tags: [],
          inputs: [], outputs_list: [], installed: false, size_kb: 0, rel: '' }
      : DATA.packs[idx];
    $id('ebTitle').textContent = isNew ? '新增技能' : '编辑技能';
    $id('ebSub').textContent = isNew ? '保存后立即写入 技能库.html' : (p.name || '') + ' · ' + (p.cat || '');
    $id('ebName').value = p.name || '';
    $id('ebNameEn').value = p.name_en || '';
    fillCatOptions();
    var known = (DATA.cats || []).indexOf(p.cat) >= 0 || DATA.packs.some(function (x) { return x.cat === p.cat; });
    $id('ebCat').value = known ? p.cat : '__new__';
    $id('ebNewCatWrap').hidden = $id('ebCat').value !== '__new__';
    $id('ebNewCat').value = ($id('ebCat').value === '__new__') ? (p.cat || '') : '';
    $id('ebTagline').value = p.tagline || '';
    $id('ebTags').value = (p.tags || []).join(', ');
    $id('ebInputs').value = (p.inputs || []).join('\n');
    $id('ebOutputs').value = (p.outputs_list || []).join('\n');
    $id('ebAbout').value = p.about || '';
    $id('ebUsage').value = p.usage || '';
    $id('ebNote').value = p.note || '';
    $id('ebRaw').value = JSON.stringify(p, null, 2);
    $id('ebDel').style.display = isNew ? 'none' : '';
    mask.classList.add('on');
    panel.classList.add('on');
  }
  function closeForm() { mask.classList.remove('on'); panel.classList.remove('on'); }

  function collectForm() {
    var base = editIdx >= 0 ? DATA.packs[editIdx] : {};
    var rawObj = null;
    try {
      rawObj = JSON.parse($id('ebRaw').value);
      if (JSON.stringify(rawObj) === JSON.stringify(base)) rawObj = null;
    } catch (e) {
      rawObj = null;
      toast('高级 JSON 语法有误，本次仅保存表单字段');
    }
    if (rawObj) base = rawObj;
    var cat = $id('ebCat').value === '__new__'
      ? ($id('ebNewCat').value.trim() || base.cat || '未分类')
      : $id('ebCat').value;
    var next = {};
    for (var k in base) next[k] = base[k];
    next.name = $id('ebName').value.trim() || base.name || '未命名技能';
    if ($id('ebNameEn').value.trim()) next.name_en = $id('ebNameEn').value.trim(); else delete next.name_en;
    next.cat = cat;
    next.tagline = $id('ebTagline').value.trim();
    next.tags = $id('ebTags').value.split(/[,，;；]/).map(function (s) { return s.trim(); }).filter(Boolean);
    next.inputs = $id('ebInputs').value.split('\n').map(function (s) { return s.trim(); }).filter(Boolean);
    next.outputs_list = $id('ebOutputs').value.split('\n').map(function (s) { return s.trim(); }).filter(Boolean);
    next.about = $id('ebAbout').value.trim();
    next.usage = $id('ebUsage').value.trim();
    if ($id('ebNote').value.trim()) next.note = $id('ebNote').value.trim(); else delete next.note;
    try {
      if (!CAT_COLOR[cat]) CAT_COLOR[cat] = '#64748b';
    } catch (e) {}
    if (!DATA.cats.includes(cat)) {
      DATA.cats.push(cat);
      try { cats.push(cat); } catch (e) {}
    }
    return next;
  }

  $id('ebCat').addEventListener('change', function (e) {
    $id('ebNewCatWrap').hidden = e.target.value !== '__new__';
    if (e.target.value !== '__new__') $id('ebNewCat').value = '';
  });

  $id('ebSave').onclick = function () {
    var next = collectForm();
    if (editIdx >= 0) DATA.packs[editIdx] = next; else DATA.packs.push(next);
    closeForm();
    render();
    push(editIdx >= 0 ? '技能已更新' : '技能已新增');
  };
  $id('ebCancel').onclick = closeForm;
  mask.onclick = closeForm;
  $id('ebDel').onclick = function () {
    if (editIdx < 0) return;
    if (!confirm('确定删除「' + (DATA.packs[editIdx].name || '') + '」吗？')) return;
    DATA.packs.splice(editIdx, 1);
    closeForm();
    render();
    if (document.body.classList.contains('eb-on')) injectTools();
    push('技能已删除');
  };

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && panel.classList.contains('on')) closeForm();
  });
})();
