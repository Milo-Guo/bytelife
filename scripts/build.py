"""把 Markdown 文章构建成可直接部署到 GitHub Pages 的静态网站。

内容只来自仓库里的 content/、archive/、MIGRATION.md 和 articles.json。
构建会校验文章元数据，过滤正文里的原生 HTML，并且只把网页需要的文件写进 _site/。
"""
import argparse
from base64 import b64encode
from datetime import date, datetime, timedelta, timezone
from email.utils import format_datetime
from hashlib import sha256
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
from urllib.parse import quote, unquote
from xml.sax.saxutils import escape as xml_escape

from markdown_it import MarkdownIt
from markdown_it.token import Token
from site_analytics import load_website_id, tracking_csp, tracking_markup

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT/'content'
ASSETS = ROOT/'assets'
OUT = ROOT/'_site'
BASE = '/bytelife/'
ORIGIN = 'https://milo-guo.github.io'
REPO = 'https://github.com/Milo-Guo/bytelife'
MD = MarkdownIt('commonmark', {'html': True, 'breaks': False}).enable('table').enable('strikethrough')
ALL = '全部'

# 首屏前同步执行：标记 JS 可用，并套用读者手动选过的主题，避免刷新时先闪一下浅色。
# 改动这段文字后，CSP 里的哈希会自动重新计算。
THEME_SCRIPT = ("(function(){var d=document.documentElement;d.classList.add('js');"
                "try{var t=localStorage.getItem('bytelife-theme');if(t==='light'||t==='dark')d.dataset.theme=t}catch(e){}})();")
THEME_HASH = 'sha256-'+b64encode(sha256(THEME_SCRIPT.encode()).digest()).decode()
# GitHub Pages 不能自定义响应头，只能用 meta 声明。meta 版 CSP 不支持 frame-ancestors 和违规上报。
CSP = '; '.join([
    "default-src 'none'",
    f"script-src 'self' '{THEME_HASH}'",
    "style-src 'self'",
    "img-src 'self'",
    "connect-src 'self'",
    "base-uri 'none'",
    "form-action 'none'",
    "require-trusted-types-for 'script'",
    "trusted-types 'none'",
])
# 写作页要向 GitHub 接口读写文章，只在这一页放开 api.github.com，并只允许名为 bytelife-preview 的
# Trusted Types 策略把预览 HTML 写进页面。
EDITOR_CSP = (CSP.replace("connect-src 'self'", "connect-src 'self' https://api.github.com")
              .replace("trusted-types 'none'", "trusted-types bytelife-preview"))
THEME_COLORS = {'light': '#f7f6f3', 'dark': '#131416'}
ASSET_URLS = {name: BASE+'assets/'+name for name in ('site.css', 'site.js', 'home.js', 'editor.css', 'editor.js')}
VENDOR_MARKDOWN_IT = 'vendor/markdown-it-14.3.3.min.js'
# 写作页预览用的 markdown-it 前端版，取自 npm 官方包，文件哈希写在这里，check.py 会核对。
VENDOR_HASHES = {VENDOR_MARKDOWN_IT: '494ba53db1aac9f676317dda7062bd9545b5f0bbe3f12b0ab1ab4f813825cfb0'}


class BuildError(SystemExit):
    pass


# ---------- 原生 HTML 白名单 ----------

# 文章里允许少量原生 HTML。名单外的标签去掉、文字保留；脚本类标签连同内容一起丢弃。
ALLOWED_TAGS = {
    'a': {'href', 'title', 'id', 'name'}, 'abbr': {'title'}, 'b': set(), 'br': set(), 'code': set(),
    'del': set(), 'details': {'open'}, 'div': {'id'}, 'em': set(), 'i': set(),
    'img': {'src', 'alt', 'title', 'width', 'height'}, 'ins': set(), 'kbd': set(), 'mark': set(),
    'p': {'id'}, 'small': set(), 'span': {'id'}, 'strong': set(), 'sub': set(), 'summary': set(),
    'sup': set(), 'u': set(),
}
DROP_WITH_CONTENT = {'script', 'style', 'iframe', 'frame', 'frameset', 'object', 'embed', 'applet', 'template',
                     'noscript', 'noembed', 'noframes', 'textarea', 'title', 'xmp', 'plaintext', 'svg', 'math', 'select'}
VOID_TAGS = {'br', 'img', 'hr', 'wbr', 'input', 'meta', 'link', 'base', 'source', 'track', 'area', 'col', 'param'}
SAFE_ID = re.compile(r'[A-Za-z\u4e00-\u9fff][\w\u4e00-\u9fff:.-]{0,100}\Z')
SAFE_SCHEMES = {'http', 'https', 'mailto'}


def safe_url(url):
    """危险协议返回 None；站内路径、锚点和 http(s)/mailto 保留。HTML 转义在输出时另做。"""
    # 浏览器解析网址时会去掉首尾控制字符和中间的换行、制表符，这里按同样规则判断协议。
    cleaned = re.sub(r'[\t\n\r]', '', re.sub(r'^[\x00-\x20]+|[\x00-\x20]+$', '', url))
    scheme = re.match(r'([A-Za-z][A-Za-z0-9+.-]*):', cleaned)
    if scheme and scheme[1].lower() not in SAFE_SCHEMES:
        return None
    return cleaned


class Sanitizer(HTMLParser):
    def __init__(self, used_ids):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.used_ids = used_ids
        self.skip_tag = None
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if self.skip_depth:
            self.skip_depth += tag == self.skip_tag
            return
        if tag in DROP_WITH_CONTENT:
            if tag not in VOID_TAGS:
                self.skip_tag, self.skip_depth = tag, 1
            return
        if tag not in ALLOWED_TAGS:
            return
        kept = {}
        for name, value in attrs:
            name = name.lower()
            if name not in ALLOWED_TAGS[tag] or name in kept:
                continue
            if value is None:
                if name == 'open':
                    kept[name] = ''
                continue
            if name in ('href', 'src'):
                value = safe_url(convert_link(value))
                if value is None:
                    continue
            elif name in ('id', 'name'):
                # 旧论坛的 <a name> 锚点统一换成 id，原来的章节直达地址继续有效。
                name = 'id'
                if 'id' in kept or not SAFE_ID.match(value) or value in self.used_ids:
                    continue
                self.used_ids.add(value)
            elif name in ('width', 'height') and not value.isdigit():
                continue
            kept[name] = value
        self.out.append('<'+tag+''.join(f' {name}="{escape(value)}"' for name, value in kept.items())+'>')

    def handle_startendtag(self, tag, attrs):
        # HTML 里非空元素写成 <span/> 也不会自闭合，按普通开始标签处理，和浏览器一致。
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if self.skip_depth:
            self.skip_depth -= tag == self.skip_tag
            return
        if tag in ALLOWED_TAGS and tag not in VOID_TAGS:
            self.out.append(f'</{tag}>')

    def handle_data(self, data):
        if not self.skip_depth:
            self.out.append(escape(data, quote=False))


def sanitize_html(fragment, used_ids=None):
    parser = Sanitizer(set() if used_ids is None else used_ids)
    parser.feed(fragment)
    parser.close()
    return ''.join(parser.out)


# ---------- 正文渲染 ----------

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


