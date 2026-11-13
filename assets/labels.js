/* 标签共用逻辑：名称和颜色集中管理，文章保存稳定ID；改名不会断开关联。 */
(() => {
  'use strict';
  const palette = { blue: '蓝色', teal: '青绿', violet: '紫色', orange: '橙色', sky: '天蓝', green: '绿色', rose: '玫红', slate: '灰色' };
  const slug = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  const clone = value => JSON.parse(JSON.stringify(value));
  const normalizeName = value => typeof value === 'string' ? value.trim().normalize('NFC') : '';
  function validateTags(input) {
    if (!Array.isArray(input) || input.length > 200) throw new Error('标签列表格式不正确，最多可创建200个标签。');
    const ids = new Set(), names = new Set();
    return input.map(tag => {
      if (!tag || typeof tag !== 'object' || typeof tag.id !== 'string' || !slug.test(tag.id) || tag.id.length > 40 || ids.has(tag.id)) throw new Error('标签编号不正确或重复，请重新载入标签。');
      const name = normalizeName(tag.name);
      if (!name || [...name].length > 24 || ['全部', '未分类'].includes(name)) throw new Error('标签名需为1至24个字，不能叫“全部”或“未分类”。');
      const key = name.toLocaleLowerCase();
      if (names.has(key)) throw new Error(`已经有“${name}”这个标签，请换一个名称。`);
      if (!Object.hasOwn(palette, tag.color)) throw new Error('请选择列表中的一种标签颜色。');
      if (tag.aliases !== undefined && (!Array.isArray(tag.aliases) || tag.aliases.some(alias => typeof alias !== 'string' || !alias.trim() || [...alias].length > 24))) throw new Error('标签的旧名称记录无效。');
      ids.add(tag.id); names.add(key);
      return { id: tag.id, name, color: tag.color, ...(tag.aliases?.length ? { aliases: [...new Set(tag.aliases)] } : {}) };
    });
  }
  function idsFor(article, tags) {
    if (Array.isArray(article.tags)) return article.tags.slice();
    const found = tags.find(tag => tag.name === article.category) || tags.find(tag => tag.aliases?.includes(article.category));
    return found ? [found.id] : [];
  }
  function validateIds(ids, tags) {
    if (!Array.isArray(ids) || ids.some(id => typeof id !== 'string' || !tags.some(tag => tag.id === id)) || new Set(ids).size !== ids.length) throw new Error('文章引用了不存在或重复的标签，请重新选择。');
    return ids;
  }
  function itemsFor(article, tags) {
    return idsFor(article, tags).map(id => tags.find(tag => tag.id === id)).filter(Boolean);
  }
  function badge(tag, tagName = 'span') {
    const node = document.createElement(tagName);
    node.className = 'tag-pill';
    const dot = document.createElement('span');
    dot.className = 'tag-dot';
    dot.dataset.tagColor = Object.hasOwn(palette, tag.color) ? tag.color : 'slate';
    dot.setAttribute('aria-hidden', 'true');
    node.append(dot, document.createTextNode(tag.name));
    return node;
  }
  function snapshot(tags, articles) {
    return { tags: clone(validateTags(tags)), articles: articles.map(a => ({ slug: a.slug, tags: idsFor(a, tags) })) };
  }
  function mergeChanges(base, draft, remoteTags, remoteArticles) {
    const clean = validateTags(draft.tags);
    const latestTags = validateTags(remoteTags);
    const registryChanged = !same(base.tags, clean);
    if (registryChanged && !same(base.tags, latestTags) && !same(clean, latestTags)) throw new Error('标签已在别处更新。当前草稿已保留，请导出草稿后重新载入最新版本再合并。');
    const tags = registryChanged ? clean : latestTags;
    const changed = new Map();
    for (const entry of draft.articles) {
      const previous = base.articles.find(a => a.slug === entry.slug);
      validateIds(entry.tags, clean);
      if (!previous || !same(previous.tags, entry.tags)) changed.set(entry.slug, entry.tags);
    }
    for (const [id] of changed) if (!remoteArticles.some(a => a.slug === id)) throw new Error('要修改的文章已在别处移除，请重新载入列表。');
    const articles = remoteArticles.map(article => {
      let ids = idsFor(article, latestTags);
      if (changed.has(article.slug)) {
        const previous = base.articles.find(a => a.slug === article.slug);
        if (!previous || (!same(previous.tags, ids) && !same(changed.get(article.slug), ids))) throw new Error(`“${article.title}”的标签已在别处更新。请保留草稿并重新载入后合并。`);
        ids = changed.get(article.slug);
      }
      // 删除标签时，不能悄悄移除另一设备刚分配给新文章的标签。
      if (ids.some(id => !tags.some(tag => tag.id === id))) throw new Error(`“${article.title}”正在使用已被移除的标签，请重新载入后检查。`);
      if (!changed.has(article.slug) && !registryChanged) return article;
      const category = tags.find(tag => tag.id === ids[0])?.name || '未分类';
      return { ...article, tags: ids.slice(), category };
    });
    return { tags, articles };
  }
  const api = Object.freeze({ palette, same, clone, normalizeName, validateTags, validateIds, idsFor, itemsFor, badge, snapshot, mergeChanges });
  globalThis.ByteLifeLabels = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
