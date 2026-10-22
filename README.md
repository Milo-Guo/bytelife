# ByteLife

把走过的路写清楚。这里放我的学习经验、电脑排障和生活记录。

- **阅读网站：** https://milo-guo.github.io/bytelife/
- **交流与纠错：** https://github.com/Milo-Guo/bytelife/discussions
- [迁移记录](MIGRATION.md)

## 已有文章

- [Git 零基础完整教程，附核心命令速查](content/git-basics.md)
- [我的世界 Java 版 Mod 入门](content/minecraft-mod.md)
- [软件装好了却找不到：WindowsApps](content/windowsapps.md)
- [桌面图标变白、消失的排查与恢复](content/desktop-icons.md)

## 以后怎么改文章

### 直接在 GitHub 网页改

1. 打开本仓库，点 `content`，再点要改的 `.md` 文件。
2. 点右上角铅笔 **Edit this file**。看不到时先登录自己的 GitHub 账户。
3. 编辑文字。上面的 **Preview** 可以看 Markdown 排版。
4. 点 **Commit changes**，填写这次改了什么，再确认提交。提交到 `main` 后，**Actions → 发布 ByteLife** 会自动更新网站。
5. 出现绿色勾，再打开阅读网站刷新。若失败，打开那次运行，点红色步骤看原因。

图片放在 `assets/images/` 对应文章目录。Markdown 用相对路径，例如 `![说明](../assets/images/minecraft-mod/图片.png)`，这样 GitHub 原文和网站都能显示。

### 在本机用 VS Code 改

1. 用 VS Code 打开这个仓库文件夹。最初迁移位置为 `C:\Users\guo\Documents\ByteLife-GitHub`。
2. 在 `content` 里编辑文章，保存后，打开 **Terminal → New Terminal**。
3. 首次在该电脑安装 Python 3.10 或以上，然后在终端执行：

```powershell
python -m pip install -r requirements.txt
python scripts/build.py
python scripts/check.py
python scripts/serve.py
```

构建会提示文章数量，检查会显示“检查通过”。浏览器打开 `http://localhost:8000/bytelife/`，可测试首页、搜索、配图和目录。停止服务按 `Ctrl+C`。如果找不到 Python，先在终端执行 `py --version`，可用时把命令中的 `python` 换成 `py`。

确认要公开本次修改后，再执行 Git 提交和推送；只在自己的仓库里操作：

```powershell
git status
git add content assets articles.json
git commit -m "更新文章内容"
git push
```

只要不推送，改动就只在本机。失败时先看终端原始错误，别用强制推送覆盖历史。

## 新增文章

1. 在 `content/` 新建一个英文文件名，例如 `cooking-notes.md`，正文用 Markdown 写。**不要在正文重复加文章总标题**，网页会从目录配置生成标题。
2. 在 `articles.json` 数组中新增一项，设置 `slug`、`title`、`category`、`summary`、`created`、`updated`。日期格式 `2026-10-22`；`slug` 必须等于 Markdown 文件名去掉 `.md`。
3. `source`、`source_topic_id`、`source_posts` 是迁移旧文用的，新文章可省略。
4. 执行构建和检查，再提交。首页、分类、全文搜索、RSS 与站点地图会一并生成。

## 结构与保留范围

- `content/`：当前文章，优先修改这里。
- `archive/`：旧版 PCL 原文存档，保留历史，不进入全文搜索，也不让搜索引擎收录。
- `assets/`：样式、脚本和本地图片，不依赖原论坛的图片服务器。
- `scripts/`：构建、校验和本地预览工具。只使用一个 Markdown 渲染依赖，没有前端框架。
- `.github/workflows/pages.yml`：GitHub Pages 自动发布。

旧论坛的数据库备份、账户数据、私信和管理内容不在这个公开仓库。原论坛目前仍保留，迁移没有取消其账户或删除原主题。

网站目前是文章站：GitHub Discussions 提供交流，不会自动继承 Discourse 的用户、登录状态和通知系统。4 篇公开教程的 5 楼内容已迁入；自己的原文和后续改动保留在 Git 历史中。

本站有 `sitemap.xml`。先前给旧论坛做的 Google Search Console 所有权验证不会自动转移到这个新地址；如需管理新站收录，要另加 `https://milo-guo.github.io/bytelife/` 资源。发布不等于立刻被搜索引擎收录。

文章内容与原有图片的权利归原作者；转载的项目帮助截图保留原出处。当前没有把整站内容另行改成宽松开源许可证。