def image_size(path):
    """读取 PNG、JPEG、WebP、GIF、SVG 的尺寸。图片带上宽高，懒加载时页面不会跳。"""
    data = path.read_bytes()
    if path.suffix.lower() == '.svg':
        root = re.search(r'<svg\b[^>]*>', data[:4096].decode('utf-8', 'ignore'))
        attrs = dict(re.findall(r'\b(width|height|viewBox)\s*=\s*"([^"]*)"', root[0])) if root else {}
        size = [re.fullmatch(r'(\d+(?:\.\d+)?)(?:px)?', attrs.get(key, '').strip()) for key in ('width', 'height')]
        if all(size):
            return round(float(size[0][1])), round(float(size[1][1]))
        box = attrs.get('viewBox', '').replace(',', ' ').split()
        return (round(float(box[2])), round(float(box[3]))) if len(box) == 4 else None
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return struct.unpack('>II', data[16:24])
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return struct.unpack('<HH', data[6:10])
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        kind = data[12:16]
        if kind == b'VP8 ':
            width, height = struct.unpack('<HH', data[26:30])
            return width & 0x3fff, height & 0x3fff
        if kind == b'VP8L':
            b = data[21:25]
            return 1+(b[0] | (b[1] & 0x3f) << 8), 1+((b[1] >> 6) | b[2] << 2 | (b[3] & 0x0f) << 10)
        if kind == b'VP8X':
            return 1+int.from_bytes(data[24:27], 'little'), 1+int.from_bytes(data[27:30], 'little')
    if data[:2] == b'\xff\xd8':
        i = 2
        while i+9 < len(data):
            if data[i] != 0xff:
                i += 1
                continue
            marker = data[i+1]
            if marker in (0xd8, 0x01, 0xff) or 0xd0 <= marker <= 0xd7:
                i += 1 if marker == 0xff else 2
                continue
            if marker in (0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf):
                height, width = struct.unpack('>HH', data[i+5:i+9])
                return width, height
            i += 2+struct.unpack('>H', data[i+2:i+4])[0]
    return None


def local_asset(url):
    """站内图片地址对应的仓库文件；不在 assets/ 里的地址返回 None。"""
    if not url.startswith(BASE+'assets/'):
        return None
    path = (ASSETS/unquote(url[len(BASE+'assets/'):].split('?')[0].split('#')[0])).resolve()
    return path if path.is_relative_to(ASSETS.resolve()) and path.is_file() else None


def clean_tokens(tokens, used_ids):
    for token in tokens:
        if token.type in ('html_block', 'html_inline'):
            token.content = sanitize_html(token.content, used_ids)
        for attr in ('href', 'src'):
            value = token.attrGet(attr)
            if value is None:
                continue
            value = safe_url(convert_link(value))
            if value is None:
                token.attrs.pop(attr, None)
            else:
                token.attrSet(attr, value)
        if token.type == 'image':
            token.attrSet('loading', 'lazy')
            token.attrSet('decoding', 'async')
            path = local_asset(token.attrGet('src') or '')
            size = path and image_size(path)
            if size:
                token.attrSet('width', str(size[0]))
                token.attrSet('height', str(size[1]))
        if token.type in ('th_open', 'td_open'):
            # 表格对齐原本是行内 style，会被 CSP 拦下，换成样式类。
            align = re.search(r'text-align:(left|center|right)', token.attrGet('style') or '')
            token.attrs.pop('style', None)
            if align:
                token.attrSet('class', f'align-{align[1]}')
        if token.children:
            clean_tokens(token.children, used_ids)


ANCHOR_ONLY = re.compile(r'\s*(?:<div>\s*)?<a id="([^"]+)"></a>\s*(?:</div>\s*)?\Z')


def move_anchors_into_headings(tokens):
    """旧锚点原来是标题前的空段落。挪进标题里，跳转后标题正好停在顶部，也不多出空行。"""
    for i, token in enumerate(tokens):
        anchor, after = None, i+1
        if token.type == 'html_block':
            match = ANCHOR_ONLY.match(token.content)
            anchor = match and match[1]
        elif token.type == 'paragraph_open' and i+2 < len(tokens):
            children = tokens[i+1].children or []
            if all(c.type == 'html_inline' or not c.content.strip() for c in children):
                match = ANCHOR_ONLY.match(''.join(c.content for c in children if c.type == 'html_inline'))
                anchor, after = match and match[1], i+3
        if not anchor or after >= len(tokens) or tokens[after].type != 'heading_open':
            continue
        if token.type == 'html_block':
            token.content = ''
        else:
            token.hidden = tokens[i+2].hidden = True
            tokens[i+1].children = []
        span = Token('html_inline', '', 0)
        span.content = f'<span class="anchor" id="{escape(anchor)}"></span>'
        tokens[after+1].children.insert(0, span)


def html_token(content, inline=False):
    token = Token('html_inline' if inline else 'html_block', '', 0)
    token.content = content
    return token


def only_child(tokens, i, kind):
    if tokens[i].type != 'paragraph_open' or i+2 >= len(tokens):
        return None
    children = [c for c in tokens[i+1].children or [] if c.type not in ('text', 'softbreak') or c.content.strip()]
    if kind == 'image':
        return children[0] if len(children) == 1 and children[0].type == 'image' else None
    opens = [c for c in children if c.type == 'em_open']
    return children if children and children[0].type == 'em_open' and children[-1].type == 'em_close' and len(opens) == 1 else None


CALLOUTS = {'NOTE': '说明', 'TIP': '提示', 'IMPORTANT': '重要', 'WARNING': '注意', 'CAUTION': '警告'}


def decorate(tokens):
    """统一图片、提示框和表格的结构；样式只在 site.css 里定义一次。"""
    result, i = [], 0
    while i < len(tokens):
        token = tokens[i]
        image = only_child(tokens, i, 'image')
        if image:
            # 图片和紧跟着的斜体说明合成一个 figure，图片外包一层原图链接，没有脚本也能点开看。
            src = image.attrGet('src') or ''
            inline = tokens[i+1]
            inline.children = [html_token(f'<a class="figure-link" href="{escape(src)}">', True), image,
                               html_token(f'<span class="figure-zoom" aria-hidden="true">{icon("expand")}</span>'
                                          '<span class="visually-hidden">（点击放大）</span></a>', True)]
            result += [html_token('<figure class="figure">'), inline]
            i += 3
            caption = i < len(tokens) and only_child(tokens, i, 'caption')
            if caption:
                caption[0].hidden = caption[-1].hidden = True
                result += [html_token('<figcaption>'), tokens[i+1], html_token('</figcaption>')]
                i += 3
            result.append(html_token('</figure>\n'))
            continue
        if token.type == 'blockquote_open' and i+2 < len(tokens) and tokens[i+2].type == 'inline':
            children = tokens[i+2].children or []
            match = re.match(r'\[!(\w+)\]\s*', children[0].content) if children and children[0].type == 'text' else None
            if match and match[1].upper() in CALLOUTS:
                kind = match[1].upper()
                # 兼容 GitHub 的提示框写法：> [!TIP]。GitHub 预览和网站显示一致。
                children[0].content = children[0].content[match.end():]
                if not children[0].content and len(children) > 1 and children[1].type == 'softbreak':
                    del children[:2]
                token.attrSet('class', f'callout callout-{kind.lower()}')
                result += [token, html_token(f'<p class="callout-title">{CALLOUTS[kind]}</p>\n')]
                i += 1
                continue
        if token.type == 'table_open':
            # 两列表格在手机上改成上下排列，命令和解释不用横向来回滑。
            columns = 0
            for cell in tokens[i+1:]:
                columns += cell.type in ('th_open', 'td_open')
                if cell.type == 'tr_close':
                    break
            result.append(html_token(f'<div class="table-wrap{" is-pair" if columns == 2 else ""}">'))
        result.append(token)
        if token.type == 'table_close':
            result.append(html_token('</div>\n'))
        i += 1
    return result


LANGUAGES = {
    'bash': 'Bash', 'sh': 'Shell', 'shell': 'Shell', 'powershell': 'PowerShell', 'ps1': 'PowerShell',
    'cmd': 'CMD', 'bat': 'Batch', 'java': 'Java', 'json': 'JSON', 'markdown': 'Markdown', 'md': 'Markdown',
    'gitignore': '.gitignore', 'text': '文本', 'txt': '文本', 'python': 'Python', 'py': 'Python',
    'javascript': 'JavaScript', 'js': 'JavaScript', 'html': 'HTML', 'css': 'CSS', 'yaml': 'YAML',
    'yml': 'YAML', 'toml': 'TOML', 'xml': 'XML', 'gradle': 'Gradle', 'kotlin': 'Kotlin',
}


