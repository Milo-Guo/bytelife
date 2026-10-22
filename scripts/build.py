"""把 Markdown 文章构建成可直接部署到 GitHub Pages 的静态网站。"""
from datetime import datetime
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
from urllib.parse import quote
from xml.sax.saxutils import escape as xml_escape

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT/'_site'
BASE = '/bytelife/'
ORIGIN = 'https://milo-guo.github.io'
REPO = 'https://github.com/Milo-Guo/bytelife'
MD = MarkdownIt('commonmark', {'html': True, 'breaks': False}).enable('table').enable('strikethrough')


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain(html):
    parser = PlainText()
    parser.feed(html)
    return re.sub(r'\s+', ' ', ' '.join(parser.parts)).strip()


def public_url(slug):
    return f'{BASE}articles/{slug}/'


def convert_link(url):
    # Markdown 在仓库内仍能互相跳转，生成网页时再换成网页路径。
    match = re.match(r'(?:\.\./)?content/([^/#]+)\.md(.*)$', url)
    if match:
        return public_url(match[1])+match[2]
    match = re.match(r'(?:\.\./)?archive/([^/#]+)\.md(.*)$', url)
    if match:
        return f'{BASE}archive/{match[1]}/'+match[2]
    if url.startswith('../assets/'):
        return BASE+url[3:]
    return url


def render(raw):
    # 原论坛自定义的 name 锚点保留下来，避免旧的章节直达失效。
    raw = re.sub(r'<a\s+name="([^"]+)"\s*>\s*</a>', r'<a id="\1"></a>', raw)
    tokens = MD.parse(raw)
    toc = []
    used = set(re.findall(r'<a id="([^"]+)"', raw))

    def visit(items):
        for token in items:
            for attr in ('href', 'src'):
                if token.attrGet(attr):
                    token.attrSet(attr, convert_link(token.attrGet(attr)))
            if token.type == 'image':
                token.attrSet('loading', 'lazy')
                token.attrSet('decoding', 'async')
            if token.children:
                visit(token.children)

    visit(tokens)
    for index, token in enumerate(tokens):
        if token.type != 'heading_open':
            continue
        label = tokens[index+1].content
        slug = 'h-'+re.sub(r'[^\w\u4e00-\u9fff]+', '-', label.lower()).strip('-')
        original = slug
        counter = 2
        while slug in used:
            slug = f'{original}-{counter}'
            counter += 1
        used.add(slug)
        token.attrSet('id', slug)
        if token.tag in ('h2', 'h3'):
            toc.append((token.tag, slug, re.sub(r'[`*]', '', label)))
    return MD.renderer.render(tokens, MD.options, {}), toc


def shell(title, description, body, relative='', article=None, noindex=False):
    canonical = ORIGIN+BASE+relative
    structured = ''
    if article:
        structured = '<script type="application/ld+json">'+json.dumps({
            '@context': 'https://schema.org', '@type': 'TechArticle',
            'headline': article['title'], 'description': article['summary'],
            'datePublished': article['created'], 'dateModified': article['updated'],
            'author': {'@type': 'Person', 'name': 'Milo Guo', 'url': 'https://github.com/Milo-Guo'},
            'mainEntityOfPage': canonical,
        }, ensure_ascii=False).replace('</', '<\/')+'</script>'
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · ByteLife</title>
<meta name="description" content="{escape(description, quote=True)}">
<meta name="theme-color" content="#173ad8">
<meta name="color-scheme" content="light dark">
{'<meta name="robots" content="noindex,follow">' if noindex else ''}
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="{'article' if article else 'website'}">
<meta property="og:title" content="{escape(title, quote=True)}">
<meta property="og:description" content="{escape(description, quote=True)}">
<meta property="og:url" content="{canonical}">
<link rel="icon" href="{BASE}assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{BASE}assets/site.css">
<link rel="alternate" type="application/rss+xml" title="ByteLife 更新" href="{BASE}feed.xml">
{structured}
<script src="{BASE}assets/site.js" defer></script>
</head>
<body data-base="{BASE}">
<a class="skip" href="#main">跳到正文</a>
<header class="site-header"><div class="header-inner">
<a class="brand" href="{BASE}" aria-label="ByteLife 首页"><span class="brand-icon" aria-hidden="true">b/</span>ByteLife<span class="brand-dot" aria-hidden="true">.</span></a>
<nav aria-label="主导航"><a href="{BASE}#library">文章</a><a href="{REPO}/discussions">交流</a><a href="{REPO}">GitHub <span aria-hidden="true">↗</span></a><button class="theme-toggle" type="button" aria-label="切换明暗主题">◐</button></nav>
</div></header>
{body}
<footer class="site-footer"><a class="footer-brand" href="{BASE}">ByteLife.</a><p>学习经验、折腾记录，还有生活里的兴趣。</p><div><a href="{BASE}feed.xml">RSS</a><a href="{REPO}">文章源码</a><a href="{BASE}migration/">迁移记录</a><span>© 2026 Milo Guo</span></div></footer>
</body></html>'''


def toc_html(toc):
    return '<ol>'+''.join(f'<li class="toc-{level}"><a href="#{quote(anchor)}">{escape(label)}</a></li>' for level, anchor, label in toc)+'</ol>'


def article_page(meta, html, toc, archive=False):
    slug = meta['slug']
    src = ('archive/' if archive else 'content/')+slug+'.md'
    note = '<span class="label orange">历史存档</span>' if archive else f'<span class="label">{escape(meta["category"])}</span>'
    archived = f'<p class="archive-link">迁移前的 PCL 图文：<a href="{BASE}archive/minecraft-pcl-2026-10-05/">查看 2026-10-05 原文存档</a></p>' if slug == 'minecraft-mod' else ''
    return f'''<div class="reading-progress" aria-hidden="true"></div>
