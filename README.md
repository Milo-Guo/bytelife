# ByteLife

Milo 的笔记：记录我学编程、修电脑时遇到的问题和解决过程，以后也写做菜和生活。

- **阅读网站：** https://milo-guo.github.io/bytelife/
- **交流与纠错：** https://github.com/Milo-Guo/bytelife/discussions
- [迁移记录](MIGRATION.md)

## 已有文章

- [GitHub 项目从下载到部署：dsh-purge 排错、更新、独立备份与公开／私有设置](content/github-project-deployment.md)
- [Colab 实习：计算器、AI 人物检测与 3D 点云完整解析，附复现文件](content/colab-ai-spatial-lab.md)
- [Git 零基础完整教程，附核心命令速查](content/git-basics.md)
- [我的世界 Java 版 Mod 入门](content/minecraft-mod.md)
- [软件装好了却找不到：WindowsApps](content/windowsapps.md)
- [桌面图标变白、消失的排查与恢复](content/desktop-icons.md)

## 以后怎么改文章

### 在网站的写作页里改（推荐）

打开 https://milo-guo.github.io/bytelife/write/ ，或在任意文章底部点 **编辑这篇**。

- 左边是 Markdown 源代码，右边按网站的真实样式实时预览。两边滚动一一对应；点预览里的某一段，光标会跳到对应的源代码行，光标所在的段落在预览里有标记。
- **文章信息**按钮里改标题、分类、类型、摘要、更新日期、草稿和食谱信息。
- 写的内容自动保存在这台电脑的浏览器里，关掉页面也不会丢；按 **Ctrl+S** 存一个版本。
- **版本**按钮里能看到本机保存的版本和 GitHub 上的每次提交，可以逐行对比，也可以恢复成某个版本。
- 手机上用顶部的 **源代码 / 预览** 标签切换。

写完点 **提交**，有两种方式：

1. **连接令牌，一键提交。**在 GitHub 的 **Settings → Developer settings → Fine-grained tokens** 新建一个令牌：Repository access 只选 `bytelife`，Repository permissions 里 **Contents** 设为 **Read and write**，有效期选 30 天左右。把令牌粘贴到写作页即可。令牌只放在这个页面的内存里，刷新或关闭页面就清空，只发给 `api.github.com`。不用了记得在 GitHub 设置里删除。
2. **不连接令牌。**点 **复制正文**，再点 **打开 GitHub**，在 GitHub 的编辑页全选、粘贴、提交。改了文章信息时，页面会把 `articles.json` 里要换的那一项也准备好，照着复制即可。

提交时如果发现这篇在你打开之后又被改过（比如在另一台电脑上改过），写作页不会覆盖，会提示你先在“版本”里对比。每篇文章页底部有 **修改记录**，列出每次提交的日期和说明，可以直接看每次改了什么，或打开当时的版本。

**新建文章**：写作页点 **新建**，填好后按类型生成模板，并标成草稿（提交需要连接令牌）。也可以不用令牌：在 GitHub 打开 **Actions → 新建文章 → Run workflow**，填表后会自动生成草稿并提交，接着在写作页里写正文。

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
python scripts/test_build.py
python scripts/serve.py
```

构建会提示文章数量，检查会显示“检查通过”，安全回归测试最后一行是 `OK`。浏览器打开 `http://localhost:8000/bytelife/`，可测试首页、搜索、配图和目录。停止服务按 `Ctrl+C`。如果找不到 Python，先在终端执行 `py --version`，可用时把命令中的 `python` 换成 `py`。

确认要公开本次修改后，再执行 Git 提交和推送；只在自己的仓库里操作：

```powershell
git status
git add content assets articles.json
git commit -m "更新文章内容"
git push
```

只要不推送，改动就只在本机。失败时先看终端原始错误，别用强制推送覆盖历史。

## 新增文章

推荐用脚本新建，它会按类型套好模板、在 `articles.json` 里登记，并标成草稿：