def render_code(self, tokens, idx, options, env):
    # 代码块统一带标题栏：左边语言，右边留给复制按钮。按钮不放进 <pre>，复制内容不会混进按钮文字。
    token = tokens[idx]
    lang = token.info.strip().split(maxsplit=1)[0] if token.info.strip() else ''
    label = LANGUAGES.get(lang.lower(), lang or '代码')
    css = f' class="language-{escape(lang.lower())}"' if re.fullmatch(r'[\w+#.-]{1,30}', lang) else ''
    return (f'<div class="code-block"><div class="code-head"><span class="code-lang">{escape(label)}</span></div>'
            f'<pre><code{css}>{escape(token.content)}</code></pre></div>\n')


MD.add_render_rule('fence', render_code)
MD.add_render_rule('code_block', render_code)


def render(raw):
    """返回 (正文 HTML, 二三级标题目录)。"""
    tokens = MD.parse(raw)
    used = set()
    clean_tokens(tokens, used)
    move_anchors_into_headings(tokens)
    toc = []
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
    return MD.renderer.render(decorate(tokens), MD.options, {}), toc


RECIPE_SECTIONS = {'用料': 'ingredients', '食材': 'ingredients', '材料': 'ingredients', '配料': 'ingredients',
                   '做法': 'steps', '步骤': 'steps'}


def recipe_parts(raw):
    """食谱：取出“用料”“做法”两节（二级标题）下列表的每一项，写进结构化数据。"""
    parts, section, depth, item = {'ingredients': [], 'steps': []}, None, 0, None
    tokens = MD.parse(raw)
    for i, token in enumerate(tokens):
        if token.type == 'heading_open' and token.tag == 'h2':
            section = RECIPE_SECTIONS.get(tokens[i+1].content.strip())
        elif token.type in ('bullet_list_open', 'ordered_list_open'):
            depth += 1
        elif token.type in ('bullet_list_close', 'ordered_list_close'):
            depth -= 1
        elif section and depth == 1 and token.type == 'list_item_open':
            item = []
        elif section and depth == 1 and token.type == 'list_item_close' and item is not None:
            text = re.sub(r'\s+', ' ', ' '.join(item)).strip()
            if text:
                parts[section].append(text)
            item = None
        elif item is not None and depth == 1 and token.type == 'inline':
            item.append(''.join(c.content if c.type in ('text', 'code_inline') else ' ' if c.type == 'softbreak' else ''
                                for c in token.children or []))
    return parts


def person(author):
    data = {'@type': 'Person', 'name': author['name'], 'url': ORIGIN+author_url(author['id'])}
    same = ([f'https://github.com/{author["github"]}'] if author.get('github') else []) + ([author['url']] if author.get('url') else [])
    if same:
        data['sameAs'] = same
    return data


def structured_data(meta, canonical):
    kind = TYPES[meta.get('type', 'tutorial')][1]
    data = {
        '@context': 'https://schema.org', '@type': kind,
        'headline': meta['title'], 'description': meta['summary'],
        'datePublished': meta['created'], 'dateModified': meta['updated'],
        'mainEntityOfPage': canonical,
    }
    people = [person(author) for author in meta.get('author_list') or []]
    if people:
        data['author'] = people[0] if len(people) == 1 else people
    if meta.get('image'):
        data['image'] = [meta['image']]
    if kind == 'Recipe':
        recipe, parts = meta.get('recipe') or {}, meta.get('recipe_parts') or {}
        data.update({'name': meta['title'], 'recipeCategory': meta['category']})
        if recipe.get('servings'):
            data['recipeYield'] = recipe['servings']
        if recipe.get('minutes'):
            data['totalTime'] = f'PT{recipe["minutes"]}M'
        if parts.get('ingredients'):
            data['recipeIngredient'] = parts['ingredients']
        if parts.get('steps'):
            data['recipeInstructions'] = [{'@type': 'HowToStep', 'text': step} for step in parts['steps']]
    return data


HEADING = re.compile(r'<(h[23]) id="([^"]+)">(.*?)</\1>', re.S)


def sections(html):
    """按二三级标题切开正文，搜索结果可以直接跳到命中的章节。"""
    result, start, current = [], 0, ('', '')
    for match in HEADING.finditer(html):
        text = plain(html[start:match.start()])
        if text or current[0]:
            result.append([current[0], current[1], text])
        current, start = (match[2], plain(match[3])), match.end()
    text = plain(html[start:])
    if text or current[0]:
        result.append([current[0], current[1], text])
    return result


# ---------- 文章元数据 ----------

SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
REQUIRED = ('slug', 'title', 'category', 'summary', 'created', 'updated')
# 分类管首页筛选（编程、做菜……），类型管文章体裁：决定结构化数据的写法和页头显示的信息。
TYPES = {'tutorial': ('教程', 'TechArticle'), 'recipe': ('食谱', 'Recipe'), 'post': ('随笔', 'BlogPosting')}
TYPE_HINT = '、'.join(f'{key}（{label}）' for key, (label, _) in TYPES.items())


def iso_date(value, where):
    try:
        if len(value) == 10 and date.fromisoformat(value):
            return value
    except (TypeError, ValueError):
        pass
    raise BuildError(f'articles.json：{where} 的日期要写成 2026-10-22 这样的格式')


GITHUB_USER = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})\Z')


def load_authors(data):
    """检查 authors.json：每位作者要有 id（作者页网址用，小写字母、数字、连字符）和名字；
    可选 GitHub 用户名、一句话简介和个人主页（只接受 https）。第一位作者是站长，旧条目和存档默认署名站长。"""
    if not isinstance(data, list) or not data:
        raise BuildError('authors.json：应该是一个非空数组')
    authors, githubs = {}, set()
    for number, author in enumerate(data, 1):
        where = f'authors.json 第 {number} 项'
        if not isinstance(author, dict):
            raise BuildError(f'{where} 不是对象')
        if set(author) - {'id', 'name', 'github', 'bio', 'url'}:
            raise BuildError(f'{where} 只能有 id、name、github、bio、url 这几项')
        aid = author.get('id')
        if not isinstance(aid, str) or not SLUG.match(aid) or len(aid) > 40:
            raise BuildError(f'{where} 的 id 只能用小写字母、数字和连字符')
        if aid in authors:
            raise BuildError(f'authors.json：作者 id「{aid}」重复')
        if not isinstance(author.get('name'), str) or not author['name'].strip():
            raise BuildError(f'{where} 缺少 name')
        github = author.get('github')
        if github is not None and (not isinstance(github, str) or not GITHUB_USER.match(github) or github.lower() in githubs):
            raise BuildError(f'{where} 的 github 要写 GitHub 用户名，且不能和别人重复')
        if not isinstance(author.get('bio', ''), str):
            raise BuildError(f'{where} 的 bio 要写成一句话')
        url = author.get('url')
        if url is not None and (not isinstance(url, str) or not url.startswith('https://') or safe_url(url) != url):
            raise BuildError(f'{where} 的 url 只接受 https:// 开头的网址')
        githubs.add((github or '').lower())
        authors[aid] = author
    return authors


def read_authors(root=ROOT):
    return load_authors(json.loads((root/'authors.json').read_text(encoding='utf-8')))


def author_ids(meta):
    value = meta.get('author')
    return [value] if isinstance(value, str) else list(value) if isinstance(value, list) else []


def author_url(aid):
    return f'{BASE}authors/{aid}/'


