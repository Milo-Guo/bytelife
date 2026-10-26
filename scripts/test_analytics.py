"""统计接入回归测试：公开页面可统计，写作与草稿不加载统计，外部资源白名单不可借用。

运行：python scripts/test_analytics.py
"""
from html import escape
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
import check  # noqa: E402
import site_analytics as analytics  # noqa: E402

WEBSITE_ID = '12345678-1234-4abc-8def-123456789abc'


def parse(html):
    page = check.Page()
    page.feed(html)
    page.close()
    return page


def directives(csp):
    return {parts[0]: set(parts[1:]) for part in csp.split(';') if (parts := part.split())}


def script_markup(attrs):
    return '<script'+''.join(f' {name}' if value is None else f' {name}="{escape(value, quote=True)}"'
                            for name, value in attrs.items())+'></script>'


def test_page(script, csp=None, writing=False):
    csp = analytics.tracking_csp(build.CSP) if csp is None else csp
    robots = '<meta name="robots" content="noindex,follow">' if writing else ''
    return parse(f'<meta http-equiv="Content-Security-Policy" content="{escape(csp, quote=True)}">{robots}{script}')


class ConfigurationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = Path(self.tmp.name)/'analytics.json'

    def write_config(self, data):
        self.config.write_text(json.dumps(data), encoding='utf-8')

    def test_missing_and_empty_configuration_disable_tracking(self):
        self.assertEqual(analytics.load_website_id(self.config), '')
        for data in ({}, {'website_id': ''}):
            with self.subTest(data=data):
                self.write_config(data)
                self.assertEqual(analytics.load_website_id(self.config), '')

    def test_valid_id_is_normalized(self):
        self.write_config({'website_id': WEBSITE_ID.upper()})
        self.assertEqual(analytics.load_website_id(self.config), WEBSITE_ID)

    def test_malformed_and_unexpected_configuration_is_rejected(self):
        for data in (None, [], {'website_id': None}, {'website_id': 42}, {'website_id': 'not-a-uuid'},
                     {'website_id': WEBSITE_ID+'?x=1'}, {'website_id': ' '+WEBSITE_ID},
                     {'website_id': WEBSITE_ID, 'src': 'https://example.com/script.js'}):
            with self.subTest(data=data):
                self.write_config(data)
                with self.assertRaises(ValueError):
                    analytics.load_website_id(self.config)
        self.config.write_text('{', encoding='utf-8')
        with self.assertRaises(ValueError):
            analytics.load_website_id(self.config)


class PageIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.state = patch.dict(build.SITE_STATE, {'analytics_website_id': ''})
        self.state.start()
        self.addCleanup(self.state.stop)

    def test_unconfigured_page_keeps_original_csp(self):
        page = parse(build.shell('测试', '描述', '正文'))
        self.assertEqual(page.csp, build.CSP)
        self.assertFalse(any(analytics.is_tracking_script(attrs) for attrs, _ in page.scripts))
        errors = []
        check.page_rules(check.OUT/'index.html', page, errors)
        self.assertEqual(errors, [])

    def test_configured_home_has_one_valid_tracker(self):
        build.SITE_STATE['analytics_website_id'] = WEBSITE_ID
        page = parse(build.shell('测试', '描述', '正文'))
        self.assertEqual(sum(analytics.is_tracking_script(attrs) for attrs, _ in page.scripts), 1)
        self.assertEqual(page.csp, analytics.tracking_csp(build.CSP))
        errors = []
        check.page_rules(check.OUT/'index.html', page, errors)
        self.assertEqual(errors, [])

    def test_configured_editor_keeps_original_editor_csp(self):
        build.SITE_STATE['analytics_website_id'] = WEBSITE_ID
        page = parse(build.shell('写作', '描述', '正文', 'write/', noindex=True,
                                 page='page editor-page', csp=build.EDITOR_CSP))
        self.assertEqual(page.csp, build.EDITOR_CSP)
        self.assertFalse(any(analytics.is_tracking_script(attrs) for attrs, _ in page.scripts))
        self.assertNotIn(analytics.UMAMI_COLLECT_ORIGIN, page.csp)
        errors = []
        check.page_rules(check.OUT/'write/index.html', page, errors)
        self.assertEqual(errors, [])

    def test_404_and_draft_do_not_track(self):
        build.SITE_STATE['analytics_website_id'] = WEBSITE_ID
        draft = {'title': '草稿', 'summary': '描述', 'created': '2026-10-01',
                 'updated': '2026-10-01', 'draft': True}
        for relative, article in (('404.html', None), ('articles/draft/', draft)):
            with self.subTest(relative=relative):
                page = parse(build.shell('测试', '描述', '正文', relative, article, noindex=True))
                self.assertEqual(page.csp, build.CSP)
                self.assertFalse(any(analytics.is_tracking_script(attrs) for attrs, _ in page.scripts))