```powershell
python scripts/new.py
```

按提示填英文文件名、标题、分类、类型和摘要即可（食谱还会问份量和用时，可跳过）。也可以一次写全：

```powershell
python scripts/new.py --slug tomato-egg --title "番茄炒蛋" --category 做菜 --type recipe --summary "十分钟的家常菜" --servings "2 人份" --minutes 15
```

1. 编辑生成的 `content/英文文件名.md`。**不要在正文重复加文章总标题**，网页会从 `articles.json` 生成标题。
2. 写的过程中想看效果：`python scripts/build.py --drafts`，再 `python scripts/serve.py`。草稿页带“草稿 · 未发布”标记。这样构建出来的结果只供本地预览，`check.py` 会提醒你别拿它发布。
3. 写完后，删掉 `articles.json` 里这篇的 `"draft": true`，把 `updated` 改成当天，再运行 `build.py`、`check.py`、`test_build.py`，然后提交。

`articles.json` 每一项的字段：

| 字段 | 说明 |
| --- | --- |
| `slug` | 英文文件名，也是网址：`/bytelife/articles/slug/`。只能用小写字母、数字和连字符，必须等于 Markdown 文件名去掉 `.md`。发布后别改，改了旧链接会失效 |
| `title`、`summary` | 标题和首页上的一句话摘要 |
| `category` | 分类，首页筛选自动生成。用简单的词，例如 编程、Windows、做菜、生活 |
| `type` | 类型：`tutorial`（教程）、`recipe`（食谱）、`post`（随笔）。决定给搜索引擎的结构化数据，食谱还会在页头显示份量和用时 |
| `created`、`updated` | 发布和更新日期，格式 `2026-10-22` |
| `draft` | 可选。`true` 表示草稿，不发布、不进搜索和 RSS |
| `recipe` | 可选，只用于食谱：`{"servings": "2 人份", "minutes": 15}` |
| `note` | 可选。首页这篇下面显示一条更新提示并直达某一节：`{"date": "2026-10-22", "text": "这次改了什么", "anchor": "mc-section-09"}` |
| `source` 等 | `source`、`source_topic_id`、`source_posts` 是迁移旧文用的，新文章不用写 |

食谱正文里，`## 用料` 和 `## 做法` 两节下的列表会自动整理成食谱结构化数据（每行一项），所以这两节请用列表写。模板在 `scripts/templates/`，可以按自己的习惯改。

`content/` 里没写进 `articles.json` 的 Markdown 也不会发布。

### 写法约定

- **图片和图注**：图片单独一段，下一段整段用斜体写图注（`*图注*`），网页会排成带说明的配图，可点开放大。
- **提示框**：普通引用 `>` 显示为说明框。需要强调时用 GitHub 同款写法，GitHub 预览和网站效果一致：

  ```markdown
  > [!WARNING]
  > 先备份世界存档。
  ```

  可用 `NOTE`（说明）、`TIP`（提示）、`IMPORTANT`（重要）、`WARNING`（注意）、`CAUTION`（警告）。
- **章节直达**：二、三级标题会自动生成锚点。需要固定、好记的地址时，在标题前一行写 `<a name="mc-section-09"></a>`，以后改标题文字也不会失效。
- **原生 HTML**：只保留 `a`、`div`、`span`、`p`、`kbd`、`mark`、`sup`、`sub`、`details`、`summary`、`img` 等排版标签，以及 `href`、`src`、`id`、`title`、`alt` 等少数属性。`<script>`、`<iframe>`、`style`、`onclick` 这类会在构建时去掉，链接只接受 `http`、`https`、`mailto` 和站内地址。代码块里的 HTML、JavaScript 原样显示，不会执行。
- **图片放仓库里**：网页的安全策略只允许加载本站文件，外链图片显示不出来，`check.py` 也会报错。

## 结构与保留范围

