"""检查 _site：本地链接、图片与章节锚点，以及发布内容和页面安全规则。不连接外部网站。"""
from base64 import b64encode
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT/'_site'
BASE = '/bytelife/'
ORIGIN = 'https://milo-guo.github.io'

PUBLIC_SUFFIXES = {'.html', '.css', '.js', '.json', '.xml', '.txt', '.svg', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.avif', '.ico', '.md'}
PRIVATE_NAME = re.compile(r'(?i)(^\.env|\.(sql|sqlite3?|db|bak|dump|zip|7z|rar|tar|gz|tgz|pem|key|p12|pfx|kdbx|log|tmp|psd)$'
                          r'|^id_(rsa|ed25519|ecdsa)|~$|^(thumbs\.db|desktop\.ini|\.ds_store)$)')
# 只报告类别和位置，不打印匹配到的内容。
SECRETS = {
    'GitHub 令牌': r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})',
    '私钥': r'-----BEGIN [A-Z ]*PRIVATE KEY-----',
    'AWS 访问密钥': r'\bAKIA[0-9A-Z]{16}\b',
    'sk- 开头的 API 密钥': r'\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{24,}',
    'Slack 令牌': r'\bxox[abposr]-[A-Za-z0-9-]{10,}',
    'Google API 密钥': r'\bAIza[0-9A-Za-z_-]{35}\b',
}
SAFE_SCHEMES = {'http', 'https', 'mailto'}
FORBIDDEN_TAGS = {'iframe', 'frame', 'object', 'embed', 'applet', 'form', 'base', 'style'}


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.duplicates = []
        self.links = []
        self.problems = []
        self.scripts = []
        self.csp = None
        self.csp_first = False
        self.loaded_before_csp = False
        self.robots = ''
        self.script = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id'):
            if a['id'] in self.ids:
                self.duplicates.append(a['id'])
            self.ids.add(a['id'])
        for name, value in attrs:
            if name.startswith('on'):
                self.problems.append(f'<{tag}> 带事件属性 {name}')
            elif name == 'style':
                self.problems.append(f'<{tag}> 带 style 属性，会被 CSP 拦截')
            elif name in ('href', 'src', 'action', 'formaction', 'srcset', 'poster') and value:
                self.links.append((tag, name, value, a.get('rel', '')))
        if tag in FORBIDDEN_TAGS:
            self.problems.append(f'出现 <{tag}>')
        if tag == 'meta' and a.get('http-equiv', '').lower() == 'content-security-policy':
            self.csp = a.get('content', '')
            self.csp_first = not self.loaded_before_csp
        if tag == 'meta' and a.get('name') == 'robots':
            self.robots = a.get('content', '')
        if tag in ('script', 'link', 'img'):
            self.loaded_before_csp = True
        if tag == 'script':
            self.script = [a, '']

    def handle_data(self, data):
        if self.script is not None:
            self.script[1] += data

    def handle_endtag(self, tag):
        if tag == 'script' and self.script is not None:
            self.scripts.append(tuple(self.script))
            self.script = None


