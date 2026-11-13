/* 使用 Node 内置测试验证合并边界，不向 GitHub 写入。 */
const test = require('node:test');
const assert = require('node:assert/strict');
const L = require('../assets/labels.js');
const tags = [{ id: 'code', name: '编程', color: 'blue', aliases: ['CS'] }, { id: 'notes', name: '笔记', color: 'rose' }];
const articles = [{ slug: 'first', title: '第一篇', category: '编程', tags: ['code'], summary: '保留摘要', updated: '2026-11-13', extra: { keep: true } },
  { slug: 'second', title: '第二篇', category: '未分类', tags: [], updated: '2026-11-12' }];
const baseline = () => L.snapshot(tags, articles);

test('名称、颜色与标签引用均校验；显式空标签不会恢复旧分类', () => {
  assert.throws(() => L.validateTags([...tags, { id: 'duplicate', name: '编程', color: 'green' }]));
  for (const name of ['', '全部', '未分类', '长'.repeat(25)]) assert.throws(() => L.validateTags([{ ...tags[0], name }]));
  assert.throws(() => L.validateTags([{ ...tags[0], color: 'url(evil)' }]));
  assert.throws(() => L.validateIds(['code', 'code'], tags));
  assert.throws(() => L.validateIds(['missing'], tags));
  assert.deepEqual(L.idsFor({ category: 'CS' }, tags), ['code']);
  assert.deepEqual(L.idsFor({ category: 'CS', tags: [] }, tags), []);
  assert.deepEqual(L.idsFor({ category: 'CS' }, [...tags, { id: 'cs', name: 'CS', color: 'teal' }]), ['cs']);
});
test('批量归类保留无关文章和元数据，输入不被修改', () => {
  const base = baseline(), draft = L.clone(base), remote = L.clone(articles);
  draft.articles[0].tags.push('notes');
  remote[0].title = '另一设备改过的标题'; remote[1].summary = '新增摘要';
  remote.push({ slug: 'third', title: '新文', tags: ['notes'], category: '笔记' });
  const before = L.clone(remote), result = L.mergeChanges(base, draft, tags, remote);
  assert.deepEqual(result.articles[0].tags, ['code', 'notes']);
  assert.equal(result.articles[0].title, '另一设备改过的标题');
  assert.deepEqual(result.articles[0].extra, { keep: true });
  assert.deepEqual(result.articles.slice(1), remote.slice(1));
  assert.deepEqual(remote, before); assert.deepEqual(base, baseline());
});
test('集中改名和颜色不丢文章关联', () => {
  const base = baseline(), draft = L.clone(base);
  draft.tags[0].name = 'AI 编程'; draft.tags[0].color = 'violet';
  const result = L.mergeChanges(base, draft, tags, articles);
  assert.equal(result.articles[0].category, 'AI 编程');
  assert.deepEqual(result.articles[0].tags, ['code']);
  assert.equal(result.tags[0].color, 'violet');
});
test('删除标签后保留正文元数据并成为未分类', () => {
  const base = baseline(), draft = L.clone(base);
  draft.tags = draft.tags.filter(t => t.id !== 'code'); draft.articles[0].tags = [];
  const result = L.mergeChanges(base, draft, tags, articles);
  assert.equal(result.articles.length, 2); assert.equal(result.articles[0].category, '未分类');
  assert.equal(result.articles[0].summary, '保留摘要');
});
test('同一文章、标签定义和文章删除的冲突会阻止提交', () => {
  const base = baseline(), draft = L.clone(base), remote = L.clone(articles);
  draft.articles[0].tags = ['notes']; remote[0].tags = [];
  assert.throws(() => L.mergeChanges(base, draft, tags, remote), /别处更新/);
  assert.throws(() => L.mergeChanges(base, draft, tags, articles.slice(1)), /移除/);
  draft.tags[0].name = '本机名字';
  assert.throws(() => L.mergeChanges(base, draft, [{ ...tags[0], name: '远端名字' }, tags[1]], articles), /别处更新/);
});
test('删除标签不能移除其他设备新文章的关联', () => {
  const base = baseline(), draft = L.clone(base);
  draft.tags = [tags[1]]; draft.articles[0].tags = [];
  const remote = [...articles, { slug: 'third', title: '新文', tags: ['code'] }];
  assert.throws(() => L.mergeChanges(base, draft, tags, remote), /正在使用已被移除/);
});
test('只改文章时能合并另一设备的标签改名', () => {
  const base = baseline(), draft = L.clone(base), remoteTags = L.clone(tags);
  draft.articles[1].tags = ['code']; remoteTags[0].name = '程序设计';
  const result = L.mergeChanges(base, draft, remoteTags, articles);
  assert.equal(result.articles[1].category, '程序设计');
  assert.equal(result.tags[0].name, '程序设计');
});
test('已经成功但响应中断的提交可以安全重试', () => {
  const base = baseline(), draft = L.clone(base);
  draft.tags[0].name = '新的名字'; draft.articles[1].tags = ['notes'];
  const first = L.mergeChanges(base, draft, tags, articles);
  const retried = L.mergeChanges(base, draft, first.tags, first.articles);
  assert.deepEqual(retried, first);
});
