/* ByteLife 前端：主题、全文搜索、目录、代码复制和图片放大。
   内容和索引都在本站，搜索词不会发给外部服务。
   页面 CSP 开启了 Trusted Types，这里只用 textContent / createElement 更新页面，不拼 HTML 字符串。 */
(() => {
  'use strict';
  const root = document.documentElement;
  const base = document.body.dataset.base || '/';
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const live = el('p', 'visually-hidden');
  live.setAttribute('role', 'status');
  document.body.append(live);

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function icon(name) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
    svg.setAttribute('class', `icon icon-${name}`);
    svg.setAttribute('aria-hidden', 'true');
    use.setAttribute('href', `#i-${name}`);
    svg.append(use);
    return svg;
  }

  function announce(text) {
    live.textContent = '';
    requestAnimationFrame(() => { live.textContent = text; });
  }

  // 首次定位到 # 锚点之后才打开平滑滚动（见 site.css）。
  const ready = () => requestAnimationFrame(() => root.classList.add('is-ready'));
  if (document.readyState === 'complete') ready(); else addEventListener('load', ready, { once: true });

  /* ---------- 主题：默认跟随系统，手动选过才记住 ---------- */
  const THEME_KEY = 'bytelife-theme';
  const systemDark = matchMedia('(prefers-color-scheme: dark)');
  const themeMetas = [...document.querySelectorAll('meta[name="theme-color"]')];
  const themeColors = Object.fromEntries(themeMetas.map(m => [m.media.includes('dark') ? 'dark' : 'light', m.content]));
  const toggle = document.querySelector('.theme-toggle');
  const reset = document.querySelector('.theme-reset');

  function storedTheme() {
    try {
      const value = localStorage.getItem(THEME_KEY);
      return value === 'light' || value === 'dark' ? value : null;
    } catch { return null; }
  }
  const currentTheme = () => root.dataset.theme || (systemDark.matches ? 'dark' : 'light');

  function syncTheme() {
    const dark = currentTheme() === 'dark';
    toggle?.setAttribute('aria-pressed', String(dark));
    if (toggle) toggle.title = dark ? '切换到浅色' : '切换到深色';
    if (reset) reset.hidden = !root.dataset.theme;
    for (const meta of themeMetas) meta.content = themeColors[root.dataset.theme] || themeColors[meta.media.includes('dark') ? 'dark' : 'light'];
  }

  function applyTheme(theme) {
    const change = () => {
      if (theme) root.dataset.theme = theme; else delete root.dataset.theme;
      syncTheme();
    };
    if (document.startViewTransition && !reduceMotion.matches) document.startViewTransition(change); else change();
  }

  toggle?.addEventListener('click', () => {
    const next = currentTheme() === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem(THEME_KEY, next); } catch { /* 禁用存储时只在本页生效。 */ }
    applyTheme(next);
  });
  reset?.addEventListener('click', () => {
    try { localStorage.removeItem(THEME_KEY); } catch { /* 同上。 */ }
    applyTheme(null);
    toggle?.focus();
  });
  systemDark.addEventListener('change', syncTheme);
  addEventListener('storage', event => { if (event.key === THEME_KEY) applyTheme(storedTheme()); });
  syncTheme();

  /* ---------- 首页搜索 ---------- */
  const searchInput = document.getElementById('search-input');
  if (searchInput) setupSearch(searchInput);

  function setupSearch(input) {
    const list = document.getElementById('article-list');
    const library = list.closest('.library');
    const status = document.getElementById('search-status');
    const notice = document.getElementById('search-notice');
    const clear = document.querySelector('.search-clear');
    const chips = [...document.querySelectorAll('.chip[data-category]')];
    const ALL = chips[0].dataset.category;
    const entries = [...list.children];
    const staticData = entries.map(li => ({
      li, category: li.dataset.category,
      text: `${li.querySelector('.entry-title').textContent} ${li.querySelector('.entry-summary').textContent}`.toLowerCase(),
    }));
    let category = ALL;
    let index = null;
    let loading = null;
    let timer = 0;
    let revision = 0;

    // 全角字母数字转半角，中文输入法下打出的 ｇｉｔ 也能搜到 git。
    const normalize = value => value.replace(/[０-９Ａ-Ｚａ-ｚ]/g, c => String.fromCharCode(c.charCodeAt(0) - 0xFEE0))
      .replace(/　/g, ' ').trim().toLowerCase();
    const parse = value => [...new Set(normalize(value).slice(0, 80).split(/\s+/).filter(Boolean))].slice(0, 6);
    const escapeRegExp = value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

    function loadIndex() {
      if (index) return Promise.resolve(index);
      loading ||= fetch(list.dataset.index, { headers: { Accept: 'application/json' } })
        .then(response => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); })
        .then(data => {
          if (!Array.isArray(data)) throw new Error('索引格式不对');
          index = data.filter(a => typeof a.url === 'string' && a.url.startsWith(`${base}articles/`)).map(a => ({
            ...a, titleLower: a.title.toLowerCase(), summaryLower: `${a.summary} ${a.authors || ''}`.toLowerCase(),
            sections: a.sections.map(([id, title, text]) => ({ id, title, text, lower: text.toLowerCase(), titleLower: title.toLowerCase() })),
          }));
          return index;
        })
        .catch(error => { loading = null; throw error; });
      return loading;
    }

    function count(haystack, word) {
      let n = 0;
      for (let i = haystack.indexOf(word); i !== -1 && n < 999; i = haystack.indexOf(word, i + word.length)) n++;
      return n;
    }

    function search(words) {
      const results = [];
      for (const a of index) {
        const found = w => a.titleLower.includes(w) || a.summaryLower.includes(w) || a.sections.some(s => s.lower.includes(w) || s.titleLower.includes(w));
        if (!words.every(found)) continue;
        const hits = [];
        let total = 0;
        for (const section of a.sections) {
          let matched = 0, n = 0, named = 0, first = -1;
          for (const w of words) {
            const c = count(section.lower, w) + count(section.titleLower, w);
            if (!c) continue;
            matched++;
            n += c;
            named += section.titleLower.includes(w);
            const at = section.lower.indexOf(w);
            if (at !== -1 && (first === -1 || at < first)) first = at;
          }
          if (n) { hits.push({ section, matched, named, n, first }); total += n; }
        }
        // 命中词更多、章节标题就含这个词、出现次数更多的章节排前面；其余按文章顺序。
        hits.sort((x, y) => y.matched - x.matched || y.named - x.named || y.n - x.n);
        results.push({ a, hits, total, inTitle: words.filter(w => a.titleLower.includes(w)).length });
      }
      return results.sort((x, y) => y.inTitle - x.inTitle || y.total - x.total);
    }

    function excerpt(text, first) {
      if (first < 0) return text.length > 90 ? `${text.slice(0, 90)}…` : text;
      const start = Math.max(0, first - 28);
      const end = Math.min(text.length, start + 110);
      return `${start ? '…' : ''}${text.slice(start, end)}${end < text.length ? '…' : ''}`;
    }

    function highlight(text, pattern) {
      const fragment = document.createDocumentFragment();
      let last = 0;
      for (const match of text.matchAll(pattern)) {
        if (match.index > last) fragment.append(text.slice(last, match.index));
        fragment.append(el('mark', null, match[0]));
        last = match.index + match[0].length;
      }
      fragment.append(text.slice(last));
      return fragment;
    }

    function renderResults(results, words) {
      const pattern = new RegExp([...words].sort((x, y) => y.length - x.length).map(escapeRegExp).join('|'), 'giu');
      const fragment = document.createDocumentFragment();
      for (const { a, hits, total } of results) {
        const item = el('li', 'entry is-result');
        const meta = el('p', 'entry-meta');
        meta.append(el('span', 'entry-cat', a.category));
        if (list.dataset.multiAuthor === 'true' && a.authors) meta.append(el('span', 'entry-author', a.authors));
        meta.append(el('span', null, `更新 ${a.updated}`));
        if (total) meta.append(el('span', 'entry-hits', `正文 ${total} 处`));
        const title = el('h3', 'entry-title');
        const link = el('a');
        link.href = a.url;
        link.append(highlight(a.title, pattern));
        title.append(link);
        item.append(meta, title);
        if (hits.length) {
          const places = el('ul', 'hits');
          for (const { section, first } of hits.slice(0, 3)) {
            const row = el('li');
            const jump = el('a', 'hit');
            jump.href = a.url + (section.id ? `#${encodeURIComponent(section.id)}` : '');
            const where = el('span', 'hit-where');
            where.append(icon('arrow-right'), section.title || '开头');
            const text = el('span', 'hit-text');
            text.append(highlight(excerpt(section.text, first), pattern));
            jump.append(where, text);
            row.append(jump);
            places.append(row);
          }
          if (hits.length > 3) places.append(el('li', 'hits-more', `另有 ${hits.length - 3} 个章节也提到`));
          item.append(places);
        } else {
          const summary = el('p', 'entry-summary');
          summary.append(highlight(a.summary, pattern));
          item.append(summary);
        }
        fragment.append(item);
      }
      list.replaceChildren(fragment);
    }

    function setStatus(text) { if (status.textContent !== text) status.textContent = text; }

    function showNotice(kind, message, actions = []) {
      const row = el('div', 'notice-actions');
      for (const [label, action, primary] of actions) {
        const button = el('button', primary ? 'button button-primary' : 'button', label);
        button.type = 'button';
        button.addEventListener('click', action);
        row.append(button);
      }
      notice.className = kind === 'error' ? 'search-notice is-error' : 'search-notice';
      notice.replaceChildren(el('p', null, message), ...(actions.length ? [row] : []));
      notice.hidden = false;
    }

    function hideNotice() { notice.hidden = true; notice.replaceChildren(); }

    function updateChips(counts) {
      for (const chip of chips) {
        const badge = chip.querySelector('.chip-count');
        const n = counts ? counts.get(chip.dataset.category) || 0 : Number(badge.dataset.total);
        badge.textContent = n;
      }
    }

    function showAll() {
      list.replaceChildren(...entries);
      let shown = 0;
      for (const { li, category: c } of staticData) {
        li.hidden = category !== ALL && c !== category;
        if (!li.hidden) shown++;
      }
      updateChips(null);
      library.classList.remove('is-searching');
      hideNotice();
      setStatus(category === ALL ? '' : `${category} · ${shown} 篇`);
    }

    // 索引没载入时退回到标题和摘要匹配，至少能找到文章；“重新载入”成功后恢复全文结果。
    function showFallback(words) {
      list.replaceChildren(...entries);
      const counts = new Map([[ALL, 0]]);
      let shown = 0;
      for (const { li, category: c, text } of staticData) {
        const match = words.every(w => text.includes(w));
        if (match) { counts.set(ALL, counts.get(ALL) + 1); counts.set(c, (counts.get(c) || 0) + 1); }
        li.hidden = !match || (category !== ALL && c !== category);
        if (!li.hidden) shown++;
      }
      updateChips(counts);
      library.classList.add('is-searching');
      setStatus(`全文索引没有载入，暂时只按标题和摘要匹配：${shown} 篇`);
      showNotice('error', '全文索引没有载入成功，可能是网络中断或网站刚更新。现在只能搜到标题和摘要。',
        [['重新载入索引', () => { input.focus(); run(); }, true]]);
    }

    function showResults(words, query) {
      const all = search(words);
      const counts = new Map([[ALL, all.length]]);
      for (const r of all) counts.set(r.a.category, (counts.get(r.a.category) || 0) + 1);
      updateChips(counts);
      library.classList.add('is-searching');
      const results = category === ALL ? all : all.filter(r => r.a.category === category);
      renderResults(results, words);
      const scope = category === ALL ? '' : `在“${category}”中`;
      if (results.length) {
        hideNotice();
        setStatus(`${scope}找到 ${results.length} 篇含“${query}”的文章，点章节名直接跳到那一段`);
        return;
      }
      setStatus(`${scope}没有找到“${query}”`);
      if (category !== ALL && all.length) {
        showNotice('empty', `“${category}”里没有，其他分类有 ${all.length} 篇。`, [
          [`在全部分类中查看（${all.length} 篇）`, () => { setCategory(ALL); chips[0].focus(); }, true],
          ['清空搜索', clearSearch]]);
      } else {
        showNotice('empty', '换个说法试试：少写几个字，或者只搜命令、报错里最关键的词。', [['清空搜索', clearSearch, true]]);
      }
    }

    function syncUrl(query) {
      const url = new URL(location.href);
      if (query) url.searchParams.set('q', query); else url.searchParams.delete('q');
      if (category !== ALL) url.searchParams.set('c', category); else url.searchParams.delete('c');
      if (url.href !== location.href) history.replaceState(history.state, '', url);
    }

    // 每次搜索带一个序号，旧请求晚到时直接丢弃，不会覆盖新结果。
    async function run() {
      clearTimeout(timer);
      const current = ++revision;
      const query = input.value.trim().slice(0, 100);
      const words = parse(query);
      clear.hidden = !input.value;
      syncUrl(query);
      if (!words.length) { showAll(); return; }
      if (!index) {
        const slow = setTimeout(() => { if (current === revision) setStatus('正在载入全文索引…'); }, 160);
        try {
          await loadIndex();
        } catch {
          if (current === revision) showFallback(words);
          return;
        } finally {
          clearTimeout(slow);
        }
        if (current !== revision) return;
      }
      showResults(words, query);
    }

    function schedule() { clearTimeout(timer); timer = setTimeout(run, 120); }
    function clearSearch() { input.value = ''; run(); input.focus(); }

    function setCategory(next) {
      category = next;
      for (const chip of chips) {
        const on = chip.dataset.category === next;
        chip.classList.toggle('is-active', on);
        chip.setAttribute('aria-pressed', String(on));
      }
      run();
    }

    // 中文输入法拼写过程中不搜索，选好字之后再搜，避免结果跟着拼音闪。
    input.addEventListener('input', event => { if (!event.isComposing) schedule(); });
    input.addEventListener('compositionend', schedule);
    input.addEventListener('focus', () => { loadIndex().catch(() => {}); }, { once: true });
    input.addEventListener('keydown', event => {
      if (event.isComposing || event.keyCode === 229) return;
      if (event.key === 'Escape') {
        if (input.value) { event.preventDefault(); input.value = ''; run(); } else input.blur();
      } else if (event.key === 'Enter') {
        event.preventDefault();
        run().then(() => list.querySelector('li:not([hidden]) .entry-title a')?.focus());
      }
    });
    clear.addEventListener('click', clearSearch);
    for (const chip of chips) chip.addEventListener('click', () => setCategory(chip.dataset.category));
    document.addEventListener('keydown', event => {
      if (event.key !== '/' || event.ctrlKey || event.metaKey || event.altKey || event.defaultPrevented) return;
      if (event.target.closest?.('input, textarea, select, [contenteditable]')) return;
      event.preventDefault();
      input.focus();
      input.select();
    });

    const params = new URLSearchParams(location.search);
    const initial = params.get('c');
    input.value = (params.get('q') || '').slice(0, 100);
    if (initial && chips.some(chip => chip.dataset.category === initial)) setCategory(initial);
    else if (input.value) run();
    if (location.hash === '#search') input.focus();
  }

  // 从页头“修改记录”或带 #revisions 的链接进来时，自动展开修改记录。
  const openRevisions = () => { if (location.hash === '#revisions') document.getElementById('revisions')?.setAttribute('open', ''); };
  openRevisions();
  addEventListener('hashchange', openRevisions);

  /* ---------- 正文：代码复制、超宽区域、图片放大 ---------- */
  const prose = document.querySelector('.prose');
  if (prose) setupProse(prose);

  function setupProse(prose) {
    const mac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
    for (const block of prose.querySelectorAll('.code-block')) {
      const code = block.querySelector('code');
      const button = el('button', 'copy-button');
      const label = el('span', null, '复制');
      let timer = 0;
      button.type = 'button';
      button.setAttribute('aria-label', '复制代码');
      button.append(icon('copy'), icon('check'), label);
      button.addEventListener('click', async () => {
        // 去掉末尾换行：粘贴进终端时不会自动回车执行。
        const text = code.textContent.replace(/\n$/, '');
        let copied = false;
        try { await navigator.clipboard.writeText(text); copied = true; } catch { /* 下面改为选中文字。 */ }
        clearTimeout(timer);
        if (copied) {
          button.classList.add('is-copied');
          label.textContent = '已复制';
          announce('代码已复制到剪贴板');
        } else {
          const range = document.createRange();
          range.selectNodeContents(code);
          getSelection().removeAllRanges();
          getSelection().addRange(range);
          label.textContent = mac ? '已选中，按 ⌘C' : '已选中，按 Ctrl+C';
          announce('无法直接写入剪贴板，代码已选中，请手动复制');
        }
        timer = setTimeout(() => { button.classList.remove('is-copied'); label.textContent = '复制'; }, 1800);
      });
      block.querySelector('.code-head').append(button);
    }

    // 只有真的超宽时才让代码和表格区域可聚焦，键盘用户能用方向键横向滚动。
    const scrollers = [...prose.querySelectorAll('pre, .table-wrap')];
    const markScrollable = () => {
      for (const node of scrollers) {
        const wide = node.scrollWidth > node.clientWidth + 1;
        if (wide && !node.hasAttribute('tabindex')) {
          node.tabIndex = 0;
          node.setAttribute('role', 'region');
          node.setAttribute('aria-label', node.matches('pre') ? '代码，可横向滚动' : '表格，可横向滚动');
        } else if (!wide && node.hasAttribute('tabindex')) {
          for (const name of ['tabindex', 'role', 'aria-label']) node.removeAttribute(name);
        }
      }
    };
    let resizeTimer = 0;
    markScrollable();
    if ('ResizeObserver' in window) new ResizeObserver(() => { clearTimeout(resizeTimer); resizeTimer = setTimeout(markScrollable, 150); }).observe(prose);

    const links = prose.querySelectorAll('.figure-link');
    if (!links.length || typeof HTMLDialogElement !== 'function') return;
    let dialog, image, caption, original, opener;
    const build = () => {
      dialog = el('dialog', 'lightbox');
      dialog.setAttribute('aria-label', '图片预览');
      const bar = el('div', 'lightbox-bar');
      original = el('a');
      original.target = '_blank';
      original.rel = 'noopener';
      original.append('原图', icon('external'));
      const close = el('button');
      close.type = 'button';
      close.autofocus = true;
      close.setAttribute('aria-label', '关闭图片预览');
      close.append(icon('close'));
      close.addEventListener('click', () => dialog.close());
      bar.append(original, close);
      const figure = el('figure', 'lightbox-figure');
      image = el('img');
      caption = el('figcaption');
      figure.append(image, caption);
      dialog.append(bar, figure);
      // 点图片外的空白处关闭；点图片在“适应屏幕”和“原始大小”之间切换。Esc 由 <dialog> 原生处理。
      dialog.addEventListener('click', event => { if (event.target === dialog || event.target === figure) dialog.close(); });
      image.addEventListener('click', () => {
        if (dialog.classList.contains('is-actual') || image.naturalWidth > image.clientWidth + 8) dialog.classList.toggle('is-actual');
      });
      dialog.addEventListener('close', () => {
        dialog.classList.remove('is-actual');
        image.removeAttribute('src');
        opener?.focus({ preventScroll: true });
      });
      document.body.append(dialog);
    };
    for (const link of links) {
      link.addEventListener('click', event => {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        if (!dialog) build();
        const source = link.querySelector('img');
        const text = link.closest('figure')?.querySelector('figcaption')?.textContent.trim() || '';
        opener = link;
        image.src = link.href;
        image.alt = source?.alt || '';
        original.href = link.href;
        caption.textContent = text;
        caption.hidden = !text;
        dialog.showModal();
      });
    }
  }

  /* ---------- 目录：当前章节、阅读进度、窄屏浮层 ---------- */
  const rail = document.querySelector('.toc-rail');
  if (rail) setupToc(rail);

  function setupToc(rail) {
    const links = [...rail.querySelectorAll('.toc-list a')];
    const targets = links.map(a => { try { return document.getElementById(decodeURIComponent(a.hash.slice(1))); } catch { return null; } });
    const groups = links.map(a => a.closest('.toc-h2'));
    const groupTitles = groups.map(g => g?.querySelector(':scope > a')?.textContent || '目录');
    const scroller = rail.querySelector('.toc-scroll');
    const bar = document.querySelector('.reading-bar');
    const button = bar?.querySelector('.toc-toggle');
    const current = bar?.querySelector('.reading-current');
    const progress = document.querySelector('.reading-progress span');
    const compact = matchMedia('(max-width: 1023px)');
    let active = -2;
    let ticking = false;
    let lockUntil = 0;
    let userScrolledToc = 0;
    let hoverToc = false;
    let open = false;
    let backdrop = null;

    // 只有当前项滚出目录可见范围时才挪动目录本身，不碰页面滚动，鼠标在目录上或刚手动滚过目录时也不动。
    function follow(i, force = false) {
      const link = links[i];
      if (!link || (!force && (hoverToc || performance.now() - userScrolledToc < 1500))) return;
      const box = scroller.getBoundingClientRect();
      const r = link.getBoundingClientRect();
      if (force || r.top < box.top + 24 || r.bottom > box.bottom - 24) scroller.scrollTop += r.top - box.top - box.height / 3;
    }

    function setActive(i) {
      if (i === active) return;
      active = i;
      links.forEach((a, j) => {
        a.classList.toggle('is-active', j === i);
        if (j === i) a.setAttribute('aria-current', 'location'); else a.removeAttribute('aria-current');
      });
      for (const group of new Set(groups)) group?.classList.toggle('is-open', group === groups[i]);
      if (current) current.textContent = i >= 0 ? groupTitles[i] : '目录';
      follow(i);
    }

    function update() {
      ticking = false;
      const max = document.documentElement.scrollHeight - innerHeight;
      if (progress) progress.style.transform = `scaleX(${max > 0 ? Math.min(1, Math.max(0, scrollY / max)) : 1})`;
      if (performance.now() < lockUntil) return;
      const line = (compact.matches && bar ? bar.offsetHeight : 0) + 40;
      let next = -1;
      for (let i = 0; i < targets.length; i++) {
        const top = targets[i]?.getBoundingClientRect().top;
        if (top === undefined) continue;
        if (top <= line || (scrollY >= max - 2 && top < innerHeight * .5)) next = i; else break;
      }
      setActive(next);
    }
    const schedule = () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } };
    addEventListener('scroll', schedule, { passive: true });
    addEventListener('resize', schedule, { passive: true });
    addEventListener('scrollend', () => { lockUntil = 0; schedule(); });
    scroller.addEventListener('wheel', () => { userScrolledToc = performance.now(); }, { passive: true });
    scroller.addEventListener('touchmove', () => { userScrolledToc = performance.now(); }, { passive: true });
    rail.addEventListener('pointerenter', event => { hoverToc = event.pointerType === 'mouse'; });
    rail.addEventListener('pointerleave', () => { hoverToc = false; });

    // 点目录后先把高亮定在目标上，滚动结束前不随中间经过的章节来回跳。
    links.forEach((a, i) => a.addEventListener('click', () => {
      setActive(i);
      lockUntil = performance.now() + 1000;
      if (open) setOpen(false, false);
    }));

    function setOpen(value, restoreFocus = true) {
      if (!button || value === open) return;
      open = value;
      button.setAttribute('aria-expanded', String(open));
      if (open) {
        rail.style.setProperty('--panel-top', `${Math.round(Math.max(8, bar.getBoundingClientRect().bottom + 8))}px`);
        if (!backdrop) {
          backdrop = el('div', 'toc-backdrop');
          backdrop.addEventListener('click', () => setOpen(false));
          document.body.append(backdrop);
        }
        rail.classList.add('is-open');
        backdrop.classList.add('is-visible');
        requestAnimationFrame(() => {
          follow(Math.max(active, 0), true);
          (links[active] || links[0])?.focus({ preventScroll: true });
        });
      } else {
        rail.classList.remove('is-open');
        backdrop?.classList.remove('is-visible');
        if (restoreFocus && rail.contains(document.activeElement)) button.focus({ preventScroll: true });
      }
    }
    button?.addEventListener('click', () => setOpen(!open));
    document.addEventListener('keydown', event => { if (event.key === 'Escape' && open) { event.preventDefault(); setOpen(false); } });
    rail.addEventListener('focusout', event => {
      if (open && event.relatedTarget && !rail.contains(event.relatedTarget) && event.relatedTarget !== button) setOpen(false, false);
    });
    compact.addEventListener('change', () => { if (!compact.matches) setOpen(false, false); schedule(); });
    update();
  }
})();