def page_rules(path, page, errors):
    name = path.relative_to(OUT).as_posix()
    errors.extend(f'{name}: 重复锚点 {x}' for x in page.duplicates)
    errors.extend(f'{name}: {x}' for x in page.problems)
    if not page.csp:
        errors.append(f'{name}: 缺少 CSP')
        return
    if not page.csp_first:
        errors.append(f'{name}: CSP 必须放在所有脚本、样式和图片之前')
    if re.search(r"'unsafe-(inline|eval)'|\*", page.csp):
        errors.append(f'{name}: CSP 不应放开 unsafe-inline、unsafe-eval 或通配符')
    for attrs, text in page.scripts:
        if attrs.get('src'):
            if urlsplit(attrs['src']).scheme or not attrs['src'].startswith(BASE):
                errors.append(f'{name}: 外部脚本 {attrs["src"]}')
        elif attrs.get('type') in ('application/ld+json', 'application/json'):
            try:
                json.loads(text)
            except ValueError:
                errors.append(f'{name}: 结构化数据不是合法 JSON')
        else:
            digest = "'sha256-"+b64encode(sha256(text.encode()).digest()).decode()+"'"
            if digest not in page.csp:
                errors.append(f'{name}: 内联脚本的哈希不在 CSP 里')
    archived = name.startswith(('archive/', 'write/')) or name == '404.html'
    if name.startswith('authors/'):
        return   # 作者页：只有一位作者或还没发表文章时不让收录，其余正常收录
    if archived and 'noindex' not in page.robots:
        errors.append(f'{name}: 存档页、写作页和 404 应设置 noindex')
    if not archived and 'noindex' in page.robots:
        errors.append(f'{name}: 正式页面不应 noindex')


def link_rules(path, page, pages, errors):
    checked = 0
    name = path.relative_to(OUT).as_posix()
    for tag, attr, link, rel in page.links:
        parts = urlsplit(link)
        if parts.scheme and parts.scheme.lower() not in SAFE_SCHEMES:
            errors.append(f'{name}: 不允许的地址协议 {parts.scheme}: 出现在 <{tag} {attr}>')
            continue
        if parts.scheme or parts.netloc:
            # 外部图片、脚本、样式会被 CSP 拦下，也会把访客信息带给第三方。
            if tag in ('img', 'script', 'source', 'use') or (tag == 'link' and rel in ('stylesheet', 'icon', 'preload')):
                errors.append(f'{name}: 引用了外部资源 {link}')
            if tag == 'link' and rel == 'canonical' and not link.startswith(ORIGIN+BASE):
                errors.append(f'{name}: canonical 不在站点地址下 {link}')
            continue
        if not parts.path:
            target = path
        elif parts.path.startswith(BASE):
            target = OUT/unquote(parts.path[len(BASE):])
        elif parts.path.startswith('/'):
            errors.append(f'{name}: 未使用项目路径 {link}')
            continue
        else:
            target = path.parent/unquote(parts.path)
        if target.is_dir():
            target = target/'index.html'
        target = target.resolve()
        if not target.is_relative_to(OUT.resolve()) or not target.exists():
            errors.append(f'{name}: 文件不存在 {link}')
        elif parts.fragment and target in pages and unquote(parts.fragment) not in pages[target].ids:
            errors.append(f'{name}: 锚点不存在 {link}')
        checked += 1
    return checked


def vendor_files(errors):
    """第三方前端文件必须和 npm 官方包里的原文件逐字节一致。"""
    sys.path.insert(0, str(ROOT/'scripts'))
    from build import VENDOR_HASHES
    for name, expected in VENDOR_HASHES.items():
        path = OUT/'assets'/name
        if not path.exists() or sha256(path.read_bytes()).hexdigest() != expected:
            errors.append(f'assets/{name}: 和记录的官方文件哈希不一致')


def published_files(errors):
    for path in sorted(OUT.rglob('*')):
        if path.is_dir():
            continue
        name = path.relative_to(OUT).as_posix()
        if path.is_symlink():
            errors.append(f'{name}: 发布目录里不应有符号链接')
        if path.name != '.nojekyll' and (PRIVATE_NAME.search(path.name) or path.suffix.lower() not in PUBLIC_SUFFIXES):
            errors.append(f'{name}: 不应发布的文件类型')
        if path.suffix.lower() in ('.html', '.css', '.js', '.json', '.xml', '.txt', '.md', '.svg'):
            text = path.read_text(encoding='utf-8', errors='replace')
            for label, pattern in SECRETS.items():
                for match in re.finditer(pattern, text):
                    line = text.count('\n', 0, match.start())+1
                    errors.append(f'{name}:{line}: 疑似{label}（内容未显示）')