<div class="article-layout">
<aside class="toc-rail"><a class="back-link" href="{BASE}#library">← 全部文章</a><details class="toc" open><summary>这篇写了什么 <span>↕</span></summary><nav aria-label="章节目录">{toc_html(toc)}</nav></details><a class="rail-edit" href="{REPO}/edit/main/{src}">编辑这篇文章 ↗</a></aside>
<main id="main" class="article-main"><header class="article-header">{note}<h1>{escape(meta['title'])}</h1><p class="article-summary">{escape(meta['summary'])}</p><div class="article-meta"><span>Milo Guo</span><span>发布 {meta['created']}</span><span>更新 {meta['updated']}</span></div></header>
<article class="prose">{html}</article>{archived}
<div class="article-end"><span class="end-mark">/</span><h2>有问题，就把卡住的地方说清楚。</h2><p>带上环境、操作步骤和报错，一起把文章补好。</p><a class="text-link" href="{REPO}/discussions">去 GitHub 交流 ↗</a><a class="text-link" href="{REPO}/blob/main/{src}">查看 Markdown 原文 ↗</a></div></main></div>'''


def main():
    OUT.mkdir(exist_ok=True)
    shutil.copytree(ROOT/'assets', OUT/'assets', dirs_exist_ok=True)
    articles = json.loads((ROOT/'articles.json').read_text(encoding='utf-8'))
    articles.sort(key=lambda a: a['created'], reverse=True)
    search = []
    for meta in articles:
        raw = (ROOT/'content'/f'{meta["slug"]}.md').read_text(encoding='utf-8')
        html, toc = render(raw)
        directory = OUT/'articles'/meta['slug']
        directory.mkdir(parents=True, exist_ok=True)
        body = article_page(meta, html, toc)
        (directory/'index.html').write_text(shell(meta['title'], meta['summary'], body, f'articles/{meta["slug"]}/', meta), encoding='utf-8')
        search.append({**meta, 'url': public_url(meta['slug']), 'text': plain(html)})

    archive_meta = {
        'slug': 'minecraft-pcl-2026-10-05', 'title': '从 PCL 玩明白，到用 VS Code 写出第一个 Minecraft Java 模组（原文存档）',
        'summary': '保留原论坛的旧版 PCL 下载、安装操作和全部配图。在线安装步骤已有变化，请优先阅读当前修订版。',
        'category': '历史存档', 'created': '2026-10-05', 'updated': '2026-10-22',
    }
    html, toc = render((ROOT/'archive'/f'{archive_meta["slug"]}.md').read_text(encoding='utf-8'))
    directory = OUT/'archive'/archive_meta['slug']
    directory.mkdir(parents=True, exist_ok=True)
    (directory/'index.html').write_text(shell(archive_meta['title'], archive_meta['summary'], article_page(archive_meta, html, toc, True), f'archive/{archive_meta["slug"]}/', noindex=True), encoding='utf-8')

    rows = []
    for i, meta in enumerate(articles, 1):
        rows.append(f'''<li class="article-row" data-category="{escape(meta['category'])}"><span class="row-number">{i:02}</span><div class="row-content"><div class="row-meta"><span>{escape(meta['category'])}</span><time datetime="{meta['created']}">{meta['created']}</time></div><h3><a href="{public_url(meta['slug'])}">{escape(meta['title'])}</a></h3><p>{escape(meta['summary'])}</p></div><a class="row-arrow" aria-label="阅读：{escape(meta['title'], quote=True)}" href="{public_url(meta['slug'])}">↗</a></li>''')
    categories = list(dict.fromkeys(x['category'] for x in articles))
    buttons = '<button class="filter active" data-filter="全部" aria-pressed="true">全部 <span>'+str(len(articles))+'</span></button>'
    buttons += ''.join(f'<button class="filter" data-filter="{escape(cat)}" aria-pressed="false">{escape(cat)} <span>{sum(x["category"] == cat for x in articles)}</span></button>' for cat in categories)
    home = f'''<main id="main" class="home-main"><section class="hero"><div class="hero-copy"><p class="eyebrow"><span></span> MILO’S LEARNING NOTES</p><h1>折腾过的，<br><em>写下来。</em></h1><p class="hero-description">技术怎么学，问题怎么查，日子怎么过。<br>把走过的路写清楚，让后来的人少绕一点。</p></div><div class="hero-margin"><span class="margin-line"></span><p>从一个命令，<br>到自己的作品。</p><span class="mono">{len(articles):02} 篇记录 / 持续补充</span></div></section>
