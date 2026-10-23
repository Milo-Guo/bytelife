/* ByteLife 写作页：左边 Markdown 源代码，右边按网站样式实时预览，两边滚动一一对应。
   本机自动保存，可以存版本、对比、恢复；连接 GitHub 令牌后一键提交，不连接也能复制到 GitHub 网页提交。
   令牌只放在这个页面的内存里，只发给 api.github.com。预览只经过下面这一个 Trusted Types 策略写进页面。 */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const data = JSON.parse($('editor-data').textContent);
  const API = 'https://api.github.com';
  const REPO = data.repo;
  const BRANCH = data.branch;
  const SITE = `https://github.com/${REPO}`;
  const STORE = 'bytelife-editor:v1:';
  const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
  const policy = window.trustedTypes ? window.trustedTypes.createPolicy('bytelife-preview', { createHTML: html => html }) : null;

  const els = {
    select: $('ed-article'), status: $('ed-status'), text: $('ed-text'), mirror: $('ed-mirror'), panes: $('ed-panes'),
    preview: $('ed-preview'), head: $('ed-head'), body: $('ed-body'), meta: $('ed-meta'), info: $('ed-info'),
  };
  const field = {
    title: $('m-title'), summary: $('m-summary'), category: $('m-category'), type: $('m-type'),
    updated: $('m-updated'), draft: $('m-draft'), servings: $('m-servings'), minutes: $('m-minutes'),
  };
  const state = { slug: null, isNew: false, base: null, token: null, login: null, catalog: data.articles.slice(), lineTops: [], anchors: [] };

  /* ---------- 小工具 ---------- */
  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }
  function button(label, onClick, className = 'button') {
    const node = el('button', className, label);
    node.type = 'button';
    node.addEventListener('click', onClick);
    return node;
  }
  function link(label, href) {
    const node = el('a', 'text-link', label);
    node.href = href;
    node.target = '_blank';
    node.rel = 'noopener';
    return node;
  }
  const escapeHtml = value => String(value).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const today = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  const clock = time => new Date(time).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  function setStatus(text, kind = '') {
    els.status.textContent = text;
    els.status.dataset.kind = kind;
  }
  function decodeBase64(value) {
    const binary = atob(value.replace(/\s/g, ''));
    return new TextDecoder().decode(Uint8Array.from(binary, c => c.charCodeAt(0)));
  }

  /* ---------- 预览：和 build.py 同一套规则 ---------- */
  const md = window.markdownit('commonmark', { html: true }).enable(['table', 'strikethrough']);

  function safeUrl(url) {
    const cleaned = url.replace(/^[\x00-\x20]+|[\x00-\x20]+$/g, '').replace(/[\t\n\r]/g, '');
    const scheme = /^([a-z][a-z0-9+.-]*):/i.exec(cleaned);
    return scheme && !['http', 'https', 'mailto'].includes(scheme[1].toLowerCase()) ? null : cleaned;
  }
  function convertLink(url) {
    let match = /^(?:\.\.\/)?content\/([^/#]+)\.md(.*)$/.exec(url);
    if (match) return `${data.base}articles/${match[1]}/${match[2]}`;
    match = /^(?:\.\.\/)?archive\/([^/#]+)\.md(.*)$/.exec(url);
    if (match) return `${data.base}archive/${match[1]}/${match[2]}`;
    return url.startsWith('../assets/') ? data.base + url.slice(3) : url;
  }
  function dropAttr(token, name) { token.attrs = (token.attrs || []).filter(([key]) => key !== name); }

  // 原生 HTML：只保留不带属性的排版标签和链接，其余按文字显示并提示“发布时会去掉”，预览里也不会执行脚本。
  const SIMPLE_TAG = /^<\/?(abbr|b|br|code|del|details|div|em|i|ins|kbd|mark|p|small|span|strong|sub|summary|sup|u)\s*\/?>$/i;
  function rawHtml(content) {
    return content.split(/(<!--[\s\S]*?-->|<[^>]*>)/).map(part => {
      if (!part || part.startsWith('<!--')) return '';
      if (!part.startsWith('<')) return part.replace(/</g, '&lt;');
      if (SIMPLE_TAG.test(part)) return part.replace(/\s*\/?>$/, '>');
      if (/^<\/a\s*>$/i.test(part) || /^<a\s+(name|id)\s*=\s*"[^"]*"\s*>$/i.test(part)) return part.startsWith('</') ? '</a>' : '<a>';
      const href = /^<a\s+href\s*=\s*"([^"]*)"\s*>$/i.exec(part);
      if (href) {
        const url = safeUrl(convertLink(href[1]));
        return url === null ? '<a>' : `<a href="${escapeHtml(url)}" target="_blank" rel="noopener">`;
      }
      return `<code class="raw-html" title="发布时这段 HTML 会被去掉">${escapeHtml(part)}</code>`;
    }).join('');
  }
  md.renderer.rules.html_block = (tokens, i) => `<div data-line="${tokens[i].map ? tokens[i].map[0] : ''}">${rawHtml(tokens[i].content)}</div>\n`;
  md.renderer.rules.html_inline = (tokens, i) => rawHtml(tokens[i].content);
  md.renderer.rules.bl_raw = (tokens, i) => tokens[i].content;
  md.renderer.rules.fence = md.renderer.rules.code_block = (tokens, i) => {
    const token = tokens[i];
    const lang = (token.info || '').trim().split(/\s+/)[0] || '';
    const label = data.languages[lang.toLowerCase()] || lang || '代码';
    const css = /^[\w+#.-]{1,30}$/.test(lang) ? ` class="language-${escapeHtml(lang.toLowerCase())}"` : '';
    return `<div class="code-block" data-line="${token.map ? token.map[0] : ''}"><div class="code-head"><span class="code-lang">${escapeHtml(label)}</span></div>`
      + `<pre><code${css}>${escapeHtml(token.content)}</code></pre></div>\n`;
  };

  function onlyChild(tokens, i, kind) {
    if (!tokens[i] || tokens[i].type !== 'paragraph_open' || i + 2 >= tokens.length) return null;
    const kids = (tokens[i + 1].children || []).filter(c => !((c.type === 'text' || c.type === 'softbreak') && !c.content.trim()));
    if (kind === 'image') return kids.length === 1 && kids[0].type === 'image' ? kids[0] : null;
    const opens = kids.filter(c => c.type === 'em_open').length;
    return kids.length && kids[0].type === 'em_open' && kids[kids.length - 1].type === 'em_close' && opens === 1 ? kids : null;
  }
  const ANCHOR_ONLY = /^\s*(?:<div>\s*)?<a\s+(?:name|id)="[^"]*"\s*>\s*<\/a>\s*(?:<\/div>\s*)?$/i;

  // 统一配图、提示框、表格结构，和网站正文一致；每个块带上源代码行号，用来对齐滚动。
  function decorate(tokens, state) {
    const raw = content => { const token = new state.Token('bl_raw', '', 0); token.content = content; return token; };
    const out = [];
    for (let i = 0; i < tokens.length; i++) {
      const token = tokens[i];
      if (token.type === 'html_block' && ANCHOR_ONLY.test(token.content)) continue;
      if (token.type === 'paragraph_open' && tokens[i + 1] && ANCHOR_ONLY.test((tokens[i + 1].children || []).map(c => c.content).join(''))) { i += 2; continue; }
      const image = onlyChild(tokens, i, 'image');
      if (image) {
        const inline = tokens[i + 1];
        inline.children = [raw(`<a class="figure-link" href="${escapeHtml(image.attrGet('src') || '')}" target="_blank" rel="noopener">`), image, raw('</a>')];
        out.push(raw(`<figure class="figure" data-line="${token.map ? token.map[0] : ''}">`), inline);
        i += 2;
        const caption = onlyChild(tokens, i + 1, 'caption');
        if (caption) {
          caption[0].hidden = caption[caption.length - 1].hidden = true;
          out.push(raw('<figcaption>'), tokens[i + 2], raw('</figcaption>'));
          i += 3;
        }
        out.push(raw('</figure>\n'));
        continue;
      }
      if (token.type === 'blockquote_open' && tokens[i + 2] && tokens[i + 2].type === 'inline') {
        const kids = tokens[i + 2].children || [];
        const match = kids[0] && kids[0].type === 'text' ? /^\[!(\w+)\]\s*/.exec(kids[0].content) : null;
        const kind = match && match[1].toUpperCase();
        if (kind && data.callouts[kind]) {
          kids[0].content = kids[0].content.slice(match[0].length);
          if (!kids[0].content && kids[1] && kids[1].type === 'softbreak') kids.splice(0, 2);
          token.attrJoin('class', `callout callout-${kind.toLowerCase()}`);
          out.push(token, raw(`<p class="callout-title">${escapeHtml(data.callouts[kind])}</p>\n`));
          continue;
        }
      }
      if (token.type === 'table_open') {
        let columns = 0;
        for (let j = i + 1; j < tokens.length && tokens[j].type !== 'tr_close'; j++) columns += tokens[j].type === 'th_open' || tokens[j].type === 'td_open';
        out.push(raw(`<div class="table-wrap${columns === 2 ? ' is-pair' : ''}">`));
      }
      out.push(token);
      if (token.type === 'table_close') out.push(raw('</div>\n'));
    }
    return out;
  }

  md.core.ruler.push('bytelife', state => {
    const walk = tokens => {
      for (const token of tokens) {
        if (token.type === 'link_open') {
          const href = safeUrl(convertLink(token.attrGet('href') || ''));
          if (href === null) dropAttr(token, 'href'); else { token.attrSet('href', href); token.attrSet('target', '_blank'); token.attrSet('rel', 'noopener'); }
        }
        if (token.type === 'image') {
          const src = safeUrl(convertLink(token.attrGet('src') || ''));
          if (src === null) dropAttr(token, 'src'); else token.attrSet('src', src);
          token.attrSet('loading', 'lazy');
        }
        if ((token.type === 'th_open' || token.type === 'td_open') && token.attrGet('style')) {
          const align = /text-align:(left|center|right)/.exec(token.attrGet('style'));
          dropAttr(token, 'style');
          if (align) token.attrSet('class', `align-${align[1]}`);
        }
        if (token.children) walk(token.children);
      }
    };
    walk(state.tokens);
    for (const token of state.tokens) if (token.map && token.nesting === 1) token.attrSet('data-line', String(token.map[0]));
    state.tokens = decorate(state.tokens, state);
  });

  function renderHead(meta) {
    const kicker = el('div', 'article-kicker');
    kicker.append(el('span', 'badge', meta.category || '分类'));
    if (meta.draft) kicker.append(el('span', 'badge badge-draft', '草稿 · 未发布'));
    const facts = el('p', 'article-meta');
    facts.append(el('span', null, 'Milo Guo'), el('span', null, `发布 ${meta.created}`), el('span', null, `更新 ${meta.updated}`));
    if (meta.recipe && meta.recipe.servings) facts.append(el('span', null, meta.recipe.servings));
    if (meta.recipe && meta.recipe.minutes) facts.append(el('span', null, `约 ${meta.recipe.minutes} 分钟`));
    els.head.replaceChildren(kicker, el('h1', null, meta.title || '（还没有标题）'), el('p', 'article-summary', meta.summary), facts);
  }

  let renderTimer = 0;
  function renderPreview() {
    clearTimeout(renderTimer);
    const html = md.render(els.text.value);
    els.body.innerHTML = policy ? policy.createHTML(html) : html;
    renderHead(readMeta());
    measure();
    markCurrent();
  }
  const renderSoon = () => { clearTimeout(renderTimer); renderTimer = setTimeout(renderPreview, 150); };

  /* ---------- 两边滚动对应 ---------- */
  // 用一个隐藏的镜像层量出每一行源代码的位置，再和预览里带行号的块对齐，中间按比例插值。
  function measure() {
    const lines = els.text.value.split('\n');
    els.mirror.style.width = `${els.text.clientWidth}px`;
    const fragment = document.createDocumentFragment();
    for (const line of lines) fragment.append(el('div', null, line || '​'));
    els.mirror.replaceChildren(fragment);
    const tops = [];
    for (const node of els.mirror.children) tops.push(node.offsetTop);
    tops.push(els.mirror.scrollHeight);
    state.lineTops = tops;
    const origin = els.preview.getBoundingClientRect().top - els.preview.scrollTop;
    const anchors = [];
    for (const node of els.body.querySelectorAll('[data-line]')) {
      if (node.dataset.line === '') continue;
      const line = Number(node.dataset.line);
      const top = node.getBoundingClientRect().top - origin;
      const last = anchors[anchors.length - 1];
      if (!last || (line > last.line && top >= last.top)) anchors.push({ line, top, node });
    }
    state.anchors = anchors;
  }
  const lineY = line => state.lineTops[Math.min(line, state.lineTops.length - 1)] || 0;
  function between(list, value, key) {
    let lo = -1, hi = list.length;
    while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (list[mid][key] <= value) lo = mid; else hi = mid; }
    return lo;
  }
  const ignore = { text: 0, preview: 0 };
  function scrollTo(pane, name, top) {
    const max = pane.scrollHeight - pane.clientHeight;
    const next = Math.max(0, Math.min(max, top));
    if (Math.abs(pane.scrollTop - next) < 2) return;
    ignore[name] = performance.now() + 120;
    pane.scrollTop = next;
  }
  function syncFromText() {
    const text = els.text, list = state.anchors;
    if (!list.length) return;
    if (text.scrollTop + text.clientHeight >= text.scrollHeight - 2) return scrollTo(els.preview, 'preview', els.preview.scrollHeight);
    const y = text.scrollTop + 12;
    const points = list.map(a => ({ y: lineY(a.line), top: a.top }));
    const k = between(points, y, 'y');
    const prev = points[k] || { y: 0, top: 0 };
    const next = points[k + 1] || { y: text.scrollHeight, top: els.preview.scrollHeight };
    const t = (y - prev.y) / Math.max(1, next.y - prev.y);
    scrollTo(els.preview, 'preview', prev.top + t * (next.top - prev.top) - 12);
  }
  function syncFromPreview() {
    const pane = els.preview, list = state.anchors;
    if (!list.length) return;
    if (pane.scrollTop + pane.clientHeight >= pane.scrollHeight - 2) return scrollTo(els.text, 'text', els.text.scrollHeight);
    const y = pane.scrollTop + 12;
    const k = between(list, y, 'top');
    const prev = list[k] ? { top: list[k].top, y: lineY(list[k].line) } : { top: 0, y: 0 };
    const next = list[k + 1] ? { top: list[k + 1].top, y: lineY(list[k + 1].line) } : { top: pane.scrollHeight, y: els.text.scrollHeight };
    const t = (y - prev.top) / Math.max(1, next.top - prev.top);
    scrollTo(els.text, 'text', prev.y + t * (next.y - prev.y) - 12);
  }
  let frame = 0;
  const onScroll = (name, sync) => () => {
    if (performance.now() < ignore[name]) return;
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(sync);
  };
  els.text.addEventListener('scroll', onScroll('text', syncFromText), { passive: true });
  els.preview.addEventListener('scroll', onScroll('preview', syncFromPreview), { passive: true });

  // 光标所在的段落在预览里标出来；点预览里的段落，光标跳到对应的源代码行。
  function caretLine() { return els.text.value.slice(0, els.text.selectionStart).split('\n').length - 1; }
  function markCurrent() {
    const line = caretLine();
    let current = null;
    for (const anchor of state.anchors) { if (anchor.line <= line) current = anchor.node; else break; }
    for (const node of els.body.querySelectorAll('.is-current')) if (node !== current) node.classList.remove('is-current');
    current?.classList.add('is-current');
  }
  ['keyup', 'click', 'select'].forEach(type => els.text.addEventListener(type, markCurrent));
  els.body.addEventListener('click', event => {
    if (event.target.closest('a')) return;
    const node = event.target.closest('[data-line]');
    if (!node || node.dataset.line === '') return;
    const line = Number(node.dataset.line);
    const offset = els.text.value.split('\n').slice(0, line).reduce((sum, text) => sum + text.length + 1, 0);
    els.text.focus({ preventScroll: true });
    els.text.setSelectionRange(offset, offset);
    scrollTo(els.text, 'text', lineY(line) - els.text.clientHeight / 3);
    markCurrent();
  });
  let resizeTimer = 0;
  const measureSoon = () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(measure, 120); };
  new ResizeObserver(measureSoon).observe(els.text);
  els.body.addEventListener('load', measureSoon, true);   // 预览里的图片加载完，位置会变

  /* ---------- 文章信息 ---------- */
  function readMeta() {
    const base = (state.base && state.base.meta) || {};
    const minutes = parseInt(field.minutes.value, 10);
    const meta = {
      slug: state.slug, title: field.title.value.trim(), category: field.category.value.trim(), type: field.type.value,
      summary: field.summary.value.trim(), created: base.created || state.created || today(), updated: field.updated.value || today(),
      draft: field.draft.checked,
    };
    if (meta.type === 'recipe') {
      const recipe = {};
      if (field.servings.value.trim()) recipe.servings = field.servings.value.trim();
      if (minutes > 0) recipe.minutes = minutes;
      if (Object.keys(recipe).length) meta.recipe = recipe;
    }
    return meta;
  }
  function fillMeta(meta) {
    field.title.value = meta.title || '';
    field.summary.value = meta.summary || '';
    field.category.value = meta.category || '';
    field.type.value = meta.type || 'tutorial';
    field.updated.value = meta.updated || today();
    field.draft.checked = Boolean(meta.draft);
    field.servings.value = (meta.recipe && meta.recipe.servings) || '';
    field.minutes.value = (meta.recipe && meta.recipe.minutes) || '';
    els.meta.dataset.type = field.type.value;
    state.created = meta.created || today();
  }
  const compareMeta = meta => {
    const { slug, title, category, type, summary, created, updated, draft = false, recipe = null } = meta || {};
    return { slug, title, category, type, summary, created, updated, draft: Boolean(draft), recipe: recipe || null };
  };
  function problems(meta) {
    const list = [];
    if (!SLUG.test(meta.slug || '')) list.push('英文名只能用小写字母、数字和连字符');
    if (!meta.title) list.push('标题不能为空');
    if (!meta.summary) list.push('摘要不能为空');
    if (!meta.category || meta.category === data.all) list.push(`分类不能为空，也不能叫“${data.all}”`);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(meta.updated) || meta.updated < meta.created) list.push('更新日期不能早于发布日期');
    if (!els.text.value.trim()) list.push('正文是空的');
    return list;
  }
  Object.values(field).forEach(input => input.addEventListener('input', () => {
    els.meta.dataset.type = field.type.value;
    renderHead(readMeta());
    changed();
  }));
  els.info.addEventListener('click', () => {
    const open = els.meta.hidden;
    els.meta.hidden = !open;
    els.info.setAttribute('aria-expanded', String(open));
    if (open) field.title.focus();
    requestAnimationFrame(measure);
  });

  /* ---------- 本机保存和版本 ---------- */
  function readRecord(slug = state.slug) {
    try { return JSON.parse(localStorage.getItem(STORE + slug)) || { snapshots: [] }; } catch { return { snapshots: [] }; }
  }
  function writeRecord(record, slug = state.slug) {
    record.snapshots = record.snapshots || [];
    for (;;) {
      try { localStorage.setItem(STORE + slug, JSON.stringify(record)); return true; } catch {
        if (!record.snapshots.length) return false;
        record.snapshots.shift();   // 空间不够时先丢最早的版本
      }
    }
  }
  const dirty = () => Boolean(state.base) && (state.isNew || els.text.value !== state.base.text || !same(compareMeta(readMeta()), compareMeta(state.base.meta)));
  function snapshot(label, record = readRecord()) {
    const text = els.text.value, meta = readMeta();
    const last = record.snapshots[record.snapshots.length - 1];
    if (last && last.text === text && same(last.meta, meta)) {
      // 内容和最近一个版本相同就不重复存；手动保存时把它标成手动保存，方便在列表里找到。
      if (label === '手动保存') Object.assign(last, { label, at: Date.now() });
      return record;
    }
    record.snapshots.push({ at: Date.now(), label, text, meta });
    record.snapshots = record.snapshots.slice(-20);
    return record;
  }
  function saveLocal() {
    clearTimeout(saveTimer);
    if (!state.slug || !state.base) return;
    const record = readRecord();
    if (dirty()) {
      record.working = { text: els.text.value, meta: readMeta(), baseSha: state.base.sha, at: Date.now() };
      const last = record.snapshots[record.snapshots.length - 1];
      if (!last || Date.now() - last.at > 5 * 60 * 1000) snapshot('自动保存', record);
    } else delete record.working;
    record.isNew = state.isNew;
    const ok = writeRecord(record);
    updateStatus(ok ? Date.now() : null);
  }
  let saveTimer = 0;
  function changed() { renderSoon(); clearTimeout(saveTimer); saveTimer = setTimeout(saveLocal, 800); updateStatus(); }
  function updateStatus(savedAt) {
    if (!state.base) return;
    const who = state.login ? ` · 已连接 @${state.login}` : '';
    if (state.isNew) setStatus(`新文章，还没提交到 GitHub${savedAt ? ` · 已存到本机 ${clock(savedAt)}` : ''}${who}`, 'dirty');
    else if (dirty()) setStatus(`有未提交的修改${savedAt ? ` · 已存到本机 ${clock(savedAt)}` : ''}${who}`, 'dirty');
    else setStatus(`和 GitHub 上的版本一致${who}`, 'clean');
  }
  els.text.addEventListener('input', changed);
  addEventListener('pagehide', saveLocal);
  document.addEventListener('visibilitychange', () => { if (document.hidden) saveLocal(); });
  document.addEventListener('keydown', event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
      event.preventDefault();
      writeRecord(snapshot('手动保存'));
      saveLocal();
      setStatus(`已在本机存了一个版本 · ${clock(Date.now())}`, 'clean');
    }
  });

  // 逐行对比：先去掉首尾相同的部分，中间用最长公共子序列。
  function diffLines(before, after) {
    const a = before.split('\n'), b = after.split('\n');
    let start = 0;
    while (start < a.length && start < b.length && a[start] === b[start]) start++;
    let endA = a.length, endB = b.length;
    while (endA > start && endB > start && a[endA - 1] === b[endB - 1]) { endA--; endB--; }
    const midA = a.slice(start, endA), midB = b.slice(start, endB);
    let middle = [];
    if (midA.length * midB.length > 4e6) middle = [...midA.map(t => ['-', t]), ...midB.map(t => ['+', t])];
    else {
      const n = midA.length, m = midB.length, table = new Uint32Array((n + 1) * (m + 1));
      for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) {
        table[i * (m + 1) + j] = midA[i] === midB[j] ? table[(i + 1) * (m + 1) + j + 1] + 1 : Math.max(table[(i + 1) * (m + 1) + j], table[i * (m + 1) + j + 1]);
      }
      let i = 0, j = 0;
      while (i < n || j < m) {
        if (i < n && j < m && midA[i] === midB[j]) { middle.push([' ', midA[i]]); i++; j++; }
        else if (i < n && (j === m || table[(i + 1) * (m + 1) + j] >= table[i * (m + 1) + j + 1])) middle.push(['-', midA[i++]]);
        else middle.push(['+', midB[j++]]);
      }
    }
    return [...a.slice(0, start).map(t => [' ', t]), ...middle, ...a.slice(endA).map(t => [' ', t])];
  }
  function diffView(before, after, beforeLabel, afterLabel) {
    const rows = diffLines(before, after);
    const added = rows.filter(r => r[0] === '+').length, removed = rows.filter(r => r[0] === '-').length;
    const box = el('div', 'ed-diff');
    box.append(el('p', 'ed-diff-sum', added || removed ? `${beforeLabel} → ${afterLabel}：新增 ${added} 行，删除 ${removed} 行` : '两个版本的正文完全一样'));
    const list = el('div', 'ed-diff-lines');
    let lineA = 0, lineB = 0;
    rows.forEach(([kind, text], index) => {
      if (kind === ' ') { lineA++; lineB++; } else if (kind === '-') lineA++; else lineB++;
      const near = rows.slice(Math.max(0, index - 3), index + 4).some(r => r[0] !== ' ');
      if (kind === ' ' && !near) {
        if (list.lastChild && list.lastChild.classList.contains('ed-diff-skip')) list.lastChild.dataset.count = Number(list.lastChild.dataset.count) + 1;
        else { const skip = el('div', 'ed-diff-skip'); skip.dataset.count = 1; list.append(skip); }
        return;
      }
      const row = el('div', `ed-diff-row ed-diff-${kind === '+' ? 'add' : kind === '-' ? 'del' : 'same'}`);
      row.append(el('span', 'ed-diff-no', kind === '+' ? '' : lineA), el('span', 'ed-diff-no', kind === '-' ? '' : lineB),
        el('span', 'ed-diff-mark', kind), el('span', 'ed-diff-text', text || ' '));
      list.append(row);
    });
    for (const skip of list.querySelectorAll('.ed-diff-skip')) skip.textContent = `…… ${skip.dataset.count} 行没有变化 ……`;
    box.append(list);
    return box;
  }

  /* ---------- 对话框 ---------- */
  const dialog = el('dialog', 'ed-dialog');
  document.body.append(dialog);
  function openDialog(title, build) {
    const head = el('div', 'ed-dialog-head');
    head.append(el('h2', null, title), button('关闭', () => dialog.close(), 'button'));
    const body = el('div', 'ed-dialog-body');
    dialog.replaceChildren(head, body);
    build(body);
    if (!dialog.open) dialog.showModal();
    return body;
  }
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });

  function restore(text, meta, label) {
    writeRecord(snapshot('恢复前的内容'));
    els.text.value = text;
    if (meta) fillMeta({ ...readMeta(), ...meta, slug: state.slug });
    renderPreview();
    saveLocal();
    setStatus(`已恢复：${label}（恢复前的内容存成了一个本机版本）`, 'dirty');
  }

  async function openVersions() {
    const record = readRecord();
    const body = openDialog('版本', () => {});
    const local = el('section', 'ed-section');
    local.append(el('h3', null, '本机保存的版本'), el('p', 'ed-hint', '自动保存每 5 分钟留一个版本，按 Ctrl+S 随时存一个。只保存在这台电脑的浏览器里。'));
    const save = button('现在存一个版本', () => { writeRecord(snapshot('手动保存')); openVersions(); });
    local.append(save);
    const items = el('ol', 'ed-versions');
    [...record.snapshots].reverse().forEach(item => {
      const row = el('li');
      row.append(el('span', 'ed-version-time', clock(item.at)), el('span', 'ed-version-label', `${item.label} · ${item.text.length} 字`));
      row.append(button('对比', () => showDiff(item.text, `本机 ${clock(item.at)}`)), button('恢复', () => { restore(item.text, item.meta, `本机 ${clock(item.at)}`); dialog.close(); }));
      items.append(row);
    });
    if (!record.snapshots.length) items.append(el('li', 'ed-empty', '还没有本机版本。'));
    local.append(items);

    const remote = el('section', 'ed-section');
    remote.append(el('h3', null, 'GitHub 上的提交'), el('p', 'ed-hint', '每次提交都是一个版本，网站文章页底部的“修改记录”也来自这里。'));
    const remoteList = el('ol', 'ed-versions');
    remote.append(remoteList);
    body.append(local, remote);
    if (state.isNew) { remoteList.append(el('li', 'ed-empty', '这篇还没有提交过。')); return; }
    remoteList.append(el('li', 'ed-empty', '正在读取……'));
    try {
      const path = `content/${state.slug}.md`;
      const commits = await api(`/repos/${REPO}/commits?path=${encodeURIComponent(path)}&sha=${BRANCH}&per_page=20`);
      const anchor = 'diff-' + await sha256Hex(path);
      remoteList.replaceChildren();
      for (const item of commits) {
        const row = el('li');
        const when = (item.commit.author && item.commit.author.date || '').slice(0, 10);
        row.append(el('span', 'ed-version-time', when), el('span', 'ed-version-label', item.commit.message.split('\n')[0]));
        row.append(button('对比', async () => showDiff((await getFile(path, item.sha)).text, `提交 ${item.sha.slice(0, 7)}`)),
          button('恢复', async () => { restore((await getFile(path, item.sha)).text, null, `提交 ${item.sha.slice(0, 7)}`); dialog.close(); }),
          link('在 GitHub 看', `${SITE}/commit/${item.sha}#${anchor}`));
        remoteList.append(row);
      }
      if (!commits.length) remoteList.append(el('li', 'ed-empty', '没有找到提交记录。'));
    } catch (error) {
      remoteList.replaceChildren(el('li', 'ed-empty', error.message));
    }
  }
  function showDiff(other, label) {
    openDialog('对比', body => {
      body.append(button('← 返回版本列表', openVersions), diffView(other, els.text.value, label, '当前编辑中'));
    });
  }
  async function sha256Hex(text) {
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
    return [...new Uint8Array(digest)].map(b => b.toString(16).padStart(2, '0')).join('');
  }
  $('ed-history').addEventListener('click', openVersions);

  /* ---------- GitHub 接口 ---------- */
  class ApiError extends Error {
    constructor(status, message) { super(message); this.status = status; }
  }
  async function api(path, { method = 'GET', body } = {}) {
    const headers = { Accept: 'application/vnd.github+json' };
    if (state.token) headers.Authorization = `Bearer ${state.token}`;
    if (body) headers['Content-Type'] = 'application/json';
    let response;
    try {
      response = await fetch(API + path, { method, headers, body: body ? JSON.stringify(body) : undefined, cache: 'no-store' });
    } catch {
      throw new ApiError(0, '连不上 GitHub，检查一下网络后再试。');
    }
    if (response.ok) return response.status === 204 ? null : response.json();
    let detail = '';
    try { detail = (await response.json()).message || ''; } catch { /* 没有正文 */ }
    if (response.status === 401) throw new ApiError(401, '令牌无效或已经过期，请重新连接。');
    if (response.status === 403 && response.headers.get('x-ratelimit-remaining') === '0') {
      throw new ApiError(403, 'GitHub 接口的免登录额度（每小时 60 次）用完了。连接令牌后额度更高，或者过一会儿再试。');
    }
    if (method !== 'GET' && (response.status === 403 || response.status === 404)) {
      throw new ApiError(response.status, `GitHub 拒绝了提交（${detail || response.status}）。请确认令牌只授权了 bytelife 仓库，并给了 Contents 读写权限。`);
    }
    throw new ApiError(response.status, `读取 GitHub 失败（${detail || response.status}）。`);
  }
  async function getFile(path, ref = BRANCH) {
    const file = await api(`/repos/${REPO}/contents/${path}?ref=${encodeURIComponent(ref)}`);
    return { text: decodeBase64(file.content), sha: file.sha };
  }

  /* ---------- 打开文章 ---------- */
  function fillSelect() {
    const options = state.catalog.map(a => [a.slug, `${a.title}${a.draft ? '（草稿）' : ''}`]);
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (!key || !key.startsWith(STORE)) continue;
        const slug = key.slice(STORE.length);
        const record = readRecord(slug);
        if (record.isNew && record.working && !state.catalog.some(a => a.slug === slug)) options.push([slug, `${record.working.meta.title || slug}（新，未提交）`]);
      }
    } catch { /* 浏览器禁用了本机存储 */ }
    els.select.replaceChildren(...options.map(([value, label]) => { const option = el('option', null, label); option.value = value; return option; }));
    if (state.slug) els.select.value = state.slug;
  }
  function useDocument(text, meta) {
    els.text.value = text;
    fillMeta(meta);
    els.text.disabled = false;
    els.text.scrollTop = 0;
    els.preview.scrollTop = 0;
    renderPreview();
  }
  async function openArticle(slug) {
    if (state.slug && state.base) saveLocal();
    state.slug = slug;
    state.base = null;
    els.select.value = slug;
    els.text.disabled = true;
    const url = new URL(location.href);
    url.searchParams.set('a', slug);
    history.replaceState(null, '', url);
    const record = readRecord(slug);
    const entry = state.catalog.find(a => a.slug === slug);
    if (!entry) {
      if (!record.working) return setStatus('没有找到这篇文章。', 'error');
      state.isNew = true;
      state.base = { text: '', sha: null, meta: null };
      useDocument(record.working.text, record.working.meta);
      return updateStatus(record.working.at);
    }
    state.isNew = false;
    setStatus('正在从 GitHub 读取最新内容……');
    let file;
    try {
      file = await getFile(`content/${slug}.md`);
    } catch (error) {
      if (record.working) {
        state.base = { text: '', sha: record.working.baseSha, meta: entry };
        useDocument(record.working.text, record.working.meta);
        return setStatus(`${error.message} 先打开了本机保存的版本。`, 'error');
      }
      setStatus(error.message, 'error');
      return offerRetry(slug);
    }
    if (state.slug !== slug) return;
    state.base = { text: file.text, sha: file.sha, meta: entry };
    const local = record.working;
    if (local && (local.text !== file.text || !same(compareMeta(local.meta), compareMeta(entry)))) {
      if (local.baseSha === file.sha) {
        useDocument(local.text, local.meta);
        return setStatus(`已接着上次在本机的修改（${clock(local.at)}）。要放弃这些修改，到“版本”里恢复 GitHub 上的提交。`, 'dirty');
      }
      record.snapshots.push({ at: local.at, label: '基于旧版本的本机修改', text: local.text, meta: local.meta });
      delete record.working;
      writeRecord(record, slug);
      useDocument(file.text, entry);
      return setStatus('GitHub 上这篇已经更新过，打开的是最新版本；你之前在本机的修改存在“版本”里，可以对比后恢复。', 'dirty');
    }
    useDocument(file.text, entry);
    updateStatus();
  }
  function offerRetry(slug) {
    const retry = button('重试', () => openArticle(slug));
    els.status.append(' ', retry);
  }
  els.select.addEventListener('change', () => openArticle(els.select.value));

  /* ---------- 新建 ---------- */
  $('ed-new').addEventListener('click', () => {
    openDialog('新建文章', body => {
      const form = el('div', 'ed-form');
      const input = (label, attrs = {}) => {
        const wrap = el('label', null, label);
        const node = el(attrs.tag || 'input');
        Object.entries(attrs).forEach(([k, v]) => { if (k !== 'tag') node.setAttribute(k, v); });
        wrap.append(node);
        form.append(wrap);
        return node;
      };
      const slug = input('英文名（也是网址的一部分）', { placeholder: 'tomato-egg', autocomplete: 'off', spellcheck: 'false' });
      const title = input('标题');
      const category = input('分类', { list: 'ed-categories', placeholder: '编程、做菜、生活……' });
      const type = input('类型', { tag: 'select' });
      Object.entries(data.types).forEach(([key, label]) => { const option = el('option', null, label); option.value = key; type.append(option); });
      const summary = input('一句话摘要', { tag: 'textarea', rows: '2' });
      category.addEventListener('input', () => {
        if (/菜|食|烘焙/.test(category.value)) type.value = 'recipe'; else if (category.value === '生活') type.value = 'post';
      });
      const error = el('p', 'ed-error');
      const create = button('创建草稿', () => {
        const meta = { slug: slug.value.trim(), title: title.value.trim(), category: category.value.trim(), type: type.value,
          summary: summary.value.trim(), created: today(), updated: today(), draft: true };
        const taken = state.catalog.some(a => a.slug === meta.slug) || readRecord(meta.slug).working;
        const list = taken ? ['这个英文名已经用过了'] : problems({ ...meta, updated: meta.created }).filter(p => p !== '正文是空的');
        if (list.length) { error.textContent = list.join('；'); return; }
        if (state.slug && state.base) saveLocal();
        state.slug = meta.slug;
        state.isNew = true;
        state.base = { text: '', sha: null, meta: null };
        useDocument(data.templates[meta.type], meta);
        saveLocal();
        fillSelect();
        dialog.close();
        els.text.focus();
      }, 'button button-primary');
      body.append(el('p', 'ed-hint', '会按类型套用模板，标成草稿。写好后点“提交”，草稿不会出现在网站上，取消“草稿”勾选再提交才会发布。'), form, error, create);
    });
  });

  /* ---------- 连接令牌 ---------- */
  function openToken(after) {
    openDialog('连接 GitHub', body => {
      const steps = el('ol', 'ed-steps');
      ['在 GitHub 新建一个细粒度令牌（fine-grained token）：', 'Repository access 只选 bytelife 这一个仓库。',
        'Repository permissions 里把 Contents 设成 Read and write，其他保持默认。', '有效期选 30 天左右，生成后复制过来。']
        .forEach((text, index) => { const li = el('li', null, text); if (index === 0) li.append(' ', link('打开创建页面', 'https://github.com/settings/personal-access-tokens/new')); steps.append(li); });
      const label = el('label', 'ed-token', '令牌');
      const input = el('input');
      input.type = 'password';
      input.autocomplete = 'off';
      input.spellcheck = false;
      label.append(input);
      const message = el('p', 'ed-error');
      const connect = button('连接', async () => {
        const token = input.value.trim();
        if (!/^(github_pat_|ghp_)[A-Za-z0-9_]{20,}$/.test(token)) { message.textContent = '这看起来不是 GitHub 令牌。'; return; }
        message.textContent = '正在核对……';
        state.token = token;
        try {
          const [user, repo] = await Promise.all([api('/user'), api(`/repos/${REPO}`)]);
          if (!repo.permissions || !repo.permissions.push) throw new ApiError(403, '这个账号对 bytelife 仓库没有写入权限。');
          state.login = user.login;
          input.value = '';
          updateStatus();
          dialog.close();
          if (after) after();
        } catch (error) {
          state.token = null;
          state.login = null;
          message.textContent = error.message;
        }
      }, 'button button-primary');
      input.addEventListener('keydown', event => { if (event.key === 'Enter') connect.click(); });
      body.append(el('p', 'ed-hint', '令牌只保存在这个页面的内存里：刷新或关闭页面就没了，也不会发给 GitHub 以外的地方。不用的令牌记得在 GitHub 设置里删除。'), steps, label, message, connect);
      requestAnimationFrame(() => input.focus());
    });
  }

  /* ---------- 提交 ---------- */
  function catalogEntry(existing, meta) {
    const entry = existing ? { ...existing } : {};
    for (const key of ['slug', 'title', 'category', 'type', 'summary', 'created', 'updated']) entry[key] = meta[key];
    if (meta.draft) entry.draft = true; else delete entry.draft;
    if (meta.recipe) entry.recipe = meta.recipe; else delete entry.recipe;
    return entry;
  }
  async function commit(message, meta) {
    const path = `content/${state.slug}.md`;
    const text = els.text.value.replace(/\r\n/g, '\n').replace(/\n*$/, '\n');
    const head = (await api(`/repos/${REPO}/git/ref/heads/${BRANCH}`)).object.sha;
    let remote = null;
    try { remote = await getFile(path, head); } catch (error) { if (error.status !== 404) throw error; }
    if (state.isNew && remote) throw new ApiError(409, 'GitHub 上已经有同名文章，换一个英文名再提交。');
    if (!state.isNew && (!remote || remote.sha !== state.base.sha)) {
      throw new ApiError(409, '这篇在你打开之后，GitHub 上又被改过（可能是在别的设备或网页上）。你的内容已存成本机版本，请先在“版本”里对比 GitHub 上的最新提交，再决定怎么合并。');
    }
    const catalogFile = await getFile('articles.json', head);
    const catalog = JSON.parse(catalogFile.text);
    const index = catalog.findIndex(a => a.slug === state.slug);
    if (state.isNew && index >= 0) throw new ApiError(409, 'articles.json 里已经有这个英文名。');
    const entry = catalogEntry(index >= 0 ? catalog[index] : null, meta);
    if (index >= 0) catalog[index] = entry; else catalog.push(entry);
    const catalogText = JSON.stringify(catalog, null, 2) + '\n';
    const files = [];
    if (!remote || remote.text !== text) files.push({ path, mode: '100644', type: 'blob', content: text });
    if (catalogText !== catalogFile.text) files.push({ path: 'articles.json', mode: '100644', type: 'blob', content: catalogText });
    if (!files.length) throw new ApiError(0, '和 GitHub 上的内容一样，不需要提交。');
    const parent = await api(`/repos/${REPO}/git/commits/${head}`);
    const tree = await api(`/repos/${REPO}/git/trees`, { method: 'POST', body: { base_tree: parent.tree.sha, tree: files } });
    const created = await api(`/repos/${REPO}/git/commits`, { method: 'POST', body: { message, tree: tree.sha, parents: [head] } });
    await api(`/repos/${REPO}/git/refs/heads/${BRANCH}`, { method: 'PATCH', body: { sha: created.sha, force: false } });
    return { sha: created.sha, blobSha: await gitBlobSha(text), entry, text };
  }
  // Git 给文件内容算的编号：sha1("blob 字节数\0内容")，下次提交时用来判断 GitHub 上有没有被别人改过。
  async function gitBlobSha(text) {
    const bytes = new TextEncoder().encode(text);
    const header = new TextEncoder().encode(`blob ${bytes.length}\0`);
    const all = new Uint8Array(header.length + bytes.length);
    all.set(header);
    all.set(bytes, header.length);
    const digest = await crypto.subtle.digest('SHA-1', all);
    return [...new Uint8Array(digest)].map(b => b.toString(16).padStart(2, '0')).join('');
  }

  function openCommit() {
    if (!state.base) return;
    if (!state.token) return openNoToken();
    const meta = readMeta();
    const before = state.base.text;
    const rows = diffLines(before, els.text.value);
    const added = rows.filter(r => r[0] === '+').length, removed = rows.filter(r => r[0] === '-').length;
    openDialog('提交到 GitHub', body => {
      const summary = el('p', 'ed-hint', state.isNew ? `新文章：${meta.title}` : `正文新增 ${added} 行、删除 ${removed} 行${same(compareMeta(meta), compareMeta(state.base.meta)) ? '' : '，文章信息也有改动'}。`);
      const msgLabel = el('label', 'ed-token', '这次改了什么（提交说明）');
      const msg = el('input');
      msg.value = `${state.isNew ? '新建' : '修改'}：${meta.title}`;
      msgLabel.append(msg);
      const dateLabel = el('label', 'ed-check');
      const dateBox = el('input');
      dateBox.type = 'checkbox';
      dateBox.checked = !state.isNew && !meta.draft && meta.updated !== today();
      dateLabel.append(dateBox, ` 更新日期改成今天（${today()}）`);
      const note = el('p', 'ed-hint', meta.draft ? '这篇是草稿：提交后保存在 GitHub 上，但不会出现在网站里。' : '提交后网站会自动重新发布，一般一两分钟后能看到。');
      const message = el('p', 'ed-error');
      const go = button('提交', async () => {
        const final = { ...meta, updated: dateBox.checked ? today() : meta.updated };
        const list = problems(final);
        if (list.length) { message.textContent = list.join('；'); return; }
        go.disabled = true;
        message.textContent = '正在提交……';
        writeRecord(snapshot('提交前'));
        try {
          const result = await commit(msg.value.trim() || `修改：${final.title}`, final);
          state.isNew = false;
          state.base = { text: result.text, sha: result.blobSha, meta: result.entry };
          const existing = state.catalog.findIndex(a => a.slug === state.slug);
          if (existing >= 0) state.catalog[existing] = result.entry; else state.catalog.unshift(result.entry);
          fillMeta(result.entry);
          const record = readRecord();
          delete record.working;
          record.isNew = false;
          record.snapshots.push({ at: Date.now(), label: `已提交 ${result.sha.slice(0, 7)}`, text: result.text, meta: readMeta() });
          writeRecord(record);
          fillSelect();
          renderPreview();
          body.replaceChildren(el('p', 'ed-success', `已提交（${result.sha.slice(0, 7)}）。`),
            el('p', 'ed-hint', final.draft ? '草稿已保存到 GitHub，不会出现在网站上。' : '网站正在重新发布，一两分钟后刷新文章页就是新内容。'),
            link('查看发布进度', `${SITE}/actions/workflows/pages.yml`));
          updateStatus();
        } catch (error) {
          go.disabled = false;
          message.textContent = error.message;
          if (error.status === 409) message.append(' ', button('对比 GitHub 最新版本', async () => {
            try { showDiff((await getFile(`content/${state.slug}.md`)).text, 'GitHub 最新'); } catch (e) { message.textContent = e.message; }
          }));
        }
      }, 'button button-primary');
      body.append(summary, msgLabel, dateLabel, note, message, go);
    });
  }

  function openNoToken() {
    const meta = readMeta();
    openDialog('提交到 GitHub', body => {
      body.append(el('p', 'ed-hint', '两种方式任选：连接令牌后在这里一键提交；或者复制内容，到 GitHub 网页上粘贴提交。'));
      const tokenWay = el('section', 'ed-section');
      tokenWay.append(el('h3', null, '方式一：连接令牌，直接提交'), button('连接 GitHub 令牌', () => openToken(openCommit), 'button button-primary'));
      const copyWay = el('section', 'ed-section');
      copyWay.append(el('h3', null, '方式二：复制到 GitHub 网页'));
      const steps = el('ol', 'ed-steps');
      const copied = el('span', 'ed-hint');
      const copyText = button('复制正文', async () => { await navigator.clipboard.writeText(els.text.value); copied.textContent = ' 已复制'; });
      const step1 = el('li', null, '复制这篇的正文：');
      step1.append(copyText, copied);
      const step2 = el('li', null, state.isNew ? '在 GitHub 新建文件（文件名已填好），粘贴后提交：' : '打开 GitHub 编辑页，全选替换成复制的内容，再提交：');
      step2.append(' ', link('打开 GitHub', state.isNew ? `${SITE}/new/${BRANCH}/content?filename=${state.slug}.md` : `${SITE}/edit/${BRANCH}/content/${state.slug}.md`));
      steps.append(step1, step2);
      if (state.isNew || !same(compareMeta(meta), compareMeta(state.base.meta))) {
        const entry = JSON.stringify(catalogEntry(state.base.meta, meta), null, 2);
        const step3 = el('li', null, state.isNew ? 'articles.json 里还要加上这一项（放进最外层的方括号里，和其他项用逗号隔开）：' : 'articles.json 里这一项也要换成：');
        const done = el('span', 'ed-hint');
        step3.append(button('复制这一项', async () => { await navigator.clipboard.writeText(entry); done.textContent = ' 已复制'; }), done, ' ',
          link('编辑 articles.json', `${SITE}/edit/${BRANCH}/articles.json`), el('pre', 'ed-json', entry));
        steps.append(step3);
      }
      copyWay.append(steps);
      if (state.isNew) copyWay.append(el('p', 'ed-hint', '也可以在 GitHub 的 Actions 页面用“新建文章”表单生成草稿：'), link('打开新建文章表单', `${SITE}/actions/workflows/new-article.yml`));
      body.append(tokenWay, copyWay);
    });
  }
  $('ed-commit').addEventListener('click', openCommit);

  /* ---------- 手机：源代码 / 预览切换 ---------- */
  for (const tab of document.querySelectorAll('.ed-tabs [role="tab"]')) {
    tab.addEventListener('click', () => {
      els.panes.dataset.view = tab.dataset.view;
      for (const other of document.querySelectorAll('.ed-tabs [role="tab"]')) other.setAttribute('aria-selected', String(other === tab));
      requestAnimationFrame(measure);
    });
  }

  /* ---------- 启动 ---------- */
  (async () => {
    fillSelect();
    const wanted = new URLSearchParams(location.search).get('a');
    const first = wanted && SLUG.test(wanted) ? wanted : (state.catalog[0] && state.catalog[0].slug);
    try {
      // 文章列表以 GitHub 上最新的 articles.json 为准，读不到就用页面里随网站发布的那份。
      const latest = JSON.parse((await getFile('articles.json')).text);
      if (Array.isArray(latest)) { state.catalog = latest.filter(a => a && SLUG.test(a.slug)); fillSelect(); }
    } catch { /* 用页面自带的列表 */ }
    if (first) openArticle(first); else setStatus('还没有文章，点“新建”开始。');
  })();
})();