def draft_rule():
    """草稿（"draft": true）不能出现在要发布的目录里；本地用 --drafts 预览过的话，要不加参数重新构建。"""
    drafts = [m['slug'] for m in json.loads((ROOT/'articles.json').read_text(encoding='utf-8'))
              if m.get('draft') and (OUT/'articles'/m['slug']).exists()]
    return [f'发布目录里有草稿 {"、".join(drafts)}：这是 --drafts 的本地预览结果，发布前运行 python scripts/build.py 重新构建'] if drafts else []


def site_rules(pages, errors):
    if draft_rule():
        errors.extend(draft_rule())
        return
    catalog = [m for m in json.loads((ROOT/'articles.json').read_text(encoding='utf-8')) if not m.get('draft')]
    public = {f'{BASE}articles/{meta["slug"]}/' for meta in catalog}
    index = json.loads((OUT/'search-index.json').read_text(encoding='utf-8'))
    for entry in index:
        if entry.get('url') not in public:
            errors.append(f'search-index.json: 收录了不该公开搜索的地址 {entry.get("url")}')
            continue
        target = (OUT/entry['url'][len(BASE):]/'index.html').resolve()
        missing = [s[0] for s in entry.get('sections', []) if s[0] and s[0] not in pages[target].ids]
        if missing:
            errors.append(f'search-index.json: {entry["url"]} 的章节锚点不存在 {missing[:3]}')
    if len(index) != len(public):
        errors.append('search-index.json: 文章数量和 articles.json 不一致')
    for feed in ('sitemap.xml', 'feed.xml'):
        text = (OUT/feed).read_text(encoding='utf-8')
        for url in re.findall(r'<(?:loc|link)>([^<]+)</', text):
            if not url.startswith(ORIGIN+BASE) or '/archive/' in url:
                errors.append(f'{feed}: 不应出现的地址 {url}')
    # Markdown 里写过的旧锚点（name/id）必须原样出现在生成页里，旧的章节直达链接才不会失效。
    sources = [(ROOT/'content'/f'{m["slug"]}.md', OUT/'articles'/m['slug']/'index.html') for m in catalog]
    sources += [(p, OUT/'archive'/p.stem/'index.html') for p in (ROOT/'archive').glob('*.md')]
    for source, built in sources:
        raw = re.sub(r'```.*?```', '', source.read_text(encoding='utf-8'), flags=re.S)
        for anchor in re.findall(r'<a\s+(?:name|id)="([^"]+)"', raw):
            if anchor not in pages[built.resolve()].ids:
                errors.append(f'{built.relative_to(OUT).as_posix()}: 旧锚点 {anchor} 丢失')
    for meta in catalog:
        raw = (ROOT/'content'/f'{meta["slug"]}.md').read_text(encoding='utf-8')
        if 'upload://' in raw or 'discourse-cdn.com/' in raw:
            errors.append(f'{meta["slug"]}: 残留论坛图片地址')
    if list(ROOT.glob('*.sql*'))+list(ROOT.glob('.env*')):
        errors.append('仓库根目录发现不应公开的备份或环境文件')


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    if draft_rule():
        raise SystemExit('检查未通过：\n'+'\n'.join(draft_rule()))
    pages = {}
    for path in OUT.rglob('*.html'):
        parser = Page()
        parser.feed(path.read_text(encoding='utf-8'))
        pages[path.resolve()] = parser
    errors = []
    checked = 0
    for path, page in pages.items():
        page_rules(path, page, errors)
        checked += link_rules(path, page, pages, errors)
    published_files(errors)
    vendor_files(errors)
    site_rules(pages, errors)
    if errors:
        raise SystemExit('检查未通过：\n'+'\n'.join(errors))
    print(f'检查通过：{len(pages)} 个页面，{checked} 个本地链接与锚点；CSP、内联脚本哈希、发布文件和全文索引范围均符合规则。')


if __name__ == '__main__':
    main()