<a class="update-strip" href="{public_url('minecraft-mod')}#mc-section-09"><span class="update-tag">10.22 更新</span><span>PCL 下载变化之后，已有游戏、整合包和全新安装分别怎么办</span><span aria-hidden="true">→</span></a>
<section id="library" class="library"><div class="library-heading"><div><p class="eyebrow">THE NOTEBOOK</p><h2>文章</h2></div><label class="search-box"><span aria-hidden="true">⌕</span><input id="search" type="search" placeholder="搜索文章、命令、报错…" aria-label="搜索全文" autocomplete="off"><kbd>/</kbd></label></div><div class="filter-bar" role="group" aria-label="按主题筛选">{buttons}</div><p id="result-status" class="result-status" aria-live="polite"></p><ol id="article-list" class="article-list">{''.join(rows)}</ol><p id="empty-state" class="empty-state" hidden>没有找到。试试换个词，或者切回“全部”。</p></section>
<section class="about-note"><span class="note-symbol" aria-hidden="true">↳</span><div><h2>这里还会慢慢长大。</h2><p>先写学技术时真正卡住的地方。以后也写做菜、食谱和别的爱好。写过的内容会继续修订，原文和修改记录都留着。</p><a href="{REPO}/discussions">有想聊的，来交流 ↗</a></div></section></main>'''
    (OUT/'index.html').write_text(shell('把走过的路写清楚', 'ByteLife：Milo Guo 的学习经验与生活记录。Git 入门、Minecraft Java 模组开发和 Windows 排障，步骤、文件位置和原因一起讲。', home), encoding='utf-8')
    (OUT/'search-index.json').write_text(json.dumps(search, ensure_ascii=False), encoding='utf-8')

    migration = (ROOT/'MIGRATION.md').read_text(encoding='utf-8')
    html, _ = render(migration)
    (OUT/'migration').mkdir(exist_ok=True)
    (OUT/'migration'/'index.html').write_text(shell('从论坛迁到这里', 'ByteLife 公开文章、配图和历史版本的迁移记录。', f'<main id="main" class="single-page"><a href="{BASE}" class="back-link">← 回到首页</a><article class="prose">{html}</article></main>', 'migration/'), encoding='utf-8')
    (OUT/'404.html').write_text(shell('这一页没找到', '返回 ByteLife 文章目录。', f'<main id="main" class="single-page"><h1>这一页没找到。</h1><p>文章可能换过地址。<a href="{BASE}">回首页查找</a>。</p></main>', '404.html', noindex=True), encoding='utf-8')
    links = [ORIGIN+BASE] + [ORIGIN+public_url(a['slug']) for a in articles]
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{url}</loc><lastmod>2026-10-22</lastmod></url>' for url in links)+'</urlset>'
    (OUT/'sitemap.xml').write_text(sitemap, encoding='utf-8')
    (OUT/'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {ORIGIN}{BASE}sitemap.xml\n', encoding='utf-8')
    rss = '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>ByteLife</title><link>'+ORIGIN+BASE+'</link><description>Milo 的学习与生活记录</description>'
    for a in articles:
        url = ORIGIN+public_url(a['slug'])
        rss += '<item><title>'+xml_escape(a['title'])+'</title><link>'+url+'</link><guid>'+url+'</guid><description>'+xml_escape(a['summary'])+'</description></item>'
    (OUT/'feed.xml').write_text(rss+'</channel></rss>', encoding='utf-8')
    (OUT/'.nojekyll').touch()
    print(f'构建完成：{len(articles)} 篇文章、1 篇历史存档、全文索引与站点地图 → {OUT}')


if __name__ == '__main__':
    main()
