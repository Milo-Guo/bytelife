"""检查生成页的本地链接、图片与章节锚点，不连接外部网站。"""
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT/'_site'
BASE = '/bytelife/'


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.duplicates = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id'):
            if a['id'] in self.ids:
                self.duplicates.append(a['id'])
            self.ids.add(a['id'])
        for attr in ('href', 'src'):
            if a.get(attr):
                self.links.append(a[attr])


def main():
    pages = {}
    for path in OUT.rglob('*.html'):
        parser = Links()
        parser.feed(path.read_text(encoding='utf-8'))
        pages[path.resolve()] = parser
    errors = []
    checked = 0
    for path, parser in pages.items():
        errors.extend(f'{path.name}: 重复锚点 {x}' for x in parser.duplicates)
        for link in parser.links:
            parts = urlsplit(link)
            if parts.scheme or parts.netloc:
                continue
            if not parts.path:
                target = path
            elif parts.path.startswith(BASE):
                target = OUT/unquote(parts.path[len(BASE):])
            elif parts.path.startswith('/'):
                errors.append(f'{path}: 未使用项目路径 {link}')
                continue
            else:
                target = path.parent/unquote(parts.path)
            if target.is_dir():
                target = target/'index.html'
            target = target.resolve()
            if not target.exists():
                errors.append(f'{path}: 文件不存在 {link}')
            elif parts.fragment and target in pages and unquote(parts.fragment) not in pages[target].ids:
                errors.append(f'{path}: 锚点不存在 {link}')
            checked += 1
    catalog = json.loads((ROOT/'articles.json').read_text(encoding='utf-8'))
    for meta in catalog:
        raw = (ROOT/'content'/f'{meta["slug"]}.md').read_text(encoding='utf-8')
        if 'upload://' in raw or 'discourse-cdn.com/' in raw:
            errors.append(f'{meta["slug"]}: 残留论坛图片地址')
    private = list(ROOT.glob('*.sql*'))+list(ROOT.glob('.env*'))
    if private:
        errors.append('仓库根目录发现不应公开的备份或环境文件')
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'检查通过：{len(pages)} 个页面，{checked} 个本地链接与锚点；正文图片均为仓库内文件。')


if __name__ == '__main__':
    main()
