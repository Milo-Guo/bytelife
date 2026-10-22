/* 内容和索引都在本站，搜索不向外部服务发送输入。 */
const base = document.body.dataset.base;
const themeButton = document.querySelector('.theme-toggle');
try {
  const theme = localStorage.getItem('bytelife-theme');
  if (theme) document.documentElement.dataset.theme = theme;
} catch { /* 浏览器禁用存储时，仍可正常阅读。 */ }
themeButton?.addEventListener('click', () => {
  const dark = document.documentElement.dataset.theme === 'dark';
  const theme = dark ? 'light' : 'dark';
  document.documentElement.dataset.theme = theme;
  themeButton.setAttribute('aria-label', dark ? '切换深色主题' : '切换浅色主题');
  try { localStorage.setItem('bytelife-theme', theme); } catch { /* 不依赖存储。 */ }
});

const input = document.querySelector('#search');
if (input) {
  const list = document.querySelector('#article-list');
  const status = document.querySelector('#result-status');
  const empty = document.querySelector('#empty-state');
  const initialHTML = list.innerHTML;
  let index = null;
  let indexRequest = null;
  let category = '全部';
  let revision = 0;
  const filters = [...document.querySelectorAll('[data-filter]')];

  function safe(value) {
    return value.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  async function getIndex() {
    if (index) return index;
    if (!indexRequest) indexRequest = fetch(`${base}search-index.json`).then(response => {
      if (!response.ok) throw new Error('索引读取失败');
      return response.json();
    }).then(data => { index = data; return data; }).catch(error => { indexRequest = null; throw error; });
    return indexRequest;
  }

  function excerpt(article, words) {
    const lower = article.text.toLocaleLowerCase();
    const locations = words.map(word => lower.indexOf(word)).filter(n => n >= 0);
    const first = locations.length ? Math.min(...locations) : 0;
    const start = Math.max(0, first - 32);
    const text = article.text.slice(start, start + 155);
    // 逐个片段转义，避免把搜索词当成 HTML 或正则表达式。
    let html = '';
    for (let i = 0; i < text.length;) {
      const word = words.find(w => text.slice(i).toLocaleLowerCase().startsWith(w));
      if (word) { html += `<mark>${safe(text.slice(i, i + word.length))}</mark>`; i += word.length; }
      else { html += safe(text[i]); i++; }
    }
    return `${start ? '…' : ''}${html}…`;
  }

  async function update() {
    const current = ++revision;
    const query = input.value.trim();
    const url = new URL(location.href);
    if (query) url.searchParams.set('q', query); else url.searchParams.delete('q');
    history.replaceState(null, '', url);
    if (!query) {
      list.innerHTML = initialHTML;
      let count = 0;
      for (const row of list.children) {
        row.hidden = category !== '全部' && row.dataset.category !== category;
        if (!row.hidden) count++;
      }
      empty.hidden = count > 0;
      status.textContent = category === '全部' ? '' : `${category} · ${count} 篇`;
      return;
    }
    status.textContent = '正在查找…';
    try {
      const data = await getIndex();
      if (revision !== current) return;
      const words = query.toLocaleLowerCase().split(/\s+/).filter(Boolean);
      const hits = data.filter(a => (category === '全部' || a.category === category) && words.every(w => `${a.title} ${a.text}`.toLocaleLowerCase().includes(w)));
      list.innerHTML = hits.map((a, i) => `<li class="article-row"><span class="row-number">${String(i + 1).padStart(2, '0')}</span><div class="row-content"><div class="row-meta"><span>${safe(a.category)}</span><time>${safe(a.created)}</time></div><h3><a href="${safe(a.url)}">${safe(a.title)}</a></h3><p class="search-excerpt">${excerpt(a, words)}</p></div><a class="row-arrow" aria-label="阅读：${safe(a.title)}" href="${safe(a.url)}">↗</a></li>`).join('');
      status.textContent = `找到 ${hits.length} 篇含“${query}”的文章`;
      empty.hidden = hits.length > 0;
    } catch {
      status.textContent = '搜索索引暂时没有读取成功，请稍后再试。文章目录仍可正常打开。';
    }
  }
  input.addEventListener('input', update);
  filters.forEach(button => button.addEventListener('click', () => {
    category = button.dataset.filter;
    filters.forEach(item => {
      const active = item === button;
      item.classList.toggle('active', active);
      item.setAttribute('aria-pressed', String(active));
    });
    update();
  }));
  document.addEventListener('keydown', event => {
    if (event.key === '/' && !['INPUT','TEXTAREA'].includes(document.activeElement.tagName) && !document.activeElement.isContentEditable) {
      event.preventDefault(); input.focus();
    }
  });
  input.value = new URLSearchParams(location.search).get('q') || '';
  update();
}

document.querySelectorAll('.prose table').forEach(table => {
  const wrapper = document.createElement('div');
  wrapper.className = 'table-scroll';
  wrapper.setAttribute('tabindex', '0');
  wrapper.setAttribute('role', 'region');
  wrapper.setAttribute('aria-label', '表格，可横向滚动');
  table.before(wrapper); wrapper.append(table);
});
document.querySelectorAll('.prose pre').forEach(pre => {
  const code = pre.querySelector('code');
  const button = document.createElement('button');
  button.type = 'button'; button.className = 'copy-code'; button.textContent = '复制';
  button.setAttribute('aria-label', '复制这段代码');
  button.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(code.textContent);
      button.textContent = '已复制';
    } catch { button.textContent = '请手动选中复制'; }
    setTimeout(() => { button.textContent = '复制'; }, 1800);
  });
  const language = document.createElement('span');
  language.className = 'code-language';
  language.textContent = [...code.classList].find(c => c.startsWith('language-'))?.slice(9).toUpperCase() || 'CODE';
  pre.append(language, button);
});

const toc = document.querySelector('.toc');
if (toc) {
  if (matchMedia('(max-width: 700px)').matches) toc.open = false;
  const progress = document.querySelector('.reading-progress');
  const links = [...toc.querySelectorAll('a')];
  const headings = links.map(a => document.getElementById(decodeURIComponent(a.hash.slice(1))));
  let scheduled = false;
  const updateReading = () => {
    scheduled = false;
    const height = document.documentElement.scrollHeight - innerHeight;
    progress.style.width = `${height > 0 ? Math.min(100, scrollY / height * 100) : 100}%`;
    let active = 0;
    headings.forEach((h, i) => { if (h && h.getBoundingClientRect().top <= 160) active = i; });
    links.forEach((a, i) => {
      a.classList.toggle('current', i === active);
      if (i === active) a.setAttribute('aria-current', 'location'); else a.removeAttribute('aria-current');
    });
  };
  addEventListener('scroll', () => { if (!scheduled) { scheduled = true; requestAnimationFrame(updateReading); } }, {passive:true});
  updateReading();
}
