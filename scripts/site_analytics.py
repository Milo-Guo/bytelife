"""可选的 Umami Cloud 接入；公开网站 ID 为空时不加载统计。"""
from html import escape
import json
from pathlib import Path
import re


UMAMI_SCRIPT = 'https://cloud.umami.is/script.js'
UMAMI_COLLECT_ORIGIN = 'https://gateway.umami.is'
UMAMI_DOMAIN = 'milo-guo.github.io'
WEBSITE_ID = re.compile(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z')


def load_website_id(path):
    """只接收公开网站 ID，不允许把任意脚本或账户密钥带入页面。"""
    path = Path(path)
    if not path.exists():
        return ''
    try:
        config = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise ValueError('analytics.json 无法读取，请检查文件编码和 JSON 格式') from error
    if not isinstance(config, dict) or set(config) - {'website_id'}:
        raise ValueError('analytics.json 只接受 website_id 字段')
    website_id = config.get('website_id', '')
    if not isinstance(website_id, str) or (website_id and not WEBSITE_ID.fullmatch(website_id)):
        raise ValueError('analytics.json 的 website_id 应留空，或填写 Umami 生成的 UUID')
    return website_id.lower()


def tracking_attributes(website_id):
    if not isinstance(website_id, str) or not WEBSITE_ID.fullmatch(website_id):
        raise ValueError('Umami 网站 ID 不是合法 UUID')
    return {
        'defer': None,
        'src': UMAMI_SCRIPT,
        'data-website-id': website_id.lower(),
        # 只累计线上浏览，避免本机测试混入访问量；文章锚点不应成为独立页面。
        'data-domains': UMAMI_DOMAIN,
        'data-exclude-search': 'true',
        'data-exclude-hash': 'true',
    }


def tracking_markup(website_id):
    attrs = tracking_attributes(website_id)
    return '<script' + ''.join(
        f' {name}' if value is None else f' {name}="{escape(value, quote=True)}"'
        for name, value in attrs.items()
    ) + '></script>'


def is_tracking_script(attrs):
    """检查完整属性集合，防止额外的发送地址等属性借白名单改变行为。"""
    try:
        expected = tracking_attributes(attrs.get('data-website-id'))
    except (TypeError, ValueError):
        return False
    return (set(attrs) == set(expected)
            and attrs.get('defer') in (None, '')
            and all(attrs.get(key) == value for key, value in expected.items() if key != 'defer'))


def tracking_csp(csp):
    """只放开官方统计脚本和收集接口，其余安全策略保持原样。"""
    additions = {'script-src': UMAMI_SCRIPT, 'connect-src': UMAMI_COLLECT_ORIGIN}
    directives = [part.strip().split() for part in csp.split(';') if part.strip()]
    found = set()
    for directive in directives:
        name = directive[0]
        if name in additions:
            found.add(name)
            if additions[name] not in directive[1:]:
                directive.append(additions[name])
    if found != set(additions):
        raise ValueError('统计接入需要现有 CSP 声明 script-src 和 connect-src')
    return '; '.join(' '.join(directive) for directive in directives)