def validate_articles(data, content_dir=CONTENT, authors=None):
    """检查 articles.json。slug 只能是小写字母、数字和连字符，对应的 Markdown 必须在 content/ 里，作者必须在 authors.json 里。"""
    authors = read_authors() if authors is None else authors
    if not isinstance(data, list) or not data:
        raise BuildError('articles.json：应该是一个非空数组')
    seen, articles = set(), []
    root = content_dir.resolve()
    for number, meta in enumerate(data, 1):
        where = f'第 {number} 项'
        if not isinstance(meta, dict):
            raise BuildError(f'articles.json：{where} 不是对象')
        for key in REQUIRED:
            if not isinstance(meta.get(key), str) or not meta[key].strip():
                raise BuildError(f'articles.json：{where} 缺少 {key}')
        slug = meta['slug']
        if not SLUG.match(slug) or len(slug) > 80:
            raise BuildError(f'articles.json：{where} 的 slug「{slug}」只能用小写字母、数字和连字符')
        if slug in seen:
            raise BuildError(f'articles.json：slug「{slug}」重复')
        if meta['category'].strip() == ALL:
            raise BuildError(f'articles.json：{where} 的分类不能叫「{ALL}」')
        path = (content_dir/f'{slug}.md').resolve()
        if path.parent != root or not path.is_file():
            raise BuildError(f'articles.json：找不到 content/{slug}.md')
        iso_date(meta['created'], where)
        iso_date(meta['updated'], where)
        if meta['updated'] < meta['created']:
            raise BuildError(f'articles.json：{where} 的更新日期早于发布日期')
        note = meta.get('note')
        if note is not None:
            if not isinstance(note, dict) or not all(isinstance(note.get(k), str) and note[k].strip() for k in ('date', 'text', 'anchor')):
                raise BuildError(f'articles.json：{where} 的 note 需要 date、text、anchor 三项')
            iso_date(note['date'], where+' note')
            if not SAFE_ID.match(note['anchor']):
                raise BuildError(f'articles.json：{where} 的 note.anchor 只能是章节锚点名')
        if meta.get('type') not in TYPES:
            raise BuildError(f'articles.json：{where} 的 type 要写成 {TYPE_HINT} 之一')
        if not isinstance(meta.get('draft', False), bool):
            raise BuildError(f'articles.json：{where} 的 draft 只能是 true 或 false')
        ids = author_ids(meta)
        if (not isinstance(meta.get('author'), (str, list)) or not ids or len(set(ids)) != len(ids)
                or not all(isinstance(i, str) and i in authors for i in ids)):
            raise BuildError(f'articles.json：{where} 的 author 要写 authors.json 里的作者 id，例如 "{next(iter(authors))}"，'
                             f'几个人合写用 ["a", "b"]')
        recipe = meta.get('recipe')
        if recipe is not None:
            minutes = recipe.get('minutes', 1) if isinstance(recipe, dict) else None
            if (meta['type'] != 'recipe' or not isinstance(recipe, dict) or set(recipe) - {'servings', 'minutes'}
                    or not isinstance(recipe.get('servings', '份量'), str) or not recipe.get('servings', '份量').strip()
                    or not isinstance(minutes, int) or isinstance(minutes, bool) or not 0 < minutes <= 10000):
                raise BuildError(f'articles.json：{where} 的 recipe 只用于食谱，写成 {{"servings": "2 人份", "minutes": 30}}')
        seen.add(slug)
        articles.append({**meta, 'path': path, 'author_list': [authors[i] for i in ids]})
    return articles


# ---------- 页面模板 ----------

ICONS = {
    'search': '<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/>',
    'sun': '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M4.6 4.6 6 6M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4 6 18M18 6l1.4-1.4"/>',
    'moon': '<path d="M19.5 14.6A7.5 7.5 0 0 1 9.4 4.5a7.5 7.5 0 1 0 10.1 10.1Z"/>',
    'arrow-right': '<path d="M5 12h14M13 6l6 6-6 6"/>',
    'arrow-left': '<path d="M19 12H5M11 6l-6 6 6 6"/>',
    'external': '<path d="M8 16 16 8M9.5 8H16v6.5"/>',
    'chevron': '<path d="m7 10 5 5 5-5"/>',
    'copy': '<rect x="8.5" y="8.5" width="11" height="11" rx="2"/><path d="M15.5 8.5V6A1.5 1.5 0 0 0 14 4.5H6A1.5 1.5 0 0 0 4.5 6v8A1.5 1.5 0 0 0 6 15.5h2.5"/>',
    'check': '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    'list': '<path d="M4 6.5h16M4 12h16M4 17.5h10"/>',
    'close': '<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>',
    'expand': '<path d="M14 4.5h5.5V10M10 19.5H4.5V14M19.5 4.5 14 10M4.5 19.5 10 14"/>',
    'bookmark': '<path d="M6 4.5h12v16l-6-4-6 4Z"/>',
    'clock': '<circle cx="12" cy="12" r="8"/><path d="M12 7v5l3 2"/>',
    'code': '<path d="m8 6-6 6 6 6M16 6l6 6-6 6M14 3l-4 18"/>',
}
SPRITE = ('<svg xmlns="http://www.w3.org/2000/svg" class="sprite" aria-hidden="true">'
          + ''.join(f'<symbol id="i-{name}" viewBox="0 0 24 24">{path}</symbol>' for name, path in ICONS.items())+'</svg>')


def icon(name):
    return f'<svg class="icon icon-{name}" aria-hidden="true" focusable="false"><use href="#i-{name}"></use></svg>'


