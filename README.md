# ByteLife

Milo 的笔记：记录我学编程、修电脑时遇到的问题和解决过程，以后也写做菜和生活。

- **阅读网站：** https://milo-guo.github.io/bytelife/
- **交流与纠错：** https://github.com/Milo-Guo/bytelife/discussions
- [迁移记录](MIGRATION.md)

## 已有文章

- [AI 编程：需求文档、验收标准与架构设计，附实机图和练习文件](content/requirements-and-architecture.md)
- [AI 开发先定规则：CLAUDE.md、AGENTS.md 与六阶段流程，附可复制模板](content/ai-development-rules.md)
- [技术栈实机入门：启动商品项目与部署，附 11 张截图和源码](content/full-stack-practice.md)
- [技术栈全景图：零基础概念与完整课程复盘](content/full-stack-overview.md)
- [GitHub 项目从下载到部署：dsh-purge 排错、更新、独立备份与公开／私有设置](content/github-project-deployment.md)
- [Colab 实习：计算器、AI 人物检测与 3D 点云完整解析，附复现文件](content/colab-ai-spatial-lab.md)
- [Git 零基础完整教程，附核心命令速查](content/git-basics.md)
- [我的世界 Java 版 Mod 入门](content/minecraft-mod.md)
- [软件装好了却找不到：WindowsApps](content/windowsapps.md)
- [桌面图标变白、消失的排查与恢复](content/desktop-icons.md)

## 首页阅读与工具

- 电脑上左侧是工具栏，右侧是单列文章；手机点“阅读与工具”展开侧栏内容。
- 点文章旁的书签按钮收藏，左侧“我的收藏”可以和全文搜索、分类一起使用。
- 阅读文章后，首页“继续阅读”会回到上次阅读的章节。收藏和阅读位置只保存在当前浏览器，不会跨设备同步；清理浏览器网站数据后会清除。
- JSON 格式化和时间戳转换点开即可用，输入只在当前浏览器内处理，不上传，也不持久保存。时间戳工具显示设备本地时间和 UTC；Git 命令速查直达现有教程。
- 首页介绍下方的“正在折腾”文字放在根目录 `home.json` 的 `now` 字段里，最多 200 字。改成空字符串就隐藏，后续和文章一样构建、提交后发布。
- “最近更新”从文章日期自动生成，不用单独维护。

## 访问统计后台

