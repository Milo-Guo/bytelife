"""本地保留 /bytelife/ 子路径，和线上 Pages 的链接行为一致。只监听本机 127.0.0.1。"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from urllib.parse import urlsplit

OUT = Path(__file__).resolve().parent.parent/'_site'


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # 本地改完样式刷新就能看到；线上缓存由 GitHub Pages 决定。
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def do_GET(self):
        if self.path == '/':
            self.send_response(302)
            self.send_header('Location', '/bytelife/')
            self.end_headers()
            return
        if not urlsplit(self.path).path.startswith('/bytelife/'):
            self.send_error(404)
            return
        self.path = self.path[len('/bytelife'):]
        super().do_GET()

    def list_directory(self, path):
        # 和 Pages 一样，不列出目录内容。
        self.send_error(404)

    def send_error(self, code, message=None, explain=None):
        page = OUT/'404.html'
        if code != 404 or not page.exists():
            return super().send_error(code, message, explain)
        body = page.read_bytes()
        self.send_response(404)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)


if __name__ == '__main__':
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    if not (OUT/'index.html').exists():
        raise SystemExit('还没有构建。先运行 python scripts/build.py')
    print('本地预览：http://localhost:8000/bytelife/；停止请按 Ctrl+C', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 8000), partial(Handler, directory=str(OUT))).serve_forever()