def shell(title, description, body, relative='', article=None, noindex=False, page='page', search_link=True,
          csp=CSP, styles=(), scripts=()):
    canonical = ORIGIN+BASE+relative
    # 写作页可能连接 GitHub 令牌，不能加载第三方统计；草稿和 404 也不累计阅读量。
    website_id = SITE_STATE.get('analytics_website_id', '')
    track = (website_id and relative not in ('write/', '404.html')
             and 'editor-page' not in page.split() and not (article and article.get('draft')))
    analytics = tracking_markup(website_id) if track else ''
    if track:
        csp = tracking_csp(csp)
    analytics_notice = '<a href="https://umami.is/privacy">访问统计：Umami</a>' if track else ''
    structured = ''
    if article:
        # JSON 里的 < 写成 \u003c，标题里出现 </script> 也不会提前结束这段数据。
        structured = ('<script type="application/ld+json">'
                      + json.dumps(structured_data(article, canonical), ensure_ascii=False).replace('<', '\\u003c')+'</script>')
    nav = f'<a class="nav-link" href="{BASE}#search">{icon("search")}<span>搜索</span></a>' if search_link else ''
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="{escape(csp)}">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script>{THEME_SCRIPT}</script>
<title>{escape(title)} · ByteLife</title>
<meta name="description" content="{escape(description)}">
{'<meta name="robots" content="noindex,follow">' if noindex else ''}
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="{THEME_COLORS['light']}" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="{THEME_COLORS['dark']}" media="(prefers-color-scheme: dark)">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="{'article' if article else 'website'}">
<meta property="og:site_name" content="ByteLife">
<meta property="og:title" content="{escape(title)}">
<meta property="og:description" content="{escape(description)}">
<meta property="og:url" content="{canonical}">
<link rel="icon" href="{BASE}assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{ASSET_URLS['site.css']}">
{''.join(f'<link rel="stylesheet" href="{ASSET_URLS[name]}">' for name in styles)}
<link rel="alternate" type="application/rss+xml" title="ByteLife 更新" href="{BASE}feed.xml">
{structured}
<script src="{ASSET_URLS['site.js']}" defer></script>
{''.join(f'<script src="{ASSET_URLS[name]}" defer></script>' for name in scripts)}
{analytics}
</head>
<body class="{page}" data-base="{BASE}">
{SPRITE}
<a class="skip-link" href="#main">跳到正文</a>
<header class="site-header"><div class="header-inner">
<a class="brand" href="{BASE}"><span class="brand-mark" aria-hidden="true">b/</span><span>ByteLife</span></a>
<nav class="site-nav" aria-label="主导航">{nav}<a class="nav-link" href="{REPO}/discussions">交流</a><button class="icon-button theme-toggle" type="button" aria-pressed="false" aria-label="深色模式" title="切换明暗主题">{icon('moon')}{icon('sun')}</button></nav>
</div></header>
{body}
<footer class="site-footer"><div class="footer-inner">
<p>ByteLife · Milo Guo 的学习与生活记录</p>
<nav class="footer-links" aria-label="站点信息">{f'<a href="{BASE}authors/">作者</a>' if SITE_STATE['multi_author'] else ''}<a href="{BASE}feed.xml">RSS</a><a href="{REPO}">源码</a><a href="{BASE}migration/">迁移记录</a>{analytics_notice}</nav>
<p class="footer-meta"><span>© 2026 Milo Guo</span><button class="text-button theme-reset" type="button" hidden>恢复跟随系统主题</button></p>
</div></footer>
</body></html>'''


def toc_html(toc):
    html, group_open, sub_open = ['<ol class="toc-list">'], False, False
    for level, anchor, label in toc:
        link = f'<a href="#{quote(anchor)}">{escape(label)}</a>'
        if level == 'h2' or not group_open:
            if sub_open:
                html.append('</ol>')
                sub_open = False
            if group_open:
                html.append('</li>')
            group_open = True
            if level == 'h2':
                html.append(f'<li class="toc-h2">{link}')
                continue
            html.append('<li class="toc-h2 toc-loose">')
        if not sub_open:
            html.append('<ol>')
            sub_open = True
        html.append(f'<li class="toc-h3">{link}</li>')
    html.append(('</ol>' if sub_open else '')+('</li>' if group_open else '')+'</ol>')
    return ''.join(html)


def recipe_facts(meta):
    """食谱的份量和用时，显示在页头和首页列表里。"""
    recipe = (meta.get('recipe') or {}) if meta.get('type') == 'recipe' else {}
    facts = []
    if recipe.get('servings'):
        facts.append(escape(recipe['servings']))
    if recipe.get('minutes'):
        facts.append(f'约 {recipe["minutes"]} 分钟')
    return facts


DRAFT_BADGE = '<span class="badge badge-draft">草稿 · 未发布</span>'
# 有两位以上作者发表过文章时，首页列表显示作者，页脚出现“作者”入口。
SITE_STATE = {'multi_author': False, 'analytics_website_id': ''}


def byline(meta, link=True):
    names = []
    for author in meta.get('author_list') or []:
        name = escape(author['name'])
        names.append(f'<a class="author-link" href="{author_url(author["id"])}">{name}</a>' if link else name)
    return '、'.join(names)


def revisions(relative):
    """文件的修改记录：从 Git 历史取每次提交的日期、说明和提交号。没有 Git 或只有浅克隆时返回空列表。"""
    def git(*args):
        return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, encoding='utf-8',
                              check=True, timeout=60).stdout
    try:
        if git('rev-parse', '--is-shallow-repository').strip() != 'false':
            return []
        log = git('log', '--follow', '--format=%H%x1f%ad%x1f%s', '--date=short', '--', relative)
    except (OSError, subprocess.SubprocessError):
        return []
    result = []
    for line in log.splitlines():
        sha, day, message = (line.split('') + ['', '', ''])[:3]
        if re.fullmatch(r'[0-9a-f]{40}', sha) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', day):
            result.append({'sha': sha, 'date': day, 'message': message})
    return result


def revisions_html(src, revs):
    if not revs:
        return ''
    # GitHub 提交页里每个文件的锚点是 diff- 加文件路径的 SHA-256，点“看改动”直接跳到这篇的差异。
    anchor = 'diff-'+sha256(src.encode()).hexdigest()
    rows = ''.join(f'<li><time datetime="{r["date"]}">{r["date"]}</time><span class="rev-message">{escape(r["message"])}</span>'
                   f'<span class="rev-links"><a href="{REPO}/commit/{r["sha"]}#{anchor}">看改动</a>'
                   f'<a href="{REPO}/blob/{r["sha"]}/{src}">当时的版本</a></span></li>' for r in revs)
    return (f'<details class="revisions" id="revisions"><summary>修改记录 · {len(revs)} 次</summary><ol>{rows}</ol>'
            f'<p><a class="text-link" href="{REPO}/commits/main/{src}">在 GitHub 查看完整历史</a></p></details>')


def article_page(meta, html, toc, archive=None, revs=()):
    slug = meta['slug']
    src = ('archive/' if archive else 'content/')+slug+'.md'
    if archive:
        kicker = '<span class="badge badge-archive">历史存档</span>'
        notice = (f'<div class="archive-notice"><p>这是 {meta["created"]} 的旧版存档，在线下载和安装步骤已经变了。</p>'
                  f'<a href="{public_url(archive)}">阅读当前修订版{icon("arrow-right")}</a></div>')
    else:
        kicker = f'<a class="badge" href="{BASE}?c={quote(meta["category"])}">{escape(meta["category"])}</a>'
        kicker += DRAFT_BADGE if meta.get('draft') else ''
        notice = ''
    facts = ''.join(f'<span>{fact}</span>' for fact in recipe_facts(meta))
    history = f'<a class="meta-link" href="#revisions">修改记录</a>' if revs else ''
    edit = (f'<a class="text-link" href="{REPO}/edit/main/{src}">在 GitHub 编辑</a>' if archive
            else f'<a class="text-link" href="{BASE}write/?a={slug}">编辑这篇</a>')
    related = (f'<p class="related-archive">迁移前的 PCL 图文：<a href="{BASE}archive/minecraft-pcl-2026-10-05/">查看 2026-10-05 原文存档</a></p>'
               if slug == 'minecraft-mod' else '')
    return f'''<div class="reading-progress" aria-hidden="true"><span></span></div>
<div class="article-shell">
<nav class="toc-rail" id="toc" aria-label="文章目录">
<a class="back-link" href="{BASE}">{icon('arrow-left')}全部文章</a>
<p class="toc-title">目录</p>
<div class="toc-scroll">{toc_html(toc)}</div>
</nav>
<main id="main" class="article-main"{f' data-reading-slug="{slug}"' if not archive else ''}>
<header class="article-header">
<div class="article-kicker">{kicker}</div>
<h1>{escape(meta['title'])}</h1>
<p class="article-summary">{escape(meta['summary'])}</p>
<p class="article-meta"><span class="byline">{byline(meta)}</span><span>发布 <time datetime="{meta['created']}">{meta['created']}</time></span><span>更新 <time datetime="{meta['updated']}">{meta['updated']}</time></span>{facts}{history}</p>
{bookmark_button(slug, meta['title'], label=True) if not archive else ''}
{notice}
</header>
<div class="reading-bar"><button class="toc-toggle" type="button" aria-expanded="false" aria-controls="toc">{icon('list')}<span class="reading-current">目录</span>{icon('chevron')}</button></div>
<article class="prose">{html}</article>
{related}
<footer class="article-end">
<h2>有问题，就把卡住的地方说清楚。</h2>
<p>带上环境、操作步骤和报错，一起把文章补好。</p>
<p class="end-actions"><a class="button button-primary" href="{REPO}/discussions">去 GitHub 交流{icon('external')}</a><a class="text-link" href="{REPO}/blob/main/{src}">Markdown 原文</a>{edit}</p>
{revisions_html(src, revs)}
<a class="back-link" href="{BASE}">{icon('arrow-left')}全部文章</a>
</footer>
</main>
</div>'''


def bookmark_button(slug, title, label=False):
    return (f'<button class="bookmark-button{" bookmark-labeled" if label else ""}" type="button" '
            f'data-bookmark="{escape(slug)}" data-article-title="{escape(title)}" aria-pressed="false" '
            f'aria-label="收藏：{escape(title)}" hidden>{icon("bookmark")}<span class="bookmark-label">收藏文章</span></button>')


def entry_html(meta, show_author=False):
    url = public_url(meta['slug'])
    note = ''
    if meta.get('note'):
        n = meta['note']
        note = (f'<p class="entry-note"><a href="{url}#{quote(n["anchor"])}"><span class="note-tag">{escape(n["date"])} 更新</span>'
                f'<span class="note-text">{escape(n["text"])}</span>{icon("arrow-right")}</a></p>')
    facts = ''.join(f'<span>{fact}</span>' for fact in recipe_facts(meta))
    return (f'<li class="entry" data-slug="{escape(meta["slug"])}" data-category="{escape(meta["category"])}">'
            f'<p class="entry-meta"><span class="entry-cat">{escape(meta["category"])}</span>'
            f'{f"<span class=entry-author>{byline(meta, link=False)}</span>" if show_author else ""}'
            f'<span>更新 <time datetime="{meta["updated"]}">{meta["updated"]}</time></span>{facts}'
            f'{DRAFT_BADGE if meta.get("draft") else ""}{bookmark_button(meta["slug"], meta["title"])}</p>'
            f'<h3 class="entry-title"><a href="{url}">{escape(meta["title"])}</a></h3>'
            f'<p class="entry-summary">{escape(meta["summary"])}</p>{note}</li>')


def editor_page(catalog, authors):
    """写作页：页面本身是静态的，文章内容由浏览器向 GitHub 接口读取；这里只放文章列表、模板和渲染规则。"""
    fields = ('slug', 'title', 'category', 'type', 'author', 'summary', 'created', 'updated', 'draft', 'recipe')
    data = {
        'repo': REPO.removeprefix('https://github.com/'), 'branch': 'main', 'base': BASE, 'all': ALL,
        'types': {key: label for key, (label, _) in TYPES.items()}, 'languages': LANGUAGES, 'callouts': CALLOUTS,
        'templates': {key: (ROOT/'scripts'/'templates'/f'{key}.md').read_text(encoding='utf-8') for key in TYPES},
        'authors': [{key: a[key] for key in ('id', 'name', 'github') if key in a} for a in authors.values()],
        'articles': [{key: meta[key] for key in fields if key in meta}
                     for meta in sorted(catalog, key=lambda a: (a['created'], a['slug']), reverse=True)],
    }
    categories = ''.join(f'<option value="{escape(c)}"></option>' for c in dict.fromkeys(a['category'] for a in catalog))
    types = ''.join(f'<option value="{key}">{label}</option>' for key, (label, _) in TYPES.items())
    writers = ''.join(f'<label class="check"><input type="checkbox" value="{escape(a["id"])}">{escape(a["name"])}</label>' for a in authors.values())
    blob = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
    return f'''<main id="main" class="editor">
