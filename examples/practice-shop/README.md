# 商品管理练习：先在自己的电脑上跑起来

这是配套补课示例，不是老师原项目。用于观察页面、接口、数据库怎样协作。支持新增、查询、修改和上下架；没有实现删除、用户账户、支付等完整商城功能。

## Windows 第一次启动

1. 安装 Python 3.10 或以上、VS Code，保留安装器中的 `Add Python to PATH`。
2. 解压到自己新建的文件夹，例如 `C:\learn\practice-shop`。不能只打开压缩包里的文件。
3. 在资源管理器打开这个文件夹，地址栏输入 `powershell` 并按回车。
4. 在 PowerShell 逐行执行，哪一步报错就先处理那一步：

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -X utf8 -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -X utf8 scripts\initialize_demo.py
.\.venv\Scripts\python.exe -X utf8 -m uvicorn app.main:app --host 127.0.0.1 --port 8008
```

看到 `Uvicorn running on http://127.0.0.1:8008` 后，保持窗口打开，用 Chrome 或 Edge 访问 `http://127.0.0.1:8008`。不要双击 `index.html` 启动项目。

在 VS Code 用 `File > Open Folder` 打开 `practice-shop`。点 `.env`，将 `ADMIN_KEY=` 后面的值复制到页面的管理员口令框，然后新增一件练习商品。不要把 `.env` 或含有该口令的截图发到网上。

停止：在运行后端的 PowerShell 按 `Ctrl+C`。下次启动只执行上面的最后一行，不必重新安装。

## 文件在哪里

- `app/static/index.html`：浏览器页面。
- `app/static/style.css`：页面样式。
- `app/static/app.js`：按钮和接口调用。
- `app/main.py`：接口、参数校验、数据库操作。
- `data/shop.db`：第一次运行后生成的 SQLite 数据库；重启保留数据。
- `.env`：初始化后生成的本地口令；不要上传。
- `requirements.txt`：Python 依赖清单。
- `Dockerfile`、`compose.yaml`：可选的 Docker 部署配置。
- `compose.mysql.yaml`：另一套可选的 MySQL + Redis 配置。不要同时运行两套配置，它们都使用本机 8008 端口。
- `deploy/`：Ubuntu + systemd + Nginx 的部署示例。

## 接口文档

打开 `http://127.0.0.1:8008/docs`。展开 `GET /api/products`，点 `Try it out`，再点 `Execute`。实际执行成功会在 `Server response` 下显示 `200` 和商品数据。

新增和修改需要点 `Authorize`，填入本机 `.env` 的 `ADMIN_KEY`。截图前要收起授权信息和可能包含口令的 Curl 内容。

## Docker（可选）

先完成本机练习，再安装并启动 Docker Desktop。项目目录中已有 `.env` 后执行：

```powershell
docker version
docker compose version
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

浏览器仍打开 `http://127.0.0.1:8008`。先按 `Ctrl+C` 停止原来的 Python 后端，避免端口冲突。

```powershell
docker compose logs --tail 80 app
docker compose stop
docker compose start
```

SQLite 容器版使用独立命名卷，不会自动读取本机 `data/shop.db`。数据为两套独立练习记录。

体验 MySQL + Redis 前先停止上面这套，再运行：

```powershell
docker compose -f compose.mysql.yaml config --quiet
docker compose -f compose.mysql.yaml up -d --build
docker compose -f compose.mysql.yaml ps
```

停止、看日志时也必须保留 `-f compose.mysql.yaml`。MySQL 是独立数据库，不会自动迁移 SQLite 数据。Redis 是可选缓存，数据库仍是商品记录的来源。

## 验证范围

本机已实际验证 Python + SQLite 的页面和接口；Docker、MySQL、Redis、Ubuntu 服务器示例没有实际启动验证。Compose 文件做了结构校验，不能等同于容器运行测试。

接口自检使用临时数据库，不改现有商品：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pip install httpx
.\.venv\Scripts\python.exe -X utf8 scripts\check_api.py
```

这只是教学样例。对公网仅通过 HTTPS 使用管理员口令；正式多人系统还需要独立账户、角色权限、限流、审计与备份。
