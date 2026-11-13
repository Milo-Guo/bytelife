/* 标签管理：本机草稿与线上版本分开保存，发布时按文章核对冲突。令牌只存在页面内存。 */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const L = ByteLifeLabels;
  const data = JSON.parse($('manager-data').textContent);
  const managed = data.managed === true;
  let autoSaveTimer = 0, cloudStatus = '';
  const API = 'https://api.github.com';
  const repoPath = `/repos/${data.repo}`;
  const STORE = `bytelife-labels:v1:${data.repo}`;
  const dialog = $('manager-dialog');
  let articles = data.articles;
  let base = L.snapshot(data.tags, articles), draft = L.clone(base);
  let token = '', login = '', busy = false, storageFailed = false, onlineLoaded = false, opener = null;
  const selected = new Set();
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  function button(text, action, cls = 'button') {
    const node = el('button', cls, text); node.type = 'button'; node.addEventListener('click', action); return node;
  }
  function link(text, url) {
    const node = el('a', 'dialog-link', text); node.href = url; node.target = '_blank'; node.rel = 'noopener'; return node;
  }
  const dirty = () => !L.same(base, draft);
  const tagIds = slug => draft.articles.find(a => a.slug === slug)?.tags || [];
  const tagCount = id => draft.articles.filter(a => a.tags.includes(id)).length;
  function say(text = '', kind = '', url = '') {
    const node = $('manager-message'); node.replaceChildren(document.createTextNode(text));
    node.dataset.kind = kind; node.hidden = !text;
    if (url) node.append(' ', link('查看发布进度 ↗', url));
  }
  function syncStatus() {
    const changed = dirty();
    $('main').setAttribute('aria-busy', String(busy));
    document.querySelector('.manager-savebar').dataset.dirty = String(changed);
    $('manager-status').textContent = managed ? (busy ? '正在同步，请稍候……' : changed ? (storageFailed ? '尚未同步 · 本机备份不可用，请保持页面打开' : '尚未同步 · 本机草稿已保留') : cloudStatus || (onlineLoaded ? '已与后台同步' : '正在载入……')) : busy ? '正在连接 GitHub，请稍候……' : changed
      ? (storageFailed ? '有未发布更改 · 本机存储不可用，请导出备份' : '有未发布更改 · 已自动保存到本机') : (onlineLoaded ? '已与线上版本同步' : '当前为随网站发布的版本');
    $('manager-publish').disabled = busy || !changed;
    $('manager-connect').disabled = busy;
    $('manager-connect').textContent = managed ? '同步设置' : login ? `已连接 ${login} · 断开` : '连接 GitHub';
    document.querySelector('.manager-grid').inert = busy;
    // 自动保存可能在用户刚打开下一个弹窗时开始，暂时锁住弹窗以免覆盖后续输入。
    dialog.inert = busy;
    $('manager-reload').disabled = busy;
    $('manager-export').disabled = busy;
  }
  function save() {
    try {
      if (dirty()) localStorage.setItem(STORE, JSON.stringify({ version: 1, base, draft, articles, at: Date.now() }));
      else localStorage.removeItem(STORE);
      storageFailed = false;
    } catch { storageFailed = true; }
    syncStatus();
  }
  function restore() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORE) || 'null');
      if (!saved) return;
      if (saved.version !== 1 || !Array.isArray(saved.articles)) throw new Error();
      validateArticles(saved.articles, saved.base.tags);
      const oldBase = L.snapshot(saved.base.tags, saved.base.articles);
      const oldDraft = L.snapshot(saved.draft.tags, saved.draft.articles);
      if (!L.same(oldBase.articles.map(a => a.slug), oldDraft.articles.map(a => a.slug))) throw new Error();
      for (const a of oldBase.articles) L.validateIds(a.tags, oldBase.tags);
      for (const a of oldDraft.articles) L.validateIds(a.tags, oldDraft.tags);
      base = oldBase; draft = oldDraft; articles = saved.articles;
      say('已恢复上次未发布的更改，可以继续整理。');
    } catch { say('本机草稿格式无法读取，暂时显示网站版本。', 'error'); }
  }
  function changed() {
    save(); render();
    if (managed) { clearTimeout(autoSaveTimer); autoSaveTimer = setTimeout(autoSave, 700); }
  }
  function autoSave() {
    if (!dirty() || busy) return;
    if (dialog.open) { autoSaveTimer = setTimeout(autoSave, 700); return; }
    publish();
  }
  function visibleArticles() {
    const q = $('manager-search').value.trim().toLocaleLowerCase();
    const filter = $('manager-filter').value;
    return articles.filter(a => a.title.toLocaleLowerCase().includes(q) && (!filter || (filter === '_none' ? !tagIds(a.slug).length : tagIds(a.slug).includes(filter))));
  }
  function syncSelection() {
    const visible = visibleArticles();
    const count = visible.filter(a => selected.has(a.slug)).length;
    $('select-visible').checked = visible.length > 0 && count === visible.length;
    $('select-visible').indeterminate = count > 0 && count < visible.length;
    $('select-visible').disabled = !visible.length;
    $('selection-count').textContent = selected.size ? `已选 ${selected.size} 篇${selected.size > count ? `（含列表外 ${selected.size - count} 篇）` : ''}` : '未选择文章';
    $('selection-clear').hidden = !selected.size;
    $('batch-actions').hidden = !selected.size;
  }
  function renderArticles() {
    const visible = visibleArticles();
    $('article-total').textContent = `${visible.length} / ${articles.length}`;
    const rows = visible.map(article => {
      const row = el('li', 'manager-article'); row.dataset.slug = article.slug;
      const check = el('input'); check.type = 'checkbox'; check.checked = selected.has(article.slug);
      check.setAttribute('aria-label', `选择：${article.title}`);
      check.addEventListener('change', () => { if (check.checked) selected.add(article.slug); else selected.delete(article.slug); syncSelection(); });
      const content = el('div');
      const title = el('a', 'manager-article-title', article.title);
      title.href = article.draft ? `${data.base}write/?a=${article.slug}` : `${data.base}articles/${article.slug}/`;
      title.target = '_blank'; title.rel = 'noopener';
      const badges = el('div', 'manager-article-tags');
      for (const id of tagIds(article.slug)) {
        const tag = draft.tags.find(t => t.id === id); if (tag) badges.append(L.badge(tag));
      }
      if (!badges.childElementCount) badges.append(el('span', 'tag-pill tag-unassigned', '未分类'));
      content.append(title, el('p', 'manager-article-date', `${article.draft ? '草稿 · ' : ''}更新 ${article.updated}`), badges);
      const edit = button('编辑标签', () => assignDialog([article.slug]), 'text-button');
      edit.setAttribute('aria-label', `编辑标签：${article.title}`);
      row.append(check, content, edit); return row;
    });
    $('manager-articles').replaceChildren(...(rows.length ? rows : [el('li', 'manager-empty', '这里还没有文章。试试其他标签，或清空搜索。')]));
    syncSelection();
  }
  function render() {
    $('tag-total').textContent = draft.tags.length;
    $('tag-list').replaceChildren(...draft.tags.map(tag => {
      const row = button('', () => editTag(tag.id), 'manager-tag-row'); row.dataset.tagId = tag.id;
      const dot = el('span', 'tag-dot'); dot.dataset.tagColor = tag.color; dot.setAttribute('aria-hidden', 'true');
      row.append(dot, el('span', 'tag-name', tag.name), el('span', 'tag-count', tagCount(tag.id)), el('span', 'tag-edit', '编辑'));
      row.setAttribute('aria-label', `编辑标签 ${tag.name}，${tagCount(tag.id)} 篇文章`); return row;
    }));
    if (!draft.tags.length) $('tag-list').append(el('p', 'manager-empty', '从第一个标签开始。比如“编程”或“生活”。'));
    const filter = $('manager-filter'), value = filter.value;
    filter.replaceChildren(...[['', '全部标签'], ...draft.tags.map(t => [t.id, t.name]), ['_none', '未分类']].map(([id, text]) => {
      const option = el('option', '', text); option.value = id; return option;
    }));
    filter.value = [...filter.options].some(o => o.value === value) ? value : '';
    renderArticles(); syncStatus();
  }
  function openDialog(title) {
    opener = document.activeElement;
    const head = el('div', 'manager-dialog-head');
    const heading = el('h2', '', title); heading.id = 'manager-dialog-title';
    const close = button('×', () => dialog.close(), 'icon-button'); close.setAttribute('aria-label', '关闭');
    head.append(heading, close); dialog.replaceChildren(head);
    if (!dialog.open) dialog.showModal();
    return dialog;
  }
  dialog.addEventListener('close', () => {
    // 连接成功后会立即打开发布确认；旧窗口的异步 close 事件不能清空新窗口。
    if (dialog.open) return;
    dialog.replaceChildren();
    if (busy) $('manager-status').focus({ preventScroll: true });
    else if (opener?.isConnected) opener.focus({ preventScroll: true });
    else $('tag-new').focus({ preventScroll: true });
  });
  function actions(...buttons) { const row = el('div', 'dialog-actions'); row.append(...buttons); return row; }
  function editTag(id = '') {
    const tag = draft.tags.find(t => t.id === id);
    const body = openDialog(tag ? '编辑标签' : '新建标签');
    const label = el('label', 'dialog-label', '标签名称');
    const name = el('input'); name.type = 'text'; name.maxLength = 48; name.placeholder = '例如：AI 编程、课堂笔记'; name.value = tag?.name || '';
    label.append(name);
    const colors = el('fieldset'); colors.append(el('legend', '', '圆点颜色'));
    const palette = el('div', 'tag-palette');
    for (const [value, text] of Object.entries(L.palette)) {
      const swatch = el('label', 'tag-swatch'); const radio = el('input');
      radio.type = 'radio'; radio.name = 'tag-color'; radio.value = value; radio.dataset.tagColor = value;
      radio.checked = value === (tag?.color || 'blue'); radio.setAttribute('aria-label', text);
      swatch.append(radio, el('span', '', text)); palette.append(swatch);
    }
    colors.append(palette);
    const preview = el('div', 'tag-preview');
    const current = () => ({ name: L.normalizeName(name.value) || '你的标签', color: palette.querySelector('input:checked').value });
    const update = () => preview.replaceChildren(el('span', '', '显示效果'), L.badge(current()));
    name.addEventListener('input', update); palette.addEventListener('change', update); update();
    const error = el('p', 'dialog-error'); error.setAttribute('role', 'alert');
    const apply = button(tag ? '保存标签' : '创建标签', () => {
      try {
        const next = { ...(tag || {}), id: id || `tag-${crypto.randomUUID().slice(0, 18)}`, ...current(), name: L.normalizeName(name.value) };
        // 把旧名字保留为链接别名，之前分享的 ?c=名称 仍能打开对应标签。
        if (tag && tag.name !== next.name) next.aliases = [...new Set([...(tag.aliases || []), tag.name])];
        draft.tags = L.validateTags(tag ? draft.tags.map(t => t.id === id ? next : t) : [...draft.tags, next]);
        changed(); dialog.close();
      } catch (e) { error.textContent = e.message; }
    }, 'button button-primary');
    const remove = tag ? [button('删除标签', () => deleteTag(tag), 'text-button danger-button')] : [];
    body.append(label, colors, preview, error, actions(...remove, button('取消', () => dialog.close()), apply));
    name.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.isComposing) apply.click(); });
    name.focus();
  }
  function deleteTag(tag) {
    const body = openDialog(`删除“${tag.name}”？`);
    body.append(el('p', '', `这个标签用于 ${tagCount(tag.id)} 篇文章。删除后会移除这些关联，文章正文会保留；没有其他标签的文章会显示为“未分类”。`));
    body.append(actions(button('取消', () => dialog.close()), button('删除标签', () => {
      draft.tags = draft.tags.filter(t => t.id !== tag.id);
      for (const a of draft.articles) a.tags = a.tags.filter(id => id !== tag.id);
      changed(); dialog.close();
    }, 'button button-primary')));
  }
  function assignDialog(slugs, mode = 'replace') {
    if (!slugs.length) return;
    const title = mode === 'replace' ? '选择文章标签' : `${mode === 'add' ? '添加' : '移除'}标签 · ${slugs.length} 篇文章`;
    const body = openDialog(title);
    body.append(el('p', '', mode === 'replace' ? articles.find(a => a.slug === slugs[0]).title : '只修改勾选的标签，文章原有的其他标签会保留。'));
    const choices = el('div', 'tag-options');
    for (const tag of draft.tags) {
      const label = el('label', 'tag-option'), box = el('input'); box.type = 'checkbox'; box.value = tag.id;
      box.checked = mode === 'replace' && tagIds(slugs[0]).includes(tag.id);
      label.append(box, L.badge(tag)); choices.append(label);
    }
    if (!draft.tags.length) body.append(el('p', '', '还没有标签，请关闭此窗口，先点击“＋ 新建”。'));
    const error = el('p', 'dialog-error'); error.setAttribute('role', 'alert');
    body.append(choices, error, actions(button('取消', () => dialog.close()), button('应用到文章', () => {
      const ids = [...choices.querySelectorAll('input:checked')].map(input => input.value);
      if (mode !== 'replace' && !ids.length) { error.textContent = '请至少选择一个标签。'; return; }
      for (const a of draft.articles.filter(a => slugs.includes(a.slug))) {
        a.tags = mode === 'replace' ? [...a.tags.filter(id => ids.includes(id)), ...ids.filter(id => !a.tags.includes(id))]
          : mode === 'add' ? [...new Set([...a.tags, ...ids])] : a.tags.filter(id => !ids.includes(id));
      }
      changed(); dialog.close();
    }, 'button button-primary')));
  }
  async function api(path, { method = 'GET', body } = {}) {
    const headers = { Accept: 'application/vnd.github+json' };
    if (token) headers.Authorization = `Bearer ${token}`;
    if (body) headers['Content-Type'] = 'application/json';
    let response;
    try { response = await fetch(API + path, { method, headers, cache: 'no-store', body: body ? JSON.stringify(body) : undefined, signal: AbortSignal.timeout(25000) }); }
    catch { throw new Error('未收到 GitHub 响应，请检查网络。草稿已保留；如果刚才点击了发布，可以先查看仓库提交记录再重试。'); }
    if (response.ok) return response.status === 204 ? null : response.json();
    if (response.status === 401) { token = ''; login = ''; throw new Error('令牌无效或已过期，请重新连接 GitHub。'); }
    if (response.status === 403 && response.headers.get('x-ratelimit-remaining') === '0') throw new Error('GitHub 读取额度已用完。请连接 GitHub 后重试，或稍后再来；草稿已保留。');
    if (response.status === 409 || response.status === 422) throw new Error('提交期间线上版本发生了变化，发布未完成。请重试；若仍提示冲突，先导出草稿，再重新载入线上版本。');
    if (response.status === 403 || response.status === 404) throw new Error('GitHub 未允许这次操作。请确认令牌已授权 bytelife 仓库，Contents 权限为 Read and write。草稿已保留。');
    throw new Error(`GitHub 暂时无法完成操作（${response.status}）。草稿已保留，请稍后重试。`);
  }
  async function getJson(path, head) {
    const file = await api(`${repoPath}/contents/${path}?ref=${encodeURIComponent(head)}`);
    if (typeof file.content !== 'string') throw new Error('GitHub 返回的文件格式不正确。');
    const bytes = Uint8Array.from(atob(file.content.replace(/\s/g, '')), c => c.charCodeAt(0));
    return JSON.parse(new TextDecoder().decode(bytes));
  }
  function validateArticles(list, tags) {
    const seen = new Set();
    if (!Array.isArray(list)) throw new Error('文章列表格式不正确。');
    for (const a of list) {
      if (!a || typeof a.slug !== 'string' || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(a.slug) || seen.has(a.slug) || typeof a.title !== 'string' || typeof a.updated !== 'string') throw new Error('文章列表内容不正确，请重新载入。');
      seen.add(a.slug); L.validateIds(L.idsFor(a, tags), tags);
    }
  }
  async function remote() {
    if (managed) return ByteLifeStudio.request('/api/catalog');
    const head = (await api(`${repoPath}/git/ref/heads/${data.branch}`)).object.sha;
    const [tagData, articleData] = await Promise.all([getJson('tags.json', head), getJson('articles.json', head)]);
    const tags = L.validateTags(tagData); validateArticles(articleData, tags);
    return { head, tags, articles: articleData };
  }
  function useRemote(latest) {
    onlineLoaded = true;
    articles = latest.articles; base = L.snapshot(latest.tags, articles); draft = L.clone(base); selected.clear(); save(); render();
  }
  async function reload() {
    clearTimeout(autoSaveTimer);
    busy = true; syncStatus();
    try { useRemote(await remote()); say('已载入 GitHub 上的最新标签和文章。'); }
    catch (error) { say(error.message, 'error'); }
    finally { busy = false; syncStatus(); }
  }
  function connect(after) {
    const body = openDialog('连接 GitHub');
    body.append(el('p', '', '连接后可以把整理结果发布到网站。令牌仅在当前页面临时使用，刷新或关闭页面就会清除。'));
    const steps = el('ol');
    const first = el('li', '', '创建细粒度令牌：'); first.append(link('打开 GitHub 设置 ↗', 'https://github.com/settings/personal-access-tokens/new'));
    steps.append(first, el('li', '', 'Repository access 只选 bytelife 仓库。'), el('li', '', 'Repository permissions → Contents 选择 Read and write（读写）。'));
    const label = el('label', 'dialog-label', '粘贴令牌'), input = el('input'); input.type = 'password'; input.autocomplete = 'off'; input.spellcheck = false; label.append(input);
    const error = el('p', 'dialog-error'); error.setAttribute('role', 'alert');
    const go = button('连接', async () => {
      const value = input.value.trim();
      if (!/^(github_pat_|ghp_)[A-Za-z0-9_]{20,}$/.test(value)) { error.textContent = '请粘贴完整的 GitHub 令牌。'; return; }
      go.disabled = true; error.textContent = '正在验证仓库权限……'; token = value;
      try {
        const [user, repository] = await Promise.all([api('/user'), api(repoPath)]);
        if (!repository.permissions?.push) throw new Error('这个账号没有 bytelife 仓库的写入权限。');
        if (!dialog.open || !go.isConnected) { token = ''; return; }
        login = user.login; input.value = ''; dialog.close(); syncStatus();
        if (after) after();
      } catch (e) { token = ''; login = ''; error.textContent = e.message; go.disabled = false; syncStatus(); }
    }, 'button button-primary');
    input.addEventListener('keydown', e => { if (e.key === 'Enter' && !go.disabled) go.click(); });
    body.append(steps, label, error, actions(button('取消', () => dialog.close()), go)); input.focus();
  }
  function publishDialog() {
    if (!dirty() || busy) return;
    if (managed) { publish(); return; }
    if (!token) { connect(publishDialog); return; }
    const body = openDialog('发布标签更改');
    const changedArticles = draft.articles.filter(a => !L.same(a.tags, base.articles.find(b => b.slug === a.slug)?.tags)).length;
    body.append(el('p', '', `${L.same(base.tags, draft.tags) ? '标签名称和颜色没有变化。' : '将更新标签的名称、颜色或列表。'}${changedArticles ? `另有 ${changedArticles} 篇文章的归类需要更新。` : ''}`), el('p', '', '发布后，网站会自动更新，通常需要一两分钟。'));
    body.append(actions(button('继续整理', () => dialog.close()), button('确认发布', () => { dialog.close(); publish(); }, 'button button-primary')));
  }
  async function publish() {
    if (busy || !dirty()) return;
    clearTimeout(autoSaveTimer);
    busy = true; save(); syncStatus(); say();
    try {
      if (managed) {
        const result = await ByteLifeStudio.request('/api/save-labels', { base, draft });
        useRemote(result);
        ByteLifeStudio.watch(result.sha, text => { cloudStatus = text; syncStatus(); });
        return;
      }
      const latest = await remote();
      const merged = L.mergeChanges(base, draft, latest.tags, latest.articles);
      const files = [];
      if (!L.same(merged.tags, latest.tags)) files.push({ path: 'tags.json', mode: '100644', type: 'blob', content: JSON.stringify(merged.tags, null, 2) + '\n' });
      if (!L.same(merged.articles, latest.articles)) files.push({ path: 'articles.json', mode: '100644', type: 'blob', content: JSON.stringify(merged.articles, null, 2) + '\n' });
      if (!files.length) { useRemote(latest); say('线上已经是这份标签内容，无需重复发布。'); return; }
      const parent = await api(`${repoPath}/git/commits/${latest.head}`);
      // 继承当前树，只改两份元数据；正文、图片和其他设备的无关修改均保留。
      const tree = await api(`${repoPath}/git/trees`, { method: 'POST', body: { base_tree: parent.tree.sha, tree: files } });
      const commit = await api(`${repoPath}/git/commits`, { method: 'POST', body: { message: '整理文章标签与分类', tree: tree.sha, parents: [latest.head] } });
      await api(`${repoPath}/git/refs/heads/${data.branch}`, { method: 'PATCH', body: { sha: commit.sha, force: false } });
      useRemote(merged);
      say(`已提交 ${commit.sha.slice(0, 7)}。网站正在自动更新，发布完成后刷新首页即可看到。`, '', `https://github.com/${data.repo}/actions/workflows/pages.yml`);
    } catch (e) { say(e.message, 'error'); }
    finally { busy = false; syncStatus(); }
  }
  $('tag-new').addEventListener('click', () => editTag());
  $('manager-search').addEventListener('input', renderArticles);
  $('manager-filter').addEventListener('change', renderArticles);
  $('select-visible').addEventListener('change', e => {
    for (const article of visibleArticles()) { if (e.target.checked) selected.add(article.slug); else selected.delete(article.slug); }
    renderArticles();
  });
  $('selection-clear').addEventListener('click', () => { selected.clear(); renderArticles(); });
  $('batch-add').addEventListener('click', () => assignDialog([...selected], 'add'));
  $('batch-remove').addEventListener('click', () => assignDialog([...selected], 'remove'));
  $('manager-publish').addEventListener('click', publishDialog);
  $('manager-connect').addEventListener('click', () => { if (managed) { save(); location.assign('/connect'); } else if (token) { token = ''; login = ''; syncStatus(); } else connect(); });
  $('manager-reload').addEventListener('click', () => {
    if (!dirty()) { reload(); return; }
    const body = openDialog('重新载入线上版本？');
    body.append(el('p', '', '这会放弃当前未发布的更改。需要保留时，请先取消并点击页面底部“导出草稿备份”。'), actions(button('保留草稿', () => dialog.close()), button('放弃更改并载入', () => { dialog.close(); reload(); })));
  });
  $('manager-export').addEventListener('click', () => {
    const blob = new Blob([JSON.stringify({ version: 1, base, draft, articles, at: Date.now() }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob), a = el('a'); a.href = url; a.download = `bytelife-labels-${new Date().toISOString().slice(0, 10)}.json`;
    a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    say('已导出标签和文章归类的草稿备份。');
  });
  addEventListener('pagehide', () => { token = ''; login = ''; });
  // 返回缓存页面时同步连接状态，不把已清除的令牌显示为仍然有效。
  addEventListener('pageshow', syncStatus);
  (async () => {
    if (managed) {
      $('manager-publish').textContent = '保存';
      ByteLifeStudio.resume(text => { cloudStatus = text; syncStatus(); });
    }
    restore(); busy = true; render();
    try {
      const latest = await remote();
      if (!dirty()) useRemote(latest);
      else if (!L.same(base, L.snapshot(latest.tags, latest.articles))) say('线上版本有更新，你的本机草稿仍保留。发布时会合并未冲突的更改；同一标签或同一篇文章的冲突需要先处理。');
    } catch (error) { say(`${error.message} 当前显示${dirty() ? '本机草稿' : '随网站发布的版本'}，仍可继续整理。`, 'error'); }
    finally { busy = false; render(); }
  })();
})();
