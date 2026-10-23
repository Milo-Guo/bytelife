"""Colab 课堂启动器：先检查服务，再创建 ngrok 隧道；不停止其他进程。"""
from pathlib import Path
import argparse
import getpass
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request


def stop_app(process, tunnel, log_file):
    """只关闭由本启动器返回的服务和隧道。"""
    from pyngrok import ngrok
    try:
        ngrok.disconnect(tunnel.public_url)
    finally:
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
        finally:
            log_file.close()
    print("本次应用和隧道已关闭。")


def start_app(app, port=8501):
    """返回进程、隧道、日志句柄，便于切换课题时精确关闭。"""
    from pyngrok import ngrok
    app_path = Path(app).resolve()
    if not app_path.is_file() or app_path.suffix != ".py":
        raise FileNotFoundError(f"找不到 Python 文件：{app_path}")
    # 防止把旧应用误当作本次启动成功，也不自动结束占用端口的程序
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            raise RuntimeError(f"{port} 端口已占用。先关闭上一课的服务，或换一个端口。")
    token = getpass.getpass("粘贴自己的 ngrok authtoken（输入不显示）：").strip()
    if not token:
        raise ValueError("没有输入 ngrok authtoken。")
    ngrok.set_auth_token(token)
    del token
    log_path = (Path("/content") if Path("/content").is_dir() else app_path.parent) / "logs.txt"
    log_file = log_path.open("w", encoding="utf-8")
    process = None
    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", str(app_path),
             f"--server.port={port}", "--server.address=127.0.0.1", "--server.headless=true"],
            cwd=app_path.parent, stdout=log_file, stderr=subprocess.STDOUT,
        )
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"Streamlit 提前退出，请查看 {log_path}")
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1) as response:
                    if response.status == 200:
                        break
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(0.5)
        else:
            raise TimeoutError(f"等待 Streamlit 超时，请查看 {log_path}")
        tunnel = ngrok.connect(addr=f"http://127.0.0.1:{port}", proto="http")
        print("Streamlit 网页服务已响应。请打开下面的 HTTPS 地址：")
        print(tunnel.public_url)
        print(f"模型加载或应用代码报错请查看网页与 {log_path}")
        return process, tunnel, log_file
    except Exception:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        log_file.close()
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", help="要运行的 .py 文件")
    parser.add_argument("--port", type=int, default=8501)
    args = parser.parse_args()
    course_process, course_tunnel, course_log = start_app(args.app, args.port)