<div class="ed-bar">
<div class="ed-doc"><label class="visually-hidden" for="ed-article">选择文章</label><select id="ed-article" class="ed-select"></select><button class="button" type="button" id="ed-new">新建</button></div>
<p id="ed-status" class="ed-status" role="status">正在准备……</p>
<div class="ed-actions"><button class="button" type="button" id="ed-info" aria-expanded="true" aria-controls="ed-meta">收起信息</button><button class="button" type="button" id="ed-history">版本</button><button class="button button-primary" type="button" id="ed-commit">提交</button></div>
</div>
<section id="ed-meta" class="ed-meta" aria-label="文章信息">
<div class="ed-fields">
<label class="ed-title">标题<textarea id="m-title" rows="2" placeholder="填写文章标题"></textarea></label>
<label>分类标签<input id="m-category" list="ed-categories" placeholder="例如 CS、Windows"></label><datalist id="ed-categories">{categories}</datalist>
<label class="wide">摘要（标题下方的介绍）<textarea id="m-summary" rows="2" placeholder="用一段话介绍这篇文章"></textarea></label>
</div>
<details id="ed-options" class="ed-options"><summary>更多设置</summary><div class="ed-fields ed-extra">
<label>类型<select id="m-type">{types}</select></label>
<fieldset class="ed-authors" id="m-authors"><legend>作者</legend>{writers}</fieldset>
<label>更新日期<input id="m-updated" type="date"></label>
<label class="check"><input id="m-draft" type="checkbox">草稿（不发布）</label>
<label class="recipe-only">份量<input id="m-servings" placeholder="2 人份"></label>
<label class="recipe-only">用时（分钟）<input id="m-minutes" type="number" min="1" max="10000" inputmode="numeric"></label>
</div></details>
</section>
<div class="ed-tabs" role="tablist" aria-label="切换源代码和预览"><button type="button" role="tab" data-view="source" aria-selected="true" aria-controls="ed-source">源代码</button><button type="button" role="tab" data-view="preview" aria-selected="false" aria-controls="ed-preview">预览</button></div>
<div class="ed-panes" id="ed-panes" data-view="source">
<div class="ed-source" id="ed-source"><label class="visually-hidden" for="ed-text">Markdown 源代码</label><textarea id="ed-text" spellcheck="false" autocapitalize="off" disabled></textarea><div class="ed-mirror" id="ed-mirror" aria-hidden="true"></div></div>
<div class="ed-preview" id="ed-preview" tabindex="0" role="region" aria-label="预览"><div class="ed-preview-inner"><header class="article-header" id="ed-head"></header><article class="prose" id="ed-body"></article></div></div>
</div>
<noscript><p class="ed-noscript">写作页需要启用 JavaScript。也可以直接在 GitHub 网页上编辑 content/ 里的文章。</p></noscript>
</main>
<script type="application/json" id="editor-data">{blob}</script>'''


def author_page(author, articles):
    """作者分区页：作者简介和 TA 写的全部文章。"""
    mine = [a for a in articles if author['id'] in author_ids(a)]
    categories = '、'.join(dict.fromkeys(a['category'] for a in mine))
    facts = [f'{len(mine)} 篇文章'] + ([f'分类：{escape(categories)}'] if categories else [])
    if author.get('github'):
        facts.append(f'<a class="meta-link" href="https://github.com/{author["github"]}">GitHub @{escape(author["github"])}</a>')
    if author.get('url'):
        facts.append(f'<a class="meta-link" href="{escape(author["url"])}">个人主页</a>')
    entries = ''.join(entry_html(a) for a in mine) or '<li class="entry entry-empty"><p class="entry-summary">还没有发表文章。</p></li>'
    back = f'<a class="back-link" href="{BASE}authors/">{icon("arrow-left")}全部作者</a>' if SITE_STATE['multi_author'] else ''
    return f'''<main id="main" class="home-main author-main">
<section class="intro" aria-labelledby="intro-title">
{back}
<p class="author-kicker">作者</p>
<h1 id="intro-title">{escape(author['name'])}</h1>
{f'<p>{escape(author["bio"])}</p>' if author.get('bio') else ''}
<p class="intro-meta">{' · '.join(facts)}</p>
</section>
<section class="library" aria-labelledby="author-articles">
<h2 id="author-articles" class="visually-hidden">{escape(author['name'])} 的文章</h2>
<ol class="entries">{entries}</ol>
</section>
</main>'''


def authors_index(authors, articles):
    rows = []
    for author in authors.values():
        mine = [a for a in articles if author['id'] in author_ids(a)]
        categories = '、'.join(dict.fromkeys(a['category'] for a in mine))
        kinds = f'<span>{escape(categories)}</span>' if categories else ''
        bio = f'<p class="entry-summary">{escape(author.get("bio", ""))}</p>' if author.get('bio') else ''
        rows.append(f'<li class="entry"><p class="entry-meta"><span>{len(mine)} 篇文章</span>{kinds}</p>'
                    f'<h3 class="entry-title"><a href="{author_url(author["id"])}">{escape(author["name"])}</a></h3>{bio}</li>')
    return f'''<main id="main" class="home-main">
<section class="intro" aria-labelledby="intro-title"><h1 id="intro-title">作者</h1><p>每位作者都有自己的分区，点名字看 TA 写的全部文章。</p></section>
<section class="library" aria-label="作者列表"><ol class="entries">{''.join(rows)}</ol></section>
</main>'''


def read_home_note(root=ROOT):
    path = root/'home.json'
    if not path.exists():
        return ''
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, OSError) as error:
        raise BuildError('home.json：无法读取首页动态，请检查 JSON 格式') from error
    if not isinstance(data, dict) or not isinstance(data.get('now', ''), str) or len(data.get('now', '')) > 200:
        raise BuildError('home.json：now 应是 200 字以内的文字，留空则隐藏')
    return data.get('now', '').strip()


def utility_dialog():
    return f'''<dialog id="utility-dialog" class="utility-dialog" aria-labelledby="utility-title">
