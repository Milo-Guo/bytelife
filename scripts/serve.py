"""本地保留 /bytelife/ 子路径，和线上 Pages 的链接行为一致。"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

OUT = Path(__file__).resolve().parent.parent/'_site'


class Handler(SimpleHTTPRequestHandler):
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


if __name__ == '__main__':
    if not (OUT/'index.html').exists():
        raise SystemExit('还没有构建。先运行 python scripts/build.py')
    print('本地预览：http://localhost:8000/bytelife/；停止请按 Ctrl+C')
    ThreadingHTTPServer(('127.0.0.1', 8000), partial(Handler, directory=str(OUT))).serve_forever()