可选接入 [Umami Cloud](https://cloud.umami.is/) 免费统计后台，查看浏览量、访客数、来源、国家或地区、热门文章和回访留存。统计数据在登录后的 Umami 后台查看。

根目录 `analytics.json` 已填入 ByteLife 的公开网站 ID，构建并发布后启用；将 `website_id` 清空再发布即可停用。完整注册、启用、查看报表和排错步骤见 [访问统计说明](docs/访问统计.md)。

写作页不加载统计脚本，本地预览也不累计访问。接入前的访问记录无法补统计。

## 以后怎么改文章

### 在网站的写作页里改（推荐）

打开 https://milo-guo.github.io/bytelife/write/ ，或在任意文章底部点 **编辑这篇**。

- 左边是 Markdown 源代码，右边按网站的真实样式实时预览。两边滚动一一对应；点预览里的某一段，光标会跳到对应的源代码行，光标所在的段落在预览里有标记。
- 顶部直接修改**标题、分类标签和摘要**，右侧预览会同步更新；分类可直接输入新名称，例如 `CS`。只改这些信息也能提交，不用改正文。
- **更多设置**里改类型、作者、更新日期、草稿和食谱信息。写正文时可点 **收起信息**，再点 **文章信息** 展开。
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
python scripts/test_analytics.py
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
| `author` | 作者，写 `authors.json` 里的作者 id，例如 `"milo"`；几个人合写写成 `["milo", "ajie"]` |
| `created`、`updated` | 发布和更新日期，格式 `2026-10-22` |
| `draft` | 可选。`true` 表示草稿，不发布、不进搜索和 RSS |
| `recipe` | 可选，只用于食谱：`{"servings": "2 人份", "minutes": 15}` |
| `note` | 可选。首页这篇下面显示一条更新提示并直达某一节：`{"date": "2026-10-22", "text": "这次改了什么", "anchor": "mc-section-09"}` |
| `source` 等 | `source`、`source_topic_id`、`source_posts` 是迁移旧文用的，新文章不用写 |

食谱正文里，`## 用料` 和 `## 做法` 两节下的列表会自动整理成食谱结构化数据（每行一项），所以这两节请用列表写。模板在 `scripts/templates/`，可以按自己的习惯改。

`content/` 里没写进 `articles.json` 的 Markdown 也不会发布。

## 多人写作

作者登记在 `authors.json`，第一位是站长：

```json
[
  {"id": "milo", "name": "Milo Guo", "github": "Milo-Guo", "bio": "一句话简介"},
  {"id": "ajie", "name": "阿杰", "github": "a-jie", "bio": "爱做饭的程序员", "url": "https://example.com/"}
]
```

- `id` 是作者页网址：`/bytelife/authors/ajie/`，只能用小写字母、数字和连字符，定了别改；`name` 是显示的名字；`github`、`bio`、`url`（只接受 https）可选。
- 每位作者都有自己的分区页，列出简介、GitHub 链接和 TA 写过的全部文章（包括合写的）；文章页头的作者名链到分区页，给搜索引擎的结构化数据和 RSS 也带作者。
- 有两位以上作者发表过文章时，首页每篇会显示作者，多出“N 位作者”和页脚“作者”入口（`/bytelife/authors/`）；只有你一个人时这些都不出现。首页搜索作者名能找到 TA 的文章。
- 邀请新作者：先把 TA 加进 `authors.json`，再按需要在仓库 **Settings → Collaborators** 邀请 TA，或让 TA 用 PR 投稿（见“安全与恢复”）。
- 署名怎么来：写作页“文章信息”里勾选作者，新建时默认勾选和所连 GitHub 账号对应的作者；“新建文章”表单不填作者时按运行者的 GitHub 账号自动署名，`authors.json` 里没有这个账号就会报错提醒先登记；`python scripts/new.py --author ajie` 指定作者。

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

- 网站本身没有登录服务。搜索词、JSON 与时间戳工具输入都在浏览器本地处理，没有添加这些输入的上报；收藏和阅读位置保存在当前浏览器。访问统计默认禁用，填写 `analytics.json` 并发布后，由 Umami 接收正式阅读页面的统计，后台需登录 Umami 查看。
- 写作页不加载第三方统计，只能访问 `api.github.com`，预览里的原生 HTML 一律按文字显示、不执行。任何人都能打开写作页，但没有对仓库有写权限的令牌就提交不了。令牌只在内存里，建议用只授权 `bytelife`、只给 Contents 读写、30 天过期的细粒度令牌。
- 协作者对整个仓库都有写权限，没法只限制在某个作者的文章上。人多以后建议给 `main` 加规则：禁止强制推送和删除；需要你先过目时，再加“合并前需要 PR 和审核”，把自己设为可绕过。不想给权限的人可以直接在 GitHub 上编辑文章，GitHub 会替 TA 发起 PR，构建检查自动运行，你确认后合并。
- “新建文章”工作流需要写仓库的权限，只有对仓库有写权限的人能运行；表单内容只通过环境变量交给脚本，`test_build.py` 会检查以后修改时没有把输入直接拼进命令。
- 每个页面用 `<meta>` 声明内容安全策略（CSP），放行本站资源、一段按哈希校验的主题初始化脚本，并开启 Trusted Types。配置访问统计后，阅读页额外放行 Umami 官方脚本和收集接口；写作页保持独立策略。GitHub Pages 不能自定义响应头，所以防点击劫持的 `frame-ancestors` 等只能写在响应头里的项目目前无法设置。
- 发布流程里的官方动作固定到完整提交 SHA，Python 依赖固定版本和哈希；升级时同时改版本注释和 SHA。
- **文章改错了**：在 GitHub 打开该文件的 **History**，找到改错前的版本复制回来；或在本机执行 `git revert <提交号>` 再推送，会新增一个撤销提交，历史保留。
- **发布出错了**：先在本机 `git revert` 出问题的提交并推送，网站会按上一版重新发布。急用时也可以在 **Actions** 里打开上一次成功的运行，点 **Re-run all jobs** 重新发布那一版（以 GitHub 页面当时的提示为准）；这只是临时回到旧内容，下一次推送仍会发布 `main` 的最新状态。不要用强制推送改写 `main` 的历史。

旧论坛的数据库备份、账户数据、私信和管理内容不在这个公开仓库。原论坛目前仍保留，迁移没有取消其账户或删除原主题。

网站目前是文章站：GitHub Discussions 提供交流，不会自动继承 Discourse 的用户、登录状态和通知系统。4 篇公开教程的 5 楼内容已迁入；自己的原文和后续改动保留在 Git 历史中。

本站有 `sitemap.xml`。先前给旧论坛做的 Google Search Console 所有权验证不会自动转移到这个新地址；如需管理新站收录，要另加 `https://milo-guo.github.io/bytelife/` 资源。发布不等于立刻被搜索引擎收录。

文章内容与原有图片的权利归原作者；转载的项目帮助截图保留原出处。当前没有把整站内容另行改成宽松开源许可证。