<div class="utility-head"><h2 id="utility-title">常用工具</h2><button class="icon-button" type="button" data-close-tool aria-label="关闭工具">{icon('close')}</button></div>
<section id="json-tool" class="utility-panel" hidden>
<label for="json-input">JSON 内容</label><textarea id="json-input" spellcheck="false" placeholder="粘贴 JSON 内容"></textarea>
<div class="utility-actions"><button class="button button-primary" type="button" data-json-action="format">格式化</button><button class="button" type="button" data-json-action="minify">压缩</button><button class="button" type="button" data-copy-json>复制结果</button></div>
<label for="json-output">处理结果</label><textarea id="json-output" spellcheck="false" readonly></textarea>
</section>
<section id="timestamp-tool" class="utility-panel" hidden>
<label for="unix-input">Unix 时间戳（秒或毫秒）</label><input id="unix-input" type="text" inputmode="numeric" placeholder="输入 10 位或 13 位时间戳">
<button class="button" type="button" data-convert-unix>转换为日期</button>
<label for="date-input">日期与时间（当前设备时区）</label><input id="date-input" type="datetime-local" step="1">
<button class="button" type="button" data-convert-date>转换为时间戳</button>
<output id="timestamp-output"></output>
</section>
<p id="utility-status" class="utility-status" role="status"></p><p class="utility-hint">内容只在当前浏览器中处理。</p>
</dialog>'''


def home_page(articles, index_url, now=''):
    categories = list(dict.fromkeys(a['category'] for a in articles))
    counts = [(ALL, len(articles))]+[(c, sum(a['category'] == c for a in articles)) for c in categories]
    chips = ''.join(
        f'<button class="chip{" is-active" if name == ALL else ""}" type="button" data-category="{escape(name)}" '
        f'aria-pressed="{"true" if name == ALL else "false"}">{escape(name)}<span class="chip-count" data-total="{count}">{count}</span></button>'
        for name, count in counts)
    latest = max(a['updated'] for a in articles)
    multi = SITE_STATE['multi_author']
    count = len({i for a in articles for i in author_ids(a)})
    writers = f' · <a class="meta-link" href="{BASE}authors/">{count} 位作者</a>' if multi else ''
    recent = ''.join(f'<li><time datetime="{a["updated"]}">{a["updated"]}</time><a href="{public_url(a["slug"])}">{escape(a["title"])}</a></li>'
                     for a in sorted(articles, key=lambda a: a['updated'], reverse=True)[:3])
    note = f'<p class="home-now"><span>正在折腾</span>{escape(now)}</p>' if now else ''
    return f'''<main id="main" class="home-main home-workspace">
