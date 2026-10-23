"""新建一篇文章：按类型模板生成 content/<slug>.md，并在 articles.json 里登记为草稿。

不带参数运行会逐项询问：
  python scripts/new.py
也可以一次写全：
  python scripts/new.py --slug tomato-egg --title "番茄炒蛋" --category 做菜 --type recipe --summary "……" --servings "2 人份" --minutes 20

草稿不会发布。写完后删掉 articles.json 里这篇的 "draft": true，再构建、检查、提交。
"""
import argparse
from datetime import date
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

TEMPLATES = Path(__file__).resolve().parent/'templates'
TYPE_NAMES = {**{key: key for key in build.TYPES}, **{label: key for key, (label, _) in build.TYPES.items()}}


def create_article(meta, root=build.ROOT, templates=TEMPLATES):
    """写入 Markdown 和 articles.json。任何一步校验失败都不留下半成品，返回新文件路径。"""
    if not build.SLUG.match(meta['slug']) or len(meta['slug']) > 80:
        raise build.BuildError(f'slug「{meta["slug"]}」只能用小写英文、数字和连字符，例如 tomato-egg')
    catalog_path = root/'articles.json'
    raw = catalog_path.read_bytes().decode('utf-8')
    newline = '\r\n' if '\r\n' in raw else '\n'
    catalog = json.loads(raw)
    if any(item.get('slug') == meta['slug'] for item in catalog):
        raise build.BuildError(f'articles.json 里已经有 slug「{meta["slug"]}」')
    path = root/'content'/f'{meta["slug"]}.md'
    template = (templates/f'{meta["type"]}.md').read_text(encoding='utf-8').replace('\r\n', '\n')
    try:
        # 'x'：同名文件已存在就停下，不覆盖已有文章。
        with open(path, 'x', encoding='utf-8', newline='') as file:
            file.write(template.replace('\n', newline))
    except FileExistsError:
        raise build.BuildError(f'content/{meta["slug"]}.md 已经存在，没有覆盖') from None
    try:
        build.validate_articles(catalog+[meta], root/'content')
    except BaseException:
        path.unlink()
        raise
    catalog_path.write_bytes((json.dumps(catalog+[meta], ensure_ascii=False, indent=2).replace('\n', newline)+newline).encode('utf-8'))
    return path


def ask(label, default='', check=None):
    while True:
        hint = f'（直接回车用“{default}”）' if default else ''
        value = input(f'{label}{hint}：').strip() or default
        problem = check(value) if check else None
        if not problem:
            return value
        print(f'  {problem}')


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description='新建一篇文章（登记为草稿，不会发布）。')
    parser.add_argument('--slug', help='英文文件名，也是网址的一部分，例如 tomato-egg')
    parser.add_argument('--title', help='文章标题')
    parser.add_argument('--category', help='首页筛选用的分类，例如 编程、做菜')
    parser.add_argument('--type', help='类型：'+build.TYPE_HINT)
    parser.add_argument('--summary', help='首页列表里显示的一句话摘要')
    parser.add_argument('--servings', help='食谱份量，例如“2 人份”（可选）')
    parser.add_argument('--minutes', type=int, help='食谱大约用时，单位分钟（可选）')
    parser.add_argument('--publish', action='store_true', help='不标记草稿，下次构建就发布')
    args = parser.parse_args(argv)

    catalog = json.loads((build.ROOT/'articles.json').read_text(encoding='utf-8'))
    slugs = {item['slug'] for item in catalog}
    categories = list(dict.fromkeys(item['category'] for item in catalog))
    interactive = sys.stdin.isatty()
    missing = [name for name in ('slug', 'title', 'category', 'summary') if not getattr(args, name)]
    if missing and not interactive:
        parser.error('缺少参数：'+'、'.join('--'+name for name in missing))

    slug = args.slug or ask('英文文件名（小写字母、数字、连字符，例如 tomato-egg）', check=lambda v:
                            None if build.SLUG.match(v) and len(v) <= 80 and v not in slugs
                            else '已经有这个名字了' if v in slugs else '只能用小写英文、数字和连字符')
    title = args.title or ask('标题', check=lambda v: None if v else '标题不能为空')
    category = args.category or ask(f'分类（已有：{"、".join(categories)}；也可以写新的）',
                                    check=lambda v: None if v and v != build.ALL else f'分类不能为空，也不能叫“{build.ALL}”')
    guess = 'recipe' if any(word in category for word in ('菜', '食', '烘焙')) else 'post' if category == '生活' else 'tutorial'
    kind = TYPE_NAMES.get(args.type or ask('类型：'+build.TYPE_HINT, build.TYPES[guess][0],
                                           check=lambda v: None if v in TYPE_NAMES else '请输入 '+build.TYPE_HINT+' 之一'))
    if kind is None:
        parser.error('--type 只能是 '+build.TYPE_HINT)
    summary = args.summary or ask('一句话摘要（显示在首页列表里）', check=lambda v: None if v else '摘要不能为空')

    today = date.today().isoformat()
    meta = {'slug': slug, 'title': title, 'category': category, 'type': kind, 'summary': summary,
            'created': today, 'updated': today}
    if not args.publish:
        meta['draft'] = True
    if kind == 'recipe':
        servings = args.servings if args.servings is not None else (ask('份量，例如“2 人份”（可跳过）') if interactive else '')
        minutes = args.minutes
        if minutes is None and interactive:
            text = ask('大约用时几分钟（可跳过）', check=lambda v: None if not v or v.isdigit() else '只写数字，例如 30')
            minutes = int(text) if text else None
        recipe = {key: value for key, value in (('servings', servings), ('minutes', minutes)) if value}
        if recipe:
            meta['recipe'] = recipe

    path = create_article(meta)
    relative = path.relative_to(build.ROOT).as_posix()
    print(f'\n已创建 {relative}（{build.TYPES[kind][0]}模板）')
    if meta.get('draft'):
        print('已登记到 articles.json，标记为草稿 "draft": true，构建时不会发布。')
        print(f'接下来：\n  1. 编辑 {relative}\n  2. 本地预览草稿：python scripts/build.py --drafts，再 python scripts/serve.py'
              '\n  3. 写完后删掉 articles.json 里这篇的 "draft": true，运行 build、check、test_build，再提交')
    else:
        print(f'已登记到 articles.json，下次构建就会发布。编辑 {relative} 后运行 build、check、test_build 再提交。')


if __name__ == '__main__':
    main()
