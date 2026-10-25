"""安全回归测试：危险的 Markdown/HTML 不能变成可执行内容，正常写法和旧锚点保持不变。

运行：python scripts/test_build.py
"""
from base64 import b64encode
from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
import check  # noqa: E402
import new  # noqa: E402

AUTHORS = build.load_authors([{'id': 'milo', 'name': 'Milo Guo', 'github': 'Milo-Guo'}, {'id': 'ajie', 'name': '阿杰', 'github': 'a-jie'}])


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.attrs = [], []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attrs.extend((tag, name, value or '') for name, value in attrs)


def parse(html):
    parser = Elements()
    parser.feed(html)
    return parser


def render(markdown):
    return build.render(markdown)[0]


class SanitizeTest(unittest.TestCase):
    def assertInert(self, html):
        """输出里不能有脚本类标签、事件属性、style 属性或危险协议。"""
        page = parse(html)
        self.assertFalse({'script', 'iframe', 'object', 'embed', 'svg', 'math', 'style', 'form', 'base'} & set(page.tags), html)
        for tag, name, value in page.attrs:
            self.assertFalse(name.startswith('on'), html)
            self.assertNotEqual(name, 'style', html)
            if name in ('href', 'src'):
                scheme = re.match(r'\s*([a-z][a-z0-9+.-]*):', re.sub(r'[\t\n\r]', '', value), re.I)
                self.assertTrue(not scheme or scheme[1].lower() in ('http', 'https', 'mailto'), html)

    def test_script_removed_text_kept(self):
        html = render('前文\n\n<script>alert(1)</script>\n\n后文 <script>alert(2)</script>')
        self.assertInert(html)
        self.assertIn('前文', html)
        self.assertIn('后文', html)
        self.assertNotIn('alert(1)', html)

    def test_event_and_style_attributes_removed(self):
        html = render('<img src="../assets/favicon.svg" onerror="alert(1)">\n\n<p onclick="x()" style="color:red" id="ok">文字</p>')
        self.assertInert(html)
        self.assertIn('id="ok"', html)
        self.assertIn('src="/bytelife/assets/favicon.svg"', html)

    def test_dangerous_protocols(self):
        for case in ['[a](javascript:alert(1))', '<a href="javascript:alert(1)">b</a>', '<a href="JaVaScRiPt:alert(1)">c</a>',
                     '<a href="jav&#x09;ascript:alert(1)">d</a>', '<a href="&#106;avascript:alert(1)">e</a>',
                     '<a href=" \x01javascript:alert(1)">f</a>', '<a href="data:text/html,<script>alert(1)</script>">g</a>',
                     '<a href="vbscript:msgbox(1)">h</a>', '[i](data:text/html;base64,PHNjcmlwdD4=)',
                     '<img src="javascript:alert(1)">', '![j](javascript:alert(1))']:
            with self.subTest(case=case):
                self.assertInert(render(case))

    def test_dangerous_containers_dropped_with_content(self):
        html = render('<iframe src="https://example.com"></iframe>\n\n<svg onload="alert(1)"><script>alert(2)</script></svg>\n\n'
                      '<style>body{display:none}</style>\n\n<object data="x.swf"></object>\n\n<noscript><img src=x onerror=alert(3)></noscript>\n\n<!-- 注释 -->正文')
        self.assertInert(html)
        self.assertNotIn('display:none', html)
        self.assertNotIn('注释', html)
        self.assertIn('正文', html)

    def test_attribute_cannot_break_quotes(self):
        html = render('<span id="x&quot; onmouseover=&quot;alert(1)">t</span> <a title="&quot;><img src=x onerror=alert(1)>">u</a>')
        self.assertInert(html)
        self.assertIn('>t</span>', html)

    def test_safe_links_kept(self):
        html = render('[官网](https://git-scm.com/) [邮件](mailto:hi@example.com) [本节](#h-1) [文章](../content/git-basics.md#git-section-02)')
        for href in ('https://git-scm.com/', 'mailto:hi@example.com', '#h-1', '/bytelife/articles/git-basics/#git-section-02'):
            self.assertIn(f'href="{href}"', html)

    def test_code_is_displayed_not_run(self):
        html = render('```html\n<script>alert(1)</script>\n```\n\n行内 `<img src=x onerror=alert(1)>`')
        self.assertInert(html)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)
        self.assertIn('&lt;img src=x onerror=alert(1)&gt;', html)

    def test_legacy_anchors_move_into_headings(self):
        html, toc = build.render('<div><a name="git-section-02"></a></div>\n\n## 02｜安装 Git，及确认\n\n<a name="mc-section-01"></a>\n\n## 01｜先确定\n')
        self.assertIn('<h2 id="h-02-安装-git-及确认"><span class="anchor" id="git-section-02"></span>02｜安装 Git，及确认</h2>', html)
        self.assertIn('<h2 id="h-01-先确定"><span class="anchor" id="mc-section-01"></span>01｜先确定</h2>', html)
        self.assertNotIn('<p></p>', html)
        self.assertEqual([anchor for _, anchor, _ in toc], ['h-02-安装-git-及确认', 'h-01-先确定'])

    def test_callout_figure_table(self):
        html = render('> [!WARNING]\n> 先备份。\n\n![示意图](../assets/favicon.svg)\n\n*图注*\n\n| 命令 | 用途 |\n|:--|--:|\n| `a` | b |')
        self.assertIn('<blockquote class="callout callout-warning">\n<p class="callout-title">注意</p>', html)
        self.assertIn('<a class="figure-link" href="/bytelife/assets/favicon.svg">', html)
        self.assertIn('<figcaption>图注</figcaption>', html)
        self.assertIn('<div class="table-wrap is-pair">', html)
        self.assertIn('class="align-right"', html)
        self.assertInert(html.replace(build.icon('expand'), ''))

    def test_json_ld_cannot_close_script(self):
        page = build.shell('t', 'd', '', 'x/', {'title': '</script><script>alert(1)</script>', 'summary': '<!--',
                                               'created': '2026-01-01', 'updated': '2026-01-01'})
        block = page.split('<script type="application/ld+json">')[1].split('</script>')[0]
        self.assertNotIn('<', block)
        self.assertEqual(json.loads(block)['headline'], '</script><script>alert(1)</script>')

    def test_csp_allows_only_the_theme_script(self):
        page = build.shell('t', 'd', '')
        csp = unescape(re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', page)[1])
        inline = re.search(r'<script>(.*?)</script>', page)[1]
        self.assertIn("'sha256-"+b64encode(sha256(inline.encode()).digest()).decode()+"'", csp)
        self.assertNotIn('unsafe-inline', csp)
        self.assertNotIn('unsafe-eval', csp)
        self.assertIn("require-trusted-types-for 'script'", csp)
        self.assertLess(page.index('Content-Security-Policy'), page.index('<script'))


class MetadataTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.content = Path(self.tmp.name)/'content'
        self.content.mkdir()
        (self.content/'ok-post.md').write_text('正文', encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def meta(self, **changes):
        return {'slug': 'ok-post', 'title': '标题', 'category': '做菜', 'type': 'tutorial', 'author': 'milo', 'summary': '摘要',
                'created': '2026-10-01', 'updated': '2026-10-02', **changes}

    def test_valid_entry(self):
        self.assertEqual(build.validate_articles([self.meta()], self.content, authors=AUTHORS)[0]['slug'], 'ok-post')

    def test_unsafe_slugs_rejected(self):
        for slug in ['../secret', '..', 'a/b', 'a\\b', 'Upper', 'x.md', 'a_b', '', ' ok-post', 'ok-post/']:
            with self.subTest(slug=slug), self.assertRaises(SystemExit):
                build.validate_articles([self.meta(slug=slug)], self.content, authors=AUTHORS)

    def test_other_bad_metadata(self):
        for changes in [{'slug': 'missing'}, {'created': '2026/10/01'}, {'updated': '2026-09-01'}, {'category': '全部'},
                        {'title': ''}, {'note': {'date': '2026-10-02', 'text': '更新', 'anchor': 'x" onclick="y'}}]:
            with self.subTest(changes=changes), self.assertRaises(SystemExit):
                build.validate_articles([self.meta(**changes)], self.content, authors=AUTHORS)
        with self.assertRaises(SystemExit):
            build.validate_articles([self.meta(), self.meta()], self.content, authors=AUTHORS)

    def test_type_draft_and_recipe_fields(self):
        build.validate_articles([self.meta(type='recipe', draft=True, recipe={'servings': '2 人份', 'minutes': 20})], self.content, authors=AUTHORS)
        build.validate_articles([self.meta(type='post', draft=False)], self.content, authors=AUTHORS)
        bad = [{'type': None}, {'type': 'video'}, {'draft': 'yes'}, {'recipe': {'minutes': 20}},
               {'type': 'recipe', 'recipe': {'minutes': '20'}}, {'type': 'recipe', 'recipe': {'minutes': True}},
               {'type': 'recipe', 'recipe': {'minutes': 0}}, {'type': 'recipe', 'recipe': {'servings': ''}},
               {'type': 'recipe', 'recipe': {'calories': 300}}, {'type': 'recipe', 'recipe': '2 人份'}]
        for changes in bad:
            with self.subTest(changes=changes), self.assertRaises(SystemExit):
                build.validate_articles([self.meta(**changes)], self.content, authors=AUTHORS)


    def test_author_field(self):
        build.validate_articles([self.meta(author=['milo', 'ajie'])], self.content, authors=AUTHORS)
        for value in [None, '', [], 'nobody', ['milo', 'milo'], ['milo', 'nobody'], 3]:
            with self.subTest(author=value), self.assertRaises(SystemExit):
                build.validate_articles([self.meta(author=value)], self.content, authors=AUTHORS)

    def test_authors_file(self):
        good = {'id': 'ajie', 'name': '阿杰'}
        build.load_authors([good, {'id': 'b', 'name': 'B', 'github': 'b-user', 'bio': '简介', 'url': 'https://b.example.com/'}])
        bad = [[], [{'id': 'Bad', 'name': 'x'}], [{'id': '../x', 'name': 'x'}], [good, good], [{'id': 'a', 'name': ''}],
               [{'id': 'a', 'name': 'a', 'github': 'bad name'}], [{'id': 'a', 'name': 'a', 'url': 'javascript:alert(1)'}],
               [{'id': 'a', 'name': 'a', 'url': 'http://plain.example.com'}], [{'id': 'a', 'name': 'a', 'email': 'x@y.z'}],
               [{'id': 'a', 'name': 'a', 'github': 'Same'}, {'id': 'b', 'name': 'b', 'github': 'same'}]]
        for data in bad:
            with self.subTest(data=data), self.assertRaises(SystemExit):
                build.load_authors(data)


class TypeTest(unittest.TestCase):
    RECIPE = ('开头。\n\n## 用料\n\n- 鸡蛋 3 个\n- 番茄 2 个，切块\n  - 嵌套说明不算一项\n- `盐` 适量 [链接](https://example.com)\n\n'
              '## 做法\n\n1. 鸡蛋炒熟盛出。\n2. 番茄炒出汁，\n   再倒回鸡蛋。\n\n## 小贴士\n\n- 这一节的列表不算步骤。\n')

    def test_recipe_parts_from_markdown(self):
        parts = build.recipe_parts(self.RECIPE)
        self.assertEqual(parts['ingredients'], ['鸡蛋 3 个', '番茄 2 个，切块', '盐 适量 链接'])
        self.assertEqual(parts['steps'], ['鸡蛋炒熟盛出。', '番茄炒出汁， 再倒回鸡蛋。'])

    def test_structured_data_by_type(self):
        base = {'title': '番茄炒蛋', 'summary': '家常菜', 'category': '做菜', 'created': '2026-11-01', 'updated': '2026-11-01'}
        self.assertEqual(build.structured_data(base, 'u')['@type'], 'TechArticle')
        self.assertEqual(build.structured_data({**base, 'type': 'post'}, 'u')['@type'], 'BlogPosting')
        recipe = build.structured_data({**base, 'type': 'recipe', 'recipe': {'servings': '2 人份', 'minutes': 20},
                                        'recipe_parts': build.recipe_parts(self.RECIPE), 'image': 'https://x/a.png'}, 'u')
        self.assertEqual((recipe['@type'], recipe['name'], recipe['recipeYield'], recipe['totalTime'], recipe['image']),
                         ('Recipe', '番茄炒蛋', '2 人份', 'PT20M', ['https://x/a.png']))
        self.assertEqual(recipe['recipeInstructions'][0], {'@type': 'HowToStep', 'text': '鸡蛋炒熟盛出。'})
        self.assertEqual(len(recipe['recipeIngredient']), 3)

    def test_recipe_facts_shown_only_for_recipes(self):
        self.assertEqual(build.recipe_facts({'type': 'recipe', 'recipe': {'servings': '<b>2</b> 人份', 'minutes': 20}}),
                         ['&lt;b&gt;2&lt;/b&gt; 人份', '约 20 分钟'])
        self.assertEqual(build.recipe_facts({'type': 'tutorial', 'recipe': {'minutes': 20}}), [])


class HomeToolsTest(unittest.TestCase):
    def test_home_note_optional_and_invalid_values_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(build.read_home_note(root), '')
            for value in [[], {'now': 123}, {'now': '字' * 201}]:
                (root/'home.json').write_text(json.dumps(value), encoding='utf-8')
                with self.subTest(value=type(value).__name__), self.assertRaises(SystemExit):
                    build.read_home_note(root)
            (root/'home.json').write_text('{broken', encoding='utf-8')
            with self.assertRaises(SystemExit):
                build.read_home_note(root)
            (root/'home.json').write_text('{"now":"  继续整理笔记  "}', encoding='utf-8')
            self.assertEqual(build.read_home_note(root), '继续整理笔记')

    def test_home_note_cannot_inject_html(self):
        meta = {'slug': 'hello', 'title': '标题', 'category': '编程', 'summary': '摘要',
                'created': '2026-10-25', 'updated': '2026-10-25', 'author': 'milo', 'author_list': [AUTHORS['milo']]}
        html = build.home_page([meta], '/bytelife/search-index.json', '<script>alert(1)</script>')
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)
        self.assertNotIn('home-now', build.home_page([meta], '/bytelife/search-index.json'))

    def test_bookmark_title_cannot_break_attributes(self):
        title = '" onmouseover="alert(1) <img src=x>'
        html = build.bookmark_button('hello', title)
        page = parse(html)
        self.assertFalse(any(name.startswith('on') for _, name, _ in page.attrs))
        self.assertNotIn('img', page.tags)
        self.assertIn(('button', 'data-article-title', title), page.attrs)


class NewArticleTest(unittest.TestCase):
    ORIGINAL = ('[\r\n  {\r\n    "slug": "old-post",\r\n    "title": "旧文",\r\n    "category": "编程",\r\n    "type": "tutorial",\r\n    "author": "milo",\r\n'
                '    "summary": "摘要",\r\n    "created": "2026-10-01",\r\n    "updated": "2026-10-01"\r\n  }\r\n]\r\n')

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root/'content').mkdir()
        (self.root/'content'/'old-post.md').write_text('旧文', encoding='utf-8')
        (self.root/'articles.json').write_bytes(self.ORIGINAL.encode('utf-8'))
        (self.root/'authors.json').write_text(json.dumps([{'id': 'milo', 'name': 'Milo Guo', 'github': 'Milo-Guo'},
                                                          {'id': 'ajie', 'name': '阿杰', 'github': 'a-jie'}]), encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def meta(self, **changes):
        return {'slug': 'tomato-egg', 'title': '番茄炒蛋', 'category': '做菜', 'type': 'recipe', 'author': 'ajie', 'summary': '家常菜',
                'created': '2026-11-01', 'updated': '2026-11-01', 'draft': True, **changes}

    def catalog_text(self):
        return (self.root/'articles.json').read_bytes().decode('utf-8')

    def test_creates_draft_from_template(self):
        path = new.create_article(self.meta(recipe={'servings': '2 人份'}), self.root)
        self.assertIn('## 用料', path.read_text(encoding='utf-8'))
        text = self.catalog_text()
        self.assertTrue(text.startswith(self.ORIGINAL[:-len('  }\r\n]\r\n')]), '原有条目的写法不应改变')
        self.assertNotIn('\n', text.replace('\r\n', ''), '沿用原文件的 CRLF 换行')
        added = json.loads(text)[-1]
        self.assertEqual((added['slug'], added['draft'], added['recipe']), ('tomato-egg', True, {'servings': '2 人份'}))

    def test_refuses_unsafe_or_conflicting_input(self):
        (self.root/'content'/'taken.md').write_text('别覆盖我', encoding='utf-8')
        for changes in [{'slug': '../evil'}, {'slug': 'old-post'}, {'slug': 'taken'}, {'category': '全部'}, {'type': 'video'}, {'author': 'nobody'}]:
            with self.subTest(changes=changes), self.assertRaises((SystemExit, FileNotFoundError)):
                new.create_article(self.meta(**changes), self.root)
            self.assertEqual(self.catalog_text(), self.ORIGINAL)
        self.assertEqual((self.root/'content'/'taken.md').read_text(encoding='utf-8'), '别覆盖我')
        self.assertEqual(sorted(p.name for p in (self.root/'content').iterdir()), ['old-post.md', 'taken.md'])
        self.assertFalse((self.root/'evil.md').exists())


    def test_resolve_author(self):
        self.assertEqual(new.resolve_author(AUTHORS, 'ajie'), 'ajie')
        self.assertEqual(new.resolve_author(AUTHORS, 'milo，ajie'), ['milo', 'ajie'])
        self.assertEqual(new.resolve_author(AUTHORS, github_user='A-JIE'), 'ajie')
        self.assertEqual(new.resolve_author(AUTHORS), 'milo')
        for args in [('nobody',), (None, 'stranger')]:
            with self.subTest(args=args), self.assertRaises(SystemExit):
                new.resolve_author(AUTHORS, *args)


class AuthorPageTest(unittest.TestCase):
    def article(self, slug, author, **extra):
        meta = {'slug': slug, 'title': f'标题 {slug}', 'category': '做菜', 'type': 'post', 'author': author, 'summary': '摘要',
                'created': '2026-10-01', 'updated': '2026-10-02', **extra}
        meta['author_list'] = [AUTHORS[i] for i in build.author_ids(meta)]
        return meta

    def test_structured_data_names_real_authors(self):
        one = build.structured_data(self.article('a', 'milo'), 'u')
        self.assertEqual(one['author'], {'@type': 'Person', 'name': 'Milo Guo', 'url': build.ORIGIN+'/bytelife/authors/milo/',
                                         'sameAs': ['https://github.com/Milo-Guo']})
        two = build.structured_data(self.article('b', ['milo', 'ajie']), 'u')
        self.assertEqual([p['name'] for p in two['author']], ['Milo Guo', '阿杰'])

    def test_author_page_lists_only_their_articles(self):
        articles = [self.article('mine', 'ajie'), self.article('shared', ['milo', 'ajie']), self.article('other', 'milo')]
        page = build.author_page(AUTHORS['ajie'], articles)
        self.assertIn('/bytelife/articles/mine/', page)
        self.assertIn('/bytelife/articles/shared/', page)
        self.assertNotIn('/bytelife/articles/other/', page)
        self.assertIn('2 篇文章', page)
        self.assertIn('https://github.com/a-jie', page)

    def test_author_text_is_escaped(self):
        evil = build.load_authors([{'id': 'x', 'name': '<img src=x onerror=alert(1)>', 'bio': '<script>alert(2)</script>'}])['x']
        page = build.author_page(evil, [])
        self.assertNotIn('<img', page)
        self.assertNotIn('<script', page)
        meta = self.article('a', 'milo')
        meta['author_list'] = [evil]
        self.assertNotIn('<img', build.byline(meta))
        self.assertNotIn('<img', build.authors_index({'x': evil}, []))


class EditorAndHistoryTest(unittest.TestCase):
    def test_only_editor_page_can_reach_github_api(self):
        self.assertNotIn('api.github.com', build.CSP)
        self.assertIn("connect-src 'self' https://api.github.com", build.EDITOR_CSP)
        self.assertIn('trusted-types bytelife-preview', build.EDITOR_CSP)
        for csp in (build.CSP, build.EDITOR_CSP):
            self.assertNotIn('unsafe-inline', csp)
            self.assertNotIn('unsafe-eval', csp)

    def test_editor_data_cannot_break_out_of_script(self):
        catalog = [{'slug': 'a', 'title': '</script><script>alert(1)</script>', 'category': '做菜', 'type': 'recipe',
                    'summary': '<!--', 'created': '2026-10-01', 'updated': '2026-10-01'}]
        page = build.editor_page(catalog, AUTHORS)
        blob = page.split('id="editor-data">')[1].split('</script>')[0]
        self.assertNotIn('<', blob)
        data = json.loads(blob)
        self.assertEqual(data['articles'][0]['title'], catalog[0]['title'])
        self.assertEqual(set(data['templates']), set(build.TYPES))
        self.assertEqual(data['repo'], 'Milo-Guo/bytelife')
        self.assertEqual([a['id'] for a in data['authors']], ['milo', 'ajie'])

    def test_revisions_come_from_git(self):
        self.assertEqual(build.revisions('content/no-such-file.md'), [])
        for rev in build.revisions('content/git-basics.md'):
            self.assertRegex(rev['sha'], r'^[0-9a-f]{40}$')
            self.assertRegex(rev['date'], r'^\d{4}-\d{2}-\d{2}$')

    def test_revision_messages_are_escaped(self):
        html = build.revisions_html('content/x.md', [{'sha': 'a'*40, 'date': '2026-10-22', 'message': '<img src=x onerror=alert(1)>'}])
        self.assertNotIn('<img', html)
        self.assertIn('&lt;img', html)
        self.assertIn('#diff-'+sha256(b'content/x.md').hexdigest(), html)
        self.assertEqual(build.revisions_html('content/x.md', []), '')

    def test_workflow_inputs_only_pass_through_env(self):
        """工作流里表单输入只能通过环境变量传给脚本，不能直接拼进 run 命令，避免命令注入。"""
        for path in (build.ROOT/'.github'/'workflows').glob('*.yml'):
            for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                if '${{' in line and ('inputs.' in line or 'github.event' in line):
                    self.assertRegex(line, r'^\s+[A-Z_]+: \$\{\{ inputs\.\w+ \}\}$', f'{path.name}:{number}')


class OutputTest(unittest.TestCase):
    def test_write_stays_inside_site(self):
        with self.assertRaises(SystemExit):
            build.write('../outside.txt', 'x')
        self.assertFalse((build.ROOT/'outside.txt').exists())

    def test_only_web_assets_published(self):
        allowed = ['site.css', 'site.js', 'favicon.svg', 'images/a/b.png', 'images/c.JPEG', 'IMAGE-SOURCES.md']
        blocked = ['.env', 'images/.hidden.png', '.git/config', 'backup.sql', 'notes.md', 'dump.zip', 'secret.key', 'images/raw.psd']
        for name in allowed:
            self.assertTrue(build.is_public_asset(Path(name)), name)
        for name in blocked:
            self.assertFalse(build.is_public_asset(Path(name)), name)


class CheckTest(unittest.TestCase):
    """check.py 本身要能发现问题，避免检查“永远通过”。"""

    def problems(self, html):
        page = check.Page()
        page.feed(html)
        errors = []
        check.page_rules(check.OUT/'x.html', page, errors)
        return errors

    def test_detects_unsafe_pages(self):
        good = build.shell('t', 'd', '<main>ok</main>')
        self.assertEqual(self.problems(good), [])
        self.assertTrue(self.problems(good.replace('<main>ok', '<main onclick="x()">ok')))
        self.assertTrue(self.problems(good.replace('<main>ok', '<main><script>alert(1)</script>ok')))
        self.assertTrue(self.problems(good.replace('<main>ok', '<main><script src="https://cdn.example.com/x.js"></script>ok')))
        self.assertTrue(self.problems(good.replace('style-src &#x27;self&#x27;', 'style-src &#x27;self&#x27; &#x27;unsafe-inline&#x27;')))
        self.assertTrue(self.problems(re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]*>', '', good)))

    def test_detects_private_files_and_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = check.OUT
            check.OUT = Path(tmp)
            try:
                (check.OUT/'backup.sql').write_text('x', encoding='utf-8')
                (check.OUT/'note.txt').write_text('token=ghp_'+'a'*36, encoding='utf-8')
                errors = []
                check.published_files(errors)
            finally:
                check.OUT = old
        self.assertTrue(any('backup.sql' in e for e in errors))
        self.assertTrue(any('GitHub 令牌' in e and 'aaaa' not in e for e in errors))

    def test_detects_drafts_in_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root, old_out = check.ROOT, check.OUT
            check.ROOT, check.OUT = Path(tmp), Path(tmp)/'_site'
            try:
                (check.ROOT/'articles.json').write_text(json.dumps([{'slug': 'half-done', 'draft': True}]), encoding='utf-8')
                (check.OUT/'articles'/'half-done').mkdir(parents=True)
                errors = []
                check.site_rules({}, errors)
            finally:
                check.ROOT, check.OUT = old_root, old_out
        self.assertTrue(errors and '草稿' in errors[0], errors)


if __name__ == '__main__':
    unittest.main(verbosity=2)