<aside class="home-rail" aria-label="首页工具">
<details class="home-toolbox" open><summary>阅读与工具{icon('chevron')}</summary><div class="home-toolbox-body">
<nav class="rail-nav js-only" aria-label="文章视图"><button class="rail-button is-active" type="button" data-library-view="all" aria-pressed="true">{icon('list')}全部文章<span>{len(articles)}</span></button><button class="rail-button" type="button" data-library-view="saved" aria-pressed="false">{icon('bookmark')}我的收藏<span data-saved-count>0</span></button></nav>
<section class="rail-section js-only" aria-labelledby="resume-title"><h2 id="resume-title">继续阅读</h2><p class="rail-empty" id="resume-empty">读过文章后，这里会记住你的位置。</p><a class="resume-link" id="resume-link" hidden><span id="resume-name"></span><span class="resume-meta" id="resume-meta"></span><progress id="resume-progress" max="100" value="0" aria-label="上次阅读进度"></progress></a></section>
<section class="rail-section" aria-labelledby="tools-title"><h2 id="tools-title">常用工具</h2><button class="rail-button js-only" type="button" data-open-tool="json">{icon('code')}JSON 格式化</button><button class="rail-button js-only" type="button" data-open-tool="timestamp">{icon('clock')}时间戳转换</button><a class="rail-button" href="{BASE}articles/git-basics/#git-commands-a">{icon('list')}Git 命令速查{icon('arrow-right')}</a></section>
<section class="rail-section" aria-labelledby="recent-title"><h2 id="recent-title">最近更新</h2><ol class="rail-recent">{recent}</ol></section>
<a class="rail-feedback" href="{REPO}/discussions">提问与反馈{icon('external')}</a>
</div></details>
</aside>
<div class="home-content">
<section class="intro" aria-labelledby="intro-title">
<h1 id="intro-title">Milo 的笔记</h1>
<p>记录我学编程、修电脑时遇到的问题和解决过程，以后也写做菜和生活。</p>
<p class="intro-meta">{len(articles)} 篇文章{writers} · 最近更新 <time datetime="{latest}">{latest}</time></p>
{note}
</section>
<section id="library" class="library" aria-labelledby="library-title">
<h2 id="library-title" class="visually-hidden">全部文章</h2>
<div class="search" id="search" role="search">
<label class="visually-hidden" for="search-input">搜索全文</label>{icon('search')}
<input id="search-input" type="search" placeholder="搜索标题、正文、命令或报错" autocomplete="off" spellcheck="false" enterkeyhint="search" aria-controls="article-list">
<button class="icon-button search-clear" type="button" aria-label="清空搜索" hidden>{icon('close')}</button>
<kbd class="search-key" aria-hidden="true">/</kbd>
</div>
<div class="chips" role="group" aria-label="按分类筛选">{chips}</div>
<p id="search-status" class="search-status" role="status"></p>
<div id="search-notice" class="search-notice" hidden></div>
<ol id="article-list" class="entries" data-index="{index_url}" data-multi-author="{str(multi).lower()}">{''.join(entry_html(a, multi) for a in articles)}</ol>
</section>
</div>
</main>{utility_dialog()}'''


# ---------- 输出 ----------

PUBLIC_ASSET_SUFFIXES = {'.css', '.js', '.svg', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.avif', '.ico'}
PUBLIC_ASSET_FILES = {'IMAGE-SOURCES.md', 'vendor/markdown-it-LICENSE.txt'}


def is_public_asset(relative):
    """assets/ 里只发布网页用得到的文件，隐藏文件、草稿和其他格式一律不发。"""
    if any(part.startswith('.') for part in relative.parts):
        return False
    return relative.suffix.lower() in PUBLIC_ASSET_SUFFIXES or relative.as_posix() in PUBLIC_ASSET_FILES


def reset_output():
    # 只清理仓库根目录下名为 _site 的真实目录，防止配置写错时删到别处。
    if OUT.is_symlink() or OUT.parent.resolve() != ROOT.resolve() or OUT.name != '_site':
        raise BuildError(f'输出目录异常，已停止：{OUT}')
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()


def write(relative, text):
    target = (OUT/relative).resolve()
    if not target.is_relative_to(OUT.resolve()):
        raise BuildError(f'拒绝写到 _site 之外：{relative}')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding='utf-8')


def copy_assets():
    source = ASSETS.resolve()
    skipped = []
    for path in sorted(source.rglob('*')):
        relative = path.relative_to(source)
        if path.is_dir() and not path.is_symlink():
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(source) or not is_public_asset(relative):
            skipped.append(relative.as_posix())
            continue
        target = OUT/'assets'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    for name, expected in VENDOR_HASHES.items():
        if sha256((source/name).read_bytes()).hexdigest() != expected:
            raise BuildError(f'assets/{name} 和记录的哈希不一致，可能被改动过；请从 npm 官方包重新取得')
    for name in ('site.css', 'site.js', 'home.js', 'editor.css', 'editor.js', VENDOR_MARKDOWN_IT):
        digest = sha256((source/name).read_bytes()).hexdigest()[:10]
        ASSET_URLS[name] = f'{BASE}assets/{name}?v={digest}'
    return skipped


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description='构建 ByteLife 静态网站。')
    parser.add_argument('--drafts', action='store_true', help='连同草稿一起构建，只用于本地预览，不要拿这次结果发布')
    options = parser.parse_args(argv)
    try:
        website_id = load_website_id(ROOT/'analytics.json')
    except ValueError as error:
        raise BuildError(str(error)) from error
    # --drafts 生成的预览即使使用线上域名，也不能发送统计。
    SITE_STATE['analytics_website_id'] = '' if options.drafts else website_id
    authors = read_authors()
    owner = next(iter(authors.values()))
    catalog = validate_articles(json.loads((ROOT/'articles.json').read_text(encoding='utf-8')), authors=authors)
    articles = list(catalog)
    drafts = [a['slug'] for a in articles if a.get('draft')]
    if not options.drafts:
        articles = [a for a in articles if not a.get('draft')]
    if not articles:
        raise BuildError('articles.json 里没有可发布的文章（全部是草稿？）')
    articles.sort(key=lambda a: (a['created'], a['slug']), reverse=True)
    published = [a for a in articles if not a.get('draft')]
    SITE_STATE['multi_author'] = len({i for a in published for i in author_ids(a)}) > 1
    reset_output()
    skipped = copy_assets()

    search = []
    for meta in articles:
        raw = meta['path'].read_text(encoding='utf-8')
        html, toc = render(raw)
        image = re.search(r'<img src="(/[^"]+)"', html)
        meta.update(image=ORIGIN+image[1] if image else None, recipe_parts=recipe_parts(raw) if meta['type'] == 'recipe' else None)
        body = article_page(meta, html, toc, revs=revisions(f'content/{meta["slug"]}.md'))
        write(f'articles/{meta["slug"]}/index.html', shell(meta['title'], meta['summary'], body, f'articles/{meta["slug"]}/', meta,
                                                           noindex=bool(meta.get('draft')), page='page article'))
        search.append({key: meta[key] for key in ('slug', 'title', 'category', 'summary', 'updated')}
                      | {'authors': byline(meta, link=False), 'url': public_url(meta['slug']), 'sections': sections(html)})

    archive_meta = {
        'slug': 'minecraft-pcl-2026-10-05', 'title': '从 PCL 玩明白，到用 VS Code 写出第一个 Minecraft Java 模组（原文存档）',
        'summary': '保留原论坛的旧版 PCL 下载、安装操作和全部配图。在线安装步骤已有变化，请优先阅读当前修订版。',
        'category': '历史存档', 'created': '2026-10-05', 'updated': '2026-10-22', 'author_list': [owner],
    }
    html, toc = render((ROOT/'archive'/f'{archive_meta["slug"]}.md').read_text(encoding='utf-8'))
    write(f'archive/{archive_meta["slug"]}/index.html',
          shell(archive_meta['title'], archive_meta['summary'], article_page(archive_meta, html, toc, archive='minecraft-mod', revs=revisions(f'archive/{archive_meta["slug"]}.md')),
                f'archive/{archive_meta["slug"]}/', noindex=True, page='page article'))

    # 历史存档不进全文索引；索引地址带内容哈希，发布后读者不会拿到旧索引。
    index = json.dumps(search, ensure_ascii=False, separators=(',', ':'))
    index_url = f'{BASE}search-index.json?v={sha256(index.encode()).hexdigest()[:10]}'
    write('search-index.json', index)
    write('index.html', shell('Milo 的笔记', 'Milo Guo 的学习与生活笔记：Git 入门、Minecraft Java 模组开发、Windows 问题排查，步骤和原因一起写清楚。',
                              home_page(articles, index_url, read_home_note()), page='page home', search_link=False, scripts=('home.js',)))
    # 写作页列出全部文章（含草稿）：articles.json 本来就在公开仓库里。页面不让搜索引擎收录。
    write('write/index.html', shell('写作', '在浏览器里编辑 ByteLife 文章：左边 Markdown，右边实时预览。',
                                    editor_page(catalog, authors),
                                    'write/', noindex=True, page='page editor-page', csp=EDITOR_CSP,
                                    styles=('editor.css',), scripts=(VENDOR_MARKDOWN_IT, 'editor.js')))

    html, _ = render((ROOT/'MIGRATION.md').read_text(encoding='utf-8'))
    write('migration/index.html', shell('从论坛迁到这里', 'ByteLife 公开文章、配图和历史版本的迁移记录。',
                                        f'<main id="main" class="single"><a href="{BASE}" class="back-link">{icon("arrow-left")}回到首页</a><article class="prose">{html}</article></main>', 'migration/'))
    write('404.html', shell('这一页没找到', '返回 ByteLife 文章目录。',
                            f'<main id="main" class="single not-found"><h1>这一页没找到。</h1><p>文章可能换过地址。可以回首页搜索标题或正文里的关键词。</p>'
                            f'<p><a class="button button-primary" href="{BASE}#search">{icon("search")}去首页搜索</a></p></main>', '404.html', noindex=True))

    # 作者分区页：只算已发表的文章；还没有发表文章的作者页不让搜索引擎收录。
    for author in authors.values():
        count = sum(author['id'] in author_ids(a) for a in published)
        write(f'authors/{author["id"]}/index.html',
              shell(f'{author["name"]} 的文章', author.get('bio') or f'{author["name"]} 在 ByteLife 写的文章。', author_page(author, articles),
                    f'authors/{author["id"]}/', noindex=not count, page='page home'))
    write('authors/index.html', shell('作者', 'ByteLife 的作者和各自的文章分区。', authors_index(authors, published), 'authors/',
                                      noindex=not SITE_STATE['multi_author'], page='page home'))

    # 草稿不进站点地图和 RSS。
    latest = max(a['updated'] for a in published or articles)
    links = [(ORIGIN+BASE, latest)]+[(ORIGIN+public_url(a['slug']), a['updated']) for a in published]
    links += [(ORIGIN+author_url(aid), max(a['updated'] for a in published if aid in author_ids(a)))
              for aid in authors if any(aid in author_ids(a) for a in published)]
    if SITE_STATE['multi_author']:
        links.append((ORIGIN+BASE+'authors/', latest))
    write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
          + ''.join(f'<url><loc>{url}</loc><lastmod>{updated}</lastmod></url>' for url, updated in links)+'</urlset>')
    write('robots.txt', f'User-agent: *\nAllow: /\nSitemap: {ORIGIN}{BASE}sitemap.xml\n')
    china = timezone(timedelta(hours=8))
    rss = '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><title>ByteLife</title><link>'+ORIGIN+BASE+'</link><description>Milo 的学习与生活记录</description>'
    for a in published:
        url = ORIGIN+public_url(a['slug'])
        pub_date = format_datetime(datetime.fromisoformat(a['created']).replace(tzinfo=china))
        rss += ('<item><title>'+xml_escape(a['title'])+'</title><link>'+url+'</link><guid>'+url+'</guid><pubDate>'+pub_date
                + '</pubDate>'+''.join('<dc:creator>'+xml_escape(x['name'])+'</dc:creator>' for x in a['author_list'])
                + '<description>'+xml_escape(a['summary'])+'</description></item>')
    write('feed.xml', rss+'</channel></rss>')
    write('.nojekyll', '')

    unlisted = sorted({p.stem for p in CONTENT.glob('*.md')}-{a['slug'] for a in catalog})
    if unlisted:
        print('未列入 articles.json、本次不发布：'+'、'.join(unlisted))
    if drafts and options.drafts:
        print('已包含草稿，只供本地预览：'+'、'.join(drafts)+'。发布前请不加 --drafts 重新构建。')
    elif drafts:
        print('草稿未发布：'+'、'.join(drafts)+'（本地预览草稿用 python scripts/build.py --drafts）')
    if skipped:
        print('assets 中这些文件不是网页资源，未发布：'+'、'.join(skipped))
    if SITE_STATE['analytics_website_id']:
        print('访问统计：已配置 Umami Cloud，仅线上域名的正式阅读页面发送统计；写作页不发送。')
    else:
        print('访问统计：未启用（website_id 为空，或正在构建草稿预览）。')
    print(f'构建完成：{len(articles)} 篇文章、1 篇历史存档、全文索引与站点地图 → {OUT}')


if __name__ == '__main__':
    main()