- `content/`：当前文章，优先修改这里。
- `archive/`：旧版 PCL 原文存档，保留历史，不进入全文搜索，也不让搜索引擎收录。
- `assets/`：样式、脚本和本地图片，不依赖原论坛的图片服务器。
- `scripts/`：构建、校验和本地预览工具。只使用一个 Markdown 渲染依赖，没有前端框架。`test_build.py` 是安全回归测试，`new.py` 新建文章，`templates/` 是三种文章模板。
- `.github/workflows/pages.yml`：GitHub Pages 自动发布。构建任务只读仓库，发布任务只拿 Pages 权限；PR 只构建检查、不发布。
- `.github/workflows/new-article.yml`：在 GitHub 网页上填表新建文章草稿。
- `.github/dependabot.yml`：每月检查发布动作和 Python 依赖的新版本，开 PR 供确认。
- `assets/editor.js`、`assets/editor.css`：写作页。`assets/vendor/` 是写作页预览用的 markdown-it（和构建用的 markdown-it-py 同一套规则），来自 npm 官方包，Dependabot 不会自动升级它。升级时在临时文件夹运行 `npm pack markdown-it@新版本`，取出 `dist/markdown-it.min.js` 换掉旧文件，并在 `scripts/build.py` 里改文件名和 `VENDOR_HASHES` 里的 SHA-256。
- `_site/`：构建生成，每次构建会整个重建，不要手改。

## 安全与恢复

- 网站没有后台和登录，访客只能输入搜索词。搜索在浏览器本地完成，不发给任何服务，也没有统计和追踪脚本。
- 写作页是唯一会连接外部服务的页面：它只能访问 `api.github.com`，预览里的原生 HTML 一律按文字显示、不执行。任何人都能打开写作页，但没有对仓库有写权限的令牌就提交不了。令牌只在内存里，建议用只授权 `bytelife`、只给 Contents 读写、30 天过期的细粒度令牌。
- “新建文章”工作流需要写仓库的权限，只有对仓库有写权限的人能运行；表单内容只通过环境变量交给脚本，`test_build.py` 会检查以后修改时没有把输入直接拼进命令。
- 每个页面用 `<meta>` 声明内容安全策略（CSP）：只允许本站的脚本、样式、图片和索引，只放行一段主题初始化脚本（按哈希），并开启 Trusted Types。GitHub Pages 不能自定义响应头，所以防点击劫持的 `frame-ancestors` 等只能写在响应头里的项目目前无法设置。
- 发布流程里的官方动作固定到完整提交 SHA，Python 依赖固定版本和哈希；升级时同时改版本注释和 SHA。
- **文章改错了**：在 GitHub 打开该文件的 **History**，找到改错前的版本复制回来；或在本机执行 `git revert <提交号>` 再推送，会新增一个撤销提交，历史保留。
- **发布出错了**：先在本机 `git revert` 出问题的提交并推送，网站会按上一版重新发布。急用时也可以在 **Actions** 里打开上一次成功的运行，点 **Re-run all jobs** 重新发布那一版（以 GitHub 页面当时的提示为准）；这只是临时回到旧内容，下一次推送仍会发布 `main` 的最新状态。不要用强制推送改写 `main` 的历史。

旧论坛的数据库备份、账户数据、私信和管理内容不在这个公开仓库。原论坛目前仍保留，迁移没有取消其账户或删除原主题。

网站目前是文章站：GitHub Discussions 提供交流，不会自动继承 Discourse 的用户、登录状态和通知系统。4 篇公开教程的 5 楼内容已迁入；自己的原文和后续改动保留在 Git 历史中。

本站有 `sitemap.xml`。先前给旧论坛做的 Google Search Console 所有权验证不会自动转移到这个新地址；如需管理新站收录，要另加 `https://milo-guo.github.io/bytelife/` 资源。发布不等于立刻被搜索引擎收录。

文章内容与原有图片的权利归原作者；转载的项目帮助截图保留原出处。当前没有把整站内容另行改成宽松开源许可证。
