"""在临时数据库中检查接口，不改动读者的商品数据。"""

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

with TemporaryDirectory(prefix="practice-shop-check-") as temporary:
    os.environ.update(DATA_DIR=temporary, DB_KIND="sqlite", ADMIN_KEY="temporary-test-key", REDIS_URL="")
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        assert client.get("/api/health").json()["status"] == "ok"
        assert client.get("/").status_code == 200
        assert client.get("/assets/app.js").status_code == 200
        assert client.get("/openapi.json").status_code == 200
        initial = client.get("/api/products").json()["data"]["total"]
        value = {"name": "测试商品", "price_cents": 1990, "stock": 8, "is_published": True}
        assert client.post("/api/products", json=value).status_code == 401
        headers = {"X-Admin-Key": "temporary-test-key"}
        response = client.post("/api/products", json=value, headers=headers)
        assert response.status_code == 201, response.text
        product_id = response.json()["data"]["id"]
        assert client.get("/api/products").json()["data"]["total"] == initial + 1
        assert client.get("/api/products", params={"search": "测试商品"}).json()["data"]["total"] == 1
        value.update(stock=3, is_published=False)
        assert client.put(f"/api/products/{product_id}", json=value, headers=headers).status_code == 200
        assert client.get("/api/products", params={"search": "测试商品"}).json()["data"]["items"][0]["stock"] == 3
        assert client.get("/api/products?page=0").status_code == 422
        value["price_cents"] = -1
        assert client.post("/api/products", json=value, headers=headers).status_code == 422
        assert client.put("/api/products/999999", json={"name": "不存在", "price_cents": 1, "stock": 1}, headers=headers).status_code == 404
        assert client.get("/api/products", params={"search": "' OR 1=1 --"}).json()["data"]["total"] == 0
    # 应用关闭后重新打开，验证记录真正保存在数据库里。
    with TestClient(app) as client:
        assert client.get("/api/products").json()["data"]["total"] == initial + 1
    print("通过：页面、健康检查、接口文档、查询、新增、修改、权限、参数校验、重启后数据保留。")