class CspTest(unittest.TestCase):
    def test_tracking_adds_only_exact_official_addresses(self):
        original = directives(build.CSP)
        enhanced = directives(analytics.tracking_csp(build.CSP))
        expected = {name: set(sources) for name, sources in original.items()}
        expected['script-src'].add(analytics.UMAMI_SCRIPT)
        expected['connect-src'].add(analytics.UMAMI_COLLECT_ORIGIN)
        self.assertEqual(enhanced, expected)
        self.assertEqual(enhanced['require-trusted-types-for'], {"'script'"})
        self.assertEqual(enhanced['trusted-types'], {"'none'"})
        self.assertNotIn('unsafe-', analytics.tracking_csp(build.CSP))
        self.assertEqual(analytics.tracking_csp(analytics.tracking_csp(build.CSP)), analytics.tracking_csp(build.CSP))

    def test_checker_requires_script_and_collection_permission(self):
        valid = analytics.tracking_csp(build.CSP)
        policies = (build.CSP, valid.replace(analytics.UMAMI_SCRIPT, analytics.UMAMI_SCRIPT+'.evil.invalid'),
                    valid.replace(analytics.UMAMI_COLLECT_ORIGIN, analytics.UMAMI_COLLECT_ORIGIN+'.evil.invalid'),
                    valid+"; script-src-elem 'self'", valid.replace(analytics.UMAMI_SCRIPT, 'https://cloud.umami.is'),
                    valid.replace(analytics.UMAMI_SCRIPT, analytics.UMAMI_SCRIPT+' https:'),
                    valid.replace(analytics.UMAMI_COLLECT_ORIGIN, analytics.UMAMI_COLLECT_ORIGIN+' https:'))
        for csp in policies:
            with self.subTest(csp=csp):
                errors = []
                check.page_rules(check.OUT/'index.html', test_page(analytics.tracking_markup(WEBSITE_ID), csp), errors)
                self.assertTrue(errors)

    def test_disabled_page_cannot_retain_tracking_permissions(self):
        for writing in (False, True):
            with self.subTest(writing=writing):
                errors = []
                path = check.OUT/('write/index.html' if writing else 'index.html')
                check.page_rules(path, test_page('', writing=writing), errors)
                self.assertTrue(any('不应放开统计 CSP' in error for error in errors))


class ResourceWhitelistTest(unittest.TestCase):
    def attributes(self):
        return parse(analytics.tracking_markup(WEBSITE_ID)).scripts[0][0]

    def rule_errors(self, page, writing=False):
        errors = []
        path = check.OUT/('write/index.html' if writing else 'index.html')
        check.page_rules(path, page, errors)
        check.link_rules(path, page, {}, errors)
        return errors

    def test_only_fully_valid_tracking_script_is_allowed(self):
        attrs = self.attributes()
        self.assertTrue(analytics.is_tracking_script(attrs))
        self.assertEqual(attrs['data-domains'], analytics.UMAMI_DOMAIN)
        self.assertEqual(attrs['data-exclude-search'], 'true')
        self.assertEqual(attrs['data-exclude-hash'], 'true')
        self.assertEqual(self.rule_errors(test_page(script_markup(attrs))), [])

    def test_extra_attributes_and_changed_safety_options_are_rejected(self):
        original = self.attributes()
        for changes in ({'data-host-url': 'https://example.com'}, {'data-auto-track': 'false'},
                        {'onload': 'alert(1)'}, {'data-domains': 'example.com'},
                        {'data-exclude-search': 'false'}, {'data-exclude-hash': 'false'},
                        {'data-website-id': 'not-a-uuid'}, {'defer': 'false'}):
            with self.subTest(changes=changes):
                attrs = original | changes
                self.assertFalse(analytics.is_tracking_script(attrs))
                errors = self.rule_errors(test_page(script_markup(attrs)))
                self.assertTrue(any('外部脚本' in error for error in errors))
                self.assertTrue(any('外部资源' in error for error in errors))

    def test_lookalike_urls_and_query_parameters_are_rejected(self):
        urls = ('https://cloud.umami.is.evil.invalid/script.js', 'https://cloud.umami.is@evil.invalid/script.js',
                analytics.UMAMI_SCRIPT+'?host=evil', '//cloud.umami.is/script.js',
                'http://cloud.umami.is/script.js', analytics.UMAMI_SCRIPT+'#tracker')
        for src in urls:
            with self.subTest(src=src):
                attrs = self.attributes() | {'src': src}
                self.assertFalse(analytics.is_tracking_script(attrs))
                self.assertTrue(self.rule_errors(test_page(script_markup(attrs))))

    def test_valid_script_does_not_whitelist_invalid_script_with_same_url(self):
        script = analytics.tracking_markup(WEBSITE_ID)
        page = test_page(script+script_markup(self.attributes() | {'data-host-url': 'https://example.com'}))
        errors = []
        check.link_rules(check.OUT/'index.html', page, {}, errors)
        self.assertTrue(any('外部资源' in error for error in errors))

    def test_valid_script_does_not_whitelist_external_images(self):
        page = test_page(analytics.tracking_markup(WEBSITE_ID)+f'<img src="{analytics.UMAMI_SCRIPT}">')
        self.assertTrue(any('外部资源' in error for error in self.rule_errors(page)))

    def test_duplicate_attributes_and_scripts_are_rejected(self):
        script = analytics.tracking_markup(WEBSITE_ID)
        repeated_attr = script.replace('<script ', '<script data-exclude-search="false" ', 1)
        for markup in (script+script, repeated_attr):
            with self.subTest(markup=markup):
                self.assertTrue(self.rule_errors(test_page(markup)))

    def test_writer_rejects_even_a_valid_tracker(self):
        errors = self.rule_errors(test_page(analytics.tracking_markup(WEBSITE_ID), writing=True), writing=True)
        self.assertTrue(any('写作页不允许加载访问统计' in error for error in errors))


if __name__ == '__main__':
    unittest.main(verbosity=2)
