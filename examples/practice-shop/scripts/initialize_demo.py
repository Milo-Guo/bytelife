"""准备练习配置，保留已经存在的配置文件。"""

import secrets
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

root = Path(__file__).resolve().parents[1]
target = root / ".env"
if target.exists():
    print("已有 .env，保留原配置。请用编辑器查看 ADMIN_KEY。")
else:
    text = (root / ".env.example").read_text(encoding="utf-8")
    for name in ("ADMIN_KEY", "MYSQL_PASSWORD", "MYSQL_ROOT_PASSWORD"):
        text = text.replace(f"{name}=\n", f"{name}={secrets.token_urlsafe(24)}\n")
    target.write_text(text, encoding="utf-8")
    print("已生成 .env。管理员口令保存在 ADMIN_KEY 中，请在编辑器里查看。")
print("配置仅用于本地练习，请勿把 .env 上传到 GitHub。")
