看一些美国大学的 CS 课程会发现，他们很少把 Git 当成一门“以后再学的工具”。

很多时候，学生刚开始写程序，就已经在用 Git 交作业、管理代码，顺带接触命令行、Linux、SSH 这些东西。老师也不会等你把某门语言学得差不多了，再专门告诉你什么叫版本控制。

我觉得这里面其实是两种学习思路的区别。

一种是先学语法、刷题，等以后做项目了，再补 Git、Linux、工程工具；另一种是从一开始就把这些东西放进真实的开发流程里，用着用着自然就明白了。

Git 就很典型。

如果只是为了应付一门编程课，确实可以几年都不用它。但如果目标是学计算机，而不只是学一门编程语言，那它其实应该学得比很多人想象中更早。

那么话不多说，我们开始。愿大家学习愉快。

## 流程预览
**安装 → 创建仓库 → 保存版本 → 查看变化 → 使用分支 → 撤销错误 → 上传 GitHub → 获取更新**。

> **适用环境：Windows + Git Bash。** 所有终端命令都在 Git Bash 中运行。其他系统的 Git 原理相同，但打开终端、安装和编辑文件的方法不同。
>
> 命令输出是示例，版本号、路径和提交编号以你的电脑为准。

## 索引

**一键空降：** [02｜安装 Git，及确认](../content/git-basics.md#git-section-02) · [05｜创建文件，保存第一个版本](../content/git-basics.md#git-section-05) · [10｜分支有什么用？亲手试一次](../content/git-basics.md#git-section-10) · [11｜操作错了怎么办？分清三种撤销](../content/git-basics.md#git-section-11) · [12｜上传 GitHub，让别人能看见项目](../content/git-basics.md#git-section-12) · [16｜进阶练习：解决一次合并冲突](../content/git-basics.md#git-section-16) · [17｜常见报错：先看重点，再处理](../content/git-basics.md#git-section-17) · [20｜Git 核心命令速查表](../content/git-basics.md#git-section-20)

- **01—05：** 认识 Git、安装、配置、创建仓库、第一次提交。
- **06—09：** 理解暂存区、查看修改、阅读历史、忽略文件。
- **10—11：** 分支和合并、三种撤销方法。
- **12—15：** 上传 GitHub、日常更新、拉取与克隆。
- **16—19：** 冲突练习、常见报错、学习路线、自测。
- **20：核心命令速查表。** 按用途分组，每条都有简短解释。

在电脑上可以按 **Ctrl + F** 搜索本文命令。论坛可能先打开自己的话题搜索；若要使用浏览器“在页面中查找”，可从浏览器菜单打开。

## 01｜Git 和 GitHub 分别是什么？

### Git：在电脑上管理版本的工具

假设你写了一份学习笔记，改来改去，最后出现：

```text
学习笔记.txt
学习笔记修改版.txt
学习笔记最终版.txt
学习笔记最终版2.txt
学习笔记真的最终版.txt
```

Git 可以记录每次提交改了什么、什么时候改的、谁改的、为什么改，以及过去的内容是什么。你可以一直使用同一个文件名，通过历史记录查看变化。

**Git 不会自动记录每次 Ctrl + S。主动执行提交，才会产生一个新的历史版本。** 大多数本地操作不需要联网。[官方说明：Git 是什么](https://git-scm.com/book/en/v2/Getting-Started-What-is-Git%3F)

它适合代码、学习笔记、配置等纯文本。图片、视频、Word 文档也能存版本，但通常不能像代码一样逐行比较，大文件还可能受托管平台限制。

### GitHub：存放和分享 Git 仓库的平台

GitHub 可以在线保存仓库、分享项目、让你换电脑继续工作，也能让多人协作。

你可以只用 Git，也可以先本地提交，再上传 GitHub。**本地提交成功，不代表已经上传。**

<div><a name="git-section-02"></a></div>

## 02｜安装 Git，及确认

### 第一步：下载

用浏览器打开 [Git 官方 Windows 下载页](https://git-scm.com/install/windows)。普通 Intel / AMD Windows 电脑一般选 **x64 Setup**；ARM 设备选对应的 ARM64 安装程序。

下载后双击安装。第一次安装，多数选项可以保留默认值。如果出现以下选项：

- **Git Bash Here**：保留，方便从文件夹打开终端。
- **Git Credential Manager**：保留，后面用于 GitHub 登录。
- **默认编辑器**：选你会用的编辑器。本教程主要用记事本编辑文件，并用命令参数填写提交说明。

安装界面可能随版本变化，不需要追求每个按钮和教程完全一致。

### 第二步：打开 Git Bash

Windows 开始菜单搜索 **Git Bash**，点击打开。以后本文说“在终端执行”，都指在这个窗口输入命令并按 Enter。

输入：

```bash
git --version
```

应该看到类似：

```text
git version 2.xx.x.windows.x
```

版本号不同没关系。看到版本号，说明 Git 可以运行。如果提示找不到命令，确认安装完成，关闭旧终端，再打开 Git Bash。

## 03｜配置提交时显示的名字和邮箱

把下面引号里的内容换成自己的信息，再逐行执行：

```bash
git config --global user.name "你的名字或昵称"
git config --global user.email "你的提交邮箱"
```

例如名字可以是 ByteLife。邮箱要使用自己的提交邮箱，不要照抄别人的地址。

提交邮箱会写入历史。如果以后公开仓库，别人可能看到它。想隐藏个人邮箱，可以登录 GitHub，在 **Settings → Emails** 中找到平台提供给你的完整 noreply 邮箱并使用。

检查：

```bash
git config --global --get user.name
git config --global --get user.email
```

应该分别显示你设置的名字和邮箱。

| 内容 | 含义 |
|---|---|
| git config | 修改 Git 配置 |
| `--global` | 对当前电脑用户的 Git 项目默认生效 |
| user.name | 提交作者名字，不要求等于 GitHub 用户名 |
| user.email | 提交作者邮箱 |

某个项目需要不同身份时，在仓库内设置不带 `--global` 的配置即可。**配置作者身份不会帮你登录 GitHub。** [官方首次配置说明](https://git-scm.com/book/zh/v2/起步-初次运行-Git-前的配置)

## 04｜创建独立练习文件夹

### 第一步：创建并进入文件夹

打开 Windows 文件资源管理器，在“文档”或自己方便找到的位置创建文件夹：**git-first-lesson**。

进入这个文件夹，在空白处右键。Windows 11 可能需要先点 **显示更多选项**，再选 **Open Git Bash here**，意思是在这里打开 Git Bash。

### 第二步：确认自己在哪里

执行：

```bash
pwd
ls
```

pwd 显示当前目录，结果可能是：

```text
/c/Users/你的用户名/Documents/git-first-lesson
```

路径可以不同，但末尾应该是练习文件夹。ls 列出文件；空文件夹没有输出很正常。这两条是终端命令，不是 Git 命令。

### 第三步：初始化仓库

执行：

```bash
git init -b main
git status
```

先出现类似 “Initialized empty Git repository in .../.git/”，然后状态里显示：

```text
On branch main
No commits yet
```

意思是当前分支叫 main，还没有提交。文件夹里会出现隐藏的 .git 目录，用来存放历史等信息，别手动修改它。

**初始化通常只做一次。重新打开项目时，不需要再次 init。**

<div><a name="git-section-05"></a></div>

## 05｜创建文件，保存第一个版本

### 第一步：创建 README.md

在练习目录的 Git Bash 中执行：

```bash
touch README.md
notepad README.md
```

touch 在文件不存在时创建空文件；notepad 用 Windows 记事本打开文件。

写入：

```markdown
# 我的 Git 学习笔记

这是我用来练习 Git 的第一个项目。

## 学习目标

- 学会保存版本。
- 学会查看修改。
- 学会把项目上传 GitHub。
```

按 **Ctrl + S** 保存，然后关闭记事本。

README.md 通常用于介绍项目。Markdown 用普通文本表示格式：# 是一级标题，## 是二级标题，行首的 - 可以表示列表。

### 第二步：查看状态

执行：

```bash
git status
```

会看到类似：

```text
Untracked files:
  README.md
```

Untracked 是“尚未跟踪”：文件存在，但还没有加入 Git 的版本管理流程。

### 第三步：暂存

执行：

```bash
git add README.md
git status
```

add 没有输出通常正常。status 应该显示：

```text
Changes to be committed:
  new file: README.md
```

意思是这个文件已经准备进入下一次提交。

### 第四步：提交

执行：

```bash
git commit -m "创建 Git 学习笔记"
```

会看到类似：

```text
[main (root-commit) a1b2c3d] 创建 Git 学习笔记
 1 file changed, ...
 create mode 100644 README.md
```

main 是分支；a1b2c3d 是示例提交编号，你的会不同；-m 后面是这次提交的说明。

### 第五步：确认结果

执行：

```bash
git status
```

应看到：

```text
nothing to commit, working tree clean
```

当前没有等待提交的修改。**第一个本地版本保存成功，但还没上传 GitHub。**

## 06｜工作区、暂存区、本地仓库、远程仓库

```text
工作区：正在编辑的文件
  │ git add
  ▼
暂存区：下一次准备提交的内容
  │ git commit
  ▼
本地仓库：已经保存的提交历史
  │ git push
  ▼
远程仓库：例如 GitHub 上的仓库
```

暂存区可以让你选择本次提交什么。比如同时修改笔记和一个未完成练习，只想先交笔记，就只 add README.md。

**git add 暂存的是执行当时的内容。** add 后又修改文件，后面的修改不会自动进入暂存区，想一起提交就再 add 一次。[官方 git add 说明](https://git-scm.com/docs/git-add)

## 07｜修改文件，查看变化，保存第二个版本

打开：

```bash
notepad README.md
```

在末尾增加：

```markdown

## 今天学到的内容

- Git 可以记录项目版本。
- git add 用来暂存修改。
- git commit 用来保存一个本地版本。
```

保存、关闭。执行：

```bash
git status
git diff
```

status 中会出现 modified: README.md，表示已跟踪文件有修改。diff 显示具体变化，正文中 + 开头是新增，- 开头是删除；顶部的 `---`、`+++` 是文件标记。

如果进入可滚动的查看界面，按 **q** 退出。

然后：

```bash
git add README.md
git diff --staged
```

这次查看的是准备提交的变化。暂存后，普通 `git diff` 可能没有输出，因为它比较工作区与暂存区；不是修改凭空消失了。

确认内容后：

```bash
git commit -m "补充 Git 基础命令说明"
git status
```

工作区应再次干净。[官方记录修改说明](https://git-scm.com/book/zh/v2/Git-基础-记录每次更新到仓库)

## 08｜过去的版本在哪里？

执行：

```bash
git log --oneline
```

结果类似：

```text
b2c3d4e 补充 Git 基础命令说明
a1b2c3d 创建 Git 学习笔记
```

最新提交通常在上面。想看当前提交的具体修改：

```bash
git show HEAD
```

在本文的正常分支操作中，HEAD 可以理解为当前所在提交。查看这个提交里 README 的完整内容：

```bash
git show HEAD:README.md
```

查看过去某次提交中的文件，用你实际看到的编号替换“提交编号”：

```bash
git show 提交编号:README.md
```

show 用于查看，不会直接把工作区文件改成旧版本。输出较长时按 q 退出。

## 09｜用 .gitignore 排除不应提交的文件

临时文件、日志、可重新生成的缓存、含密码的本地配置，通常不应提交。

创建忽略文件：

```bash
touch .gitignore
notepad .gitignore
```

写入并保存：

```gitignore
# 本地私密配置
.env

# 练习产生的临时文件
scratch.txt
*.log
```

文件名是 .gitignore，开头有点，没有 .txt 后缀。

验证：

```bash
touch scratch.txt
git status
git check-ignore -v scratch.txt
```

普通 status 应列出 .gitignore，但不列出 scratch.txt。check-ignore 会说明匹配到了哪条规则。

提交规则：

```bash
git add .gitignore
git commit -m "添加临时文件忽略规则"
```

**忽略规则不会自动作用于已经跟踪的文件，也不会清除过去的历史。** 普通文件若想保留在本地、停止跟踪，可确认路径后使用 `git rm --cached 文件名`，再提交这个变化。

如果泄露了密码或密钥，要先撤销或更换凭据，再处理历史；仅删当前文件不够。练习时不需要写入真实秘密。[官方 gitignore 说明](https://git-scm.com/docs/gitignore)

<div><a name="git-section-10"></a></div>

## 10｜分支有什么用？亲手试一次

main 保留已整理好的笔记，新分支用于尝试新增命令速查文件，确认合适后合并回来。

Git 不会为每个分支创建一个可见的新文件夹。切换分支时，它会调整当前工作区内容。

### 第一步：检查工作区

```bash
git status
```

从工作区干净的状态开始。有未提交内容就先处理，避免混淆。

### 第二步：创建并切换分支

```bash
git switch -c add-command-notes
git branch
```

switch 是切换，-c 表示创建。branch 的结果类似：

```text
* add-command-notes
  main
```

星号表示当前分支。[官方 switch 说明](https://git-scm.com/docs/git-switch)

### 第三步：添加文件并提交

```bash
touch commands.md
notepad commands.md
```

写入：

```markdown
# Git 常用命令

- git status：检查项目状态。
- git diff：查看尚未暂存的修改。
- git add：暂存准备提交的内容。
- git commit：保存一个本地版本。
- git log：查看提交历史。
```

保存、关闭，然后执行：

```bash
git add commands.md
git commit -m "新增 Git 命令速查表"
```

### 第四步：切回 main，观察变化

```bash
git switch main
ls
```

commands.md 会从当前文件夹中消失。这是正常的：它已经提交到新分支，但还没进入 main。

再执行：

```bash
git switch add-command-notes
ls
```

文件会重新出现。这就说明两个分支对应的项目内容可以不同。

### 第五步：合并回 main

```bash
git switch main
git merge add-command-notes
ls
git status
```

这次练习通常显示 Fast-forward，表示 main 可以直接向前推进，不需要额外生成合并提交。main 中现在也应有 commands.md，工作区干净。

**想把修改合并到哪个分支，就先切到那个分支。** [官方 merge 说明](https://git-scm.com/docs/git-merge)

<div><a name="git-section-11"></a></div>

## 11｜操作错了怎么办？分清三种撤销

### 情况 A：暂存了，但暂时不想提交

打开 README：

```bash
notepad README.md
```

末尾添加“这是一行撤销练习。”，保存。执行：

```bash
git add README.md
git status
git restore --staged README.md
git status
```

文件会从“已暂存”回到“修改了、尚未暂存”。打开文件，练习行仍在。

**取消暂存保留修改，只是从下次提交的准备内容里移出。**

### 情况 B：这段未提交修改，确实不要了

继续上面的练习。先执行：

```bash
git diff
```

确认只有打算丢弃的练习修改，再执行：

```bash
git restore README.md
```

练习行应该消失。**该命令会丢弃这个文件尚未暂存的修改，真实项目先检查差异，重要内容先备份。**

普通 restore 默认从暂存区恢复工作区；上面已经先取消暂存，所以这次恢复的是当前提交内容。若仍有暂存内容，不要误认为普通 restore 一定回到最近提交。[官方 restore 说明](https://git-scm.com/docs/git-restore)

### 情况 C：已经提交，想撤销那次提交的效果

再次打开 README，末尾添加“这是一行用于练习 revert 的内容。”，保存、关闭。

```bash
git add README.md
git commit -m "添加 revert 练习内容"
git status
git revert --no-edit HEAD
git log --oneline
```

先确认 status 干净再 revert。HEAD 指当前提交，`--no-edit` 使用自动生成的说明，不打开编辑器。

你应该看到：原提交还在，上面多了一条撤销提交；README 里的练习行消失。

revert 通过新提交抵消旧修改，适合撤销已经分享的提交，但也可能遇到冲突。[官方 revert 说明](https://git-scm.com/docs/git-revert)

| 目的 | 本练习使用的命令 | 结果 |
|---|---|---|
| 取消暂存 | git restore `--staged` README.md | 文件修改保留 |
| 丢弃未暂存修改 | git restore README.md | 覆盖对应工作区修改 |
| 撤销提交效果 | git revert `--no-edit` HEAD | 新增反向提交，保留历史 |

<div><a name="git-section-12"></a></div>

## 12｜上传 GitHub，让别人能看见项目

### 第一步：创建空远程仓库

用浏览器登录 [GitHub](https://github.com)，找到 **New repository**，填写：

- **Repository name**：git-first-lesson。
- **Description**：我的 Git 入门练习和学习笔记。
- **Public / Private**：公开或私有。要让其他人直接访问，选择 Public；Private 需要相应访问权限。

**本地已有文件和提交，这次创建时不要自动添加 README、.gitignore 或 License。** 点击 **Create repository**。[官方上传流程](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github)

### 第二步：复制 HTTPS 地址

在新仓库的 Quick setup 区域选择 HTTPS，复制类似地址：

```text
https://github.com/你的用户名/git-first-lesson.git
```

### 第三步：连接本地仓库

回到原来的 git-first-lesson 终端，先检查位置和状态：

```bash
pwd
git status
```

把下面地址换成你刚复制的真实地址：

```bash
git remote add origin https://github.com/你的用户名/git-first-lesson.git
git remote -v
```

origin 是远程仓库的常用名字。应看到 fetch 和 push 两行地址。添加 remote 只是记录目标，还没上传。

### 第四步：第一次推送并登录

```bash
git push -u origin main
```

它把本地 main 推送到 origin，并建立后续使用的跟踪关系。

Git Credential Manager 如弹出登录窗口，选择浏览器登录，完成 GitHub 授权及必要的双重验证。GitHub 的 Git HTTPS 操作不支持直接用账号密码认证；这里优先用 GCM 的浏览器登录，不把令牌写进命令或仓库地址。[官方凭据管理说明](https://docs.github.com/en/get-started/git-basics/caching-your-github-credentials-in-git)

成功时可能看到：

```text
main -> main
branch 'main' set up to track 'origin/main'.
```

### 第五步：到网页验证

刷新 GitHub 仓库页面，应能看到 README.md、.gitignore、commands.md，以及提交说明。scratch.txt 被忽略，不应上传。

GitHub 通常会把 README 渲染为项目介绍。**终端推送成功，网页也能看到文件，才算完成这一步。**

## 13｜以后如何继续更新？

修改并保存 README 后，依次执行：

```bash
git status
git diff
git add README.md
git diff --staged
git commit -m "补充今天的学习心得"
git push
```

分别是：检查文件状态 → 查看修改 → 选择提交内容 → 检查暂存内容 → 保存本地版本 → 上传远程。

第一次用 -u 设置过跟踪关系，后续在这个分支通常可直接 push。

**git add . 可以用，但先知道自己正在提交什么。** 它会暂存当前目录及子目录中未被忽略的新文件，以及跟踪文件的修改、删除。初学时可以明确指定：

```bash
git add README.md commands.md
```

提交说明写具体事情，例如“补充 Git 安装步骤”“修正上传命令”，比“修改”“好了”“最终版”更方便查历史。

## 14｜GitHub 网页改了内容，电脑怎么更新？

在 GitHub 打开 README.md，点击铅笔，末尾加一句“这段内容是在 GitHub 网页上添加的。”。

点击 **Commit changes**。若询问分支，这次练习提交到 main。

回到电脑，先确认工作区干净，然后：

```bash
git status
git pull --ff-only
```

在本地没有额外分叉提交的本次练习中，本地会更新。打开 README，应能看到网页新增内容。

`--ff-only` 要求只能直接向前推进；如果本地和远程都出现不同的新提交，它会停止，让你先处理分歧，避免不明不白地产生合并。[官方 pull 说明](https://git-scm.com/docs/git-pull)

```text
本地提交 ── push ──▶ 远程仓库
本地仓库 ◀── pull ── 远程更新
```

多台电脑或多人协作时，开始工作前先检查状态并获取更新，再修改内容。

## 15｜下载已有仓库：clone

GitHub 仓库页面点击 **Code → HTTPS**，复制地址。回到 Git Bash：

```bash
cd ..
pwd
```

cd .. 是进入上一级目录。确认这是你准备放新项目的位置。

替换真实地址后执行：

```bash
git clone https://github.com/你的用户名/git-first-lesson.git git-first-lesson-copy
cd git-first-lesson-copy
git status
git log --oneline
git remote -v
```

特意取名 git-first-lesson-copy，避免与原文件夹重名。克隆后有文件、历史、远程配置，不需要再次 init。

**clone 通常会取得仓库历史；Download ZIP 通常只是所选版本的文件快照，不含 .git。** 下载完成不等于项目已运行，运行方式要读项目 README。[官方 clone 说明](https://git-scm.com/docs/git-clone)

<div><a name="git-section-16"></a></div>

## 16｜进阶练习：解决一次合并冲突

前面的内容已经足够开始管理个人学习项目。继续练习时，回到**原来的 git-first-lesson 文件夹**打开 Git Bash，确认位于 main、工作区干净。

冲突表示双方修改无法自动合并，需要你决定最终内容，不表示整个项目坏了。

### 第一步：创建共同起点

```bash
touch conflict-demo.txt
notepad conflict-demo.txt
```

写入“我的学习目标：学会 Git 基础。”，保存、关闭：

```bash
git add conflict-demo.txt
git commit -m "创建冲突练习文件"
```

### 第二步：在新分支修改同一行

```bash
git switch -c conflict-practice
notepad conflict-demo.txt
```

把整行替换成“我的学习目标：学会 Git 分支。”，保存、关闭：

```bash
git add conflict-demo.txt
git commit -m "分支中调整学习目标"
```

### 第三步：回到 main，也修改这一行

```bash
git switch main
notepad conflict-demo.txt
```

把整行替换成“我的学习目标：学会上传 GitHub。”，保存、关闭：

```bash
git add conflict-demo.txt
git commit -m "主分支中调整学习目标"
git merge conflict-practice
```

应出现包含 CONFLICT 的提示。执行 `git status`，会看到 conflict-demo.txt 需要处理。

### 第四步：编辑冲突文件

```bash
notepad conflict-demo.txt
```

内容类似：

```text
<<<<<<< HEAD
我的学习目标：学会上传 GitHub。
=======
我的学习目标：学会 Git 分支。
>>>>>>> conflict-practice
```

上半部分来自当前 main，下半部分来自合入分支。把这整块替换成最终内容：

```text
我的学习目标：学会 Git 分支，并把项目上传 GitHub。
```

删除冲突标记，保存、关闭。然后：

```bash
git add conflict-demo.txt
git commit -m "合并学习目标并解决冲突"
git status
```

工作区应恢复干净。若仍在合并过程中、想中止本次合并，可用 `git merge --abort`。本练习从干净状态开始，便于中止；真实项目也应先处理已有修改。

<div><a name="git-section-17"></a></div>

## 17｜常见报错：先看重点，再处理

### fatal: not a git repository

当前位置不在 Git 仓库里。先用 pwd、ls -a 检查目录。已有项目就进入正确文件夹；确实是全新项目才 init，不要遇到报错就随手初始化。

### Author identity unknown

缺少提交身份。配置 user.name 和 user.email，再重新提交，参考第 03 节。

### nothing to commit, working tree clean

通常是正常状态。若你以为有修改，检查编辑器是否保存、是不是改错文件夹、内容是否真的变化、文件是否被忽略或已提交。

### remote origin already exists

先执行 `git remote -v`。地址正确就不用重复添加；确实错误才运行：

```bash
git remote set-url origin 你的正确仓库地址
```

### src refspec main does not match any

可能还没第一次提交，或分支不叫 main。检查：

```bash
git status
git branch --show-current
```

有提交后可再看 `git log --oneline`。根据实际情况先提交，或使用正确分支名称。

### non-fast-forward / fetch first

远程可能有本地没有的提交。先检查：

```bash
git status
git fetch origin
git log --oneline --graph --all -12
```

如果工作区干净且没有历史分叉，可以 `git pull --ff-only`，再 `git push`。若 ff-only 也失败，需要看清分歧后选择合并等处理，不要直接强推。

如果远程创建时自动添加过 README，本地又独立初始化，可能有两个不同起点，与普通“落后几个提交”不同。

### Authentication failed / 403 / Repository not found

检查仓库地址、当前登录账号、私有仓库权限、GCM 登录是否完成，以及网络或组织限制。改提交邮箱不能解决登录权限问题。

### LF / CRLF 警告

通常是换行符差异。警告不一定表示提交失败，检查最终结果和 `git status`。团队项目优先遵守已有 .gitattributes，不要为消除一条提示反复改全局配置。

### README.md 变成 README.md.txt

文件资源管理器打开 **查看 → 显示 → 文件扩展名**，确认文件确实叫 README.md；同样检查 .gitignore 没有多出 .txt。

## 18｜阶段重点学习顺序

| 阶段 | 重点 | 完成目标 |
|---|---|---|
| 个人使用 | status、diff、add、commit、log | 每完成一段内容就提交，能找回历史 |
| 远程同步 | remote、push、clone、fetch、pull | 本地与 GitHub、另一台电脑之间同步 |
| 分支协作 | switch、branch、merge、冲突处理 | 独立完成修改，再合并 |
| GitHub 协作 | Pull Request，简称 PR | 提交分支修改供维护者检查、讨论和合并 |
| 按需进阶 | stash、tag、rebase、cherry-pick、reflog、bisect | 有明确需求时再学习 |

PR 是 GitHub 等托管平台提供的协作流程，不是一个名叫 git pr 的基础 Git 命令。

## 19｜检查自己是否真正学会

不看前面的示例，试着完成：

- 创建新仓库，写 README，提交第一个版本。
- 修改文件，先看差异，再提交，之后查看历史。
- 写一条忽略规则，并验证临时文件被忽略。
- 在新分支添加文件，切换观察，再合并回 main。
- 取消暂存并确认修改仍在。
- 在练习文件里丢弃未提交修改，用 revert 撤销一次提交。
- 上传 GitHub，在另一个文件夹克隆，获取一次远程更新。

每次操作前先看 `git status`。按“一件事情”组织提交，提交说明写清实际改动。求助时贴上执行的命令、完整报错和状态，注意隐藏敏感信息。

下面是查找用的命令表。**把命令用进项目，比一次背下整张表更有用。**

<div><a name="git-section-20"></a></div>

## 20｜Git 核心命令速查表

这里整理了 **147 条常用命令及写法，分为 14 组**。数量包含同一命令的不同参数形式，不代表需要学习 147 个互不相关的命令。

**使用方法：先按目的找组，再看说明；不要把整张表当成连续脚本运行。** 标注“进阶”的内容可以后学。标注“高风险”“丢弃修改”“改历史”的命令，要先弄清影响对象。

表里的 `<文件>`、`<目录>`、`<分支>`、`<地址>`、`<提交>` 是占位符：替换成实际值，**不要输入尖括号**。路径有空格时用英文双引号包起来；命令里的引号和横线使用英文半角字符。

**速查分类直达：** [A｜安装、配置与帮助](../content/git-basics.md#git-commands-a) · [B｜新建与克隆](../content/git-basics.md#git-commands-b) · [C｜状态、日志与差异](../content/git-basics.md#git-commands-c) · [D｜暂存与提交](../content/git-basics.md#git-commands-d) · [E｜分支与切换](../content/git-basics.md#git-commands-e) · [F｜合并、变基与挑选提交](../content/git-basics.md#git-commands-f) · [G｜远程连接、下载与上传](../content/git-basics.md#git-commands-g) · [H｜撤销、恢复与 reset](../content/git-basics.md#git-commands-h) · [I｜临时收起工作：stash](../content/git-basics.md#git-commands-i) · [J｜标签与版本发布](../content/git-basics.md#git-commands-j) · [K｜文件操作与清理](../content/git-basics.md#git-commands-k) · [L｜搜索、定位问题与统计](../content/git-basics.md#git-commands-l) · [M｜子模块与多工作区](../content/git-basics.md#git-commands-m) · [N｜看旧教程时会遇到的 checkout](../content/git-basics.md#git-commands-n)

<div><a name="git-commands-a"></a></div>

### A｜安装、配置与帮助

基础：先完成身份配置，再学其他设置。

| 命令 | 用途与注意事项 |
|---|---|
| `git --version` | 查看 Git 版本，确认安装成功。 |
| `git config --global user.name "名字"` | 设置当前电脑用户的默认提交作者名。 |
| `git config --global user.email "邮箱"` | 设置默认提交邮箱；公开仓库前考虑使用 noreply 邮箱。 |
| `git config user.name "名字"` | 只为当前仓库设置作者名，覆盖全局默认值。 |
| `git config --list --show-origin` | 查看生效配置及来源文件；分享输出前检查敏感信息。 |
| `git config --global init.defaultBranch main` | 设置今后新仓库的默认初始分支名，不会改已有分支。 |
| `git config --global core.editor "code --wait"` | 已安装 VS Code 且 code 命令可用时，让 Git 用它编辑说明。 |
| `git config --get core.autocrlf` | 查看换行配置；不要脱离项目规则照抄 true/input/false。 |
| `git config --global alias.st status` | 定义缩写，以后 git st 等于 `git status`。 |
| `git config --global --unset alias.st` | 删除上面那项全局别名配置。 |
| `git help <命令>` | 打开某条命令的帮助，例如 git help commit。 |
| `git <命令> -h` | 在终端查看简短用法，例如 `git status` -h。 |

[本组相关官方文档](https://git-scm.com/docs/git-config)

<div><a name="git-commands-b"></a></div>

### B｜新建与克隆

基础：新项目通常 init，已有仓库通常 clone。

| 命令 | 用途与注意事项 |
|---|---|
| `git init -b main` | 在当前目录建立仓库，初始分支叫 main。 |
| `git init <目录>` | 在指定目录创建或初始化仓库。 |
| `git clone <地址>` | 克隆仓库，包含文件、历史和默认远程配置。 |
| `git clone <地址> <目录>` | 克隆到指定目录名。 |
| `git clone --depth 1 <地址>` | 浅克隆较近历史，节省下载量，但旧历史不完整。 |
| `git clone --recurse-submodules <地址>` | 克隆主仓库时同时初始化、获取子模块。 |
| `git rev-parse --show-toplevel` | 显示当前仓库的根目录，帮助确认操作范围。 |

[本组相关官方文档](https://git-scm.com/docs/git-clone)

<div><a name="git-commands-c"></a></div>

### C｜状态、日志与差异

基础：这些主要用于观察，是排错时优先使用的命令。

| 命令 | 用途与注意事项 |
|---|---|
| `git status` | 查看分支、暂存区、工作区状态。 |
| `git status -sb` | 用紧凑格式显示分支及文件状态。 |
| `git log --oneline` | 每次提交用一行显示。 |
| `git log --oneline --graph --decorate --all` | 画出各引用可达的提交关系，并显示分支/标签标记。 |
| `git log -5` | 查看最近 5 次提交。 |
| `git log -p -- <文件>` | 查看指定文件的历史补丁。 |
| `git show <提交>` | 查看某次提交的信息和变化。 |
| `git show <提交>:<路径>` | 读取指定提交中的文件内容，不修改工作区。 |
| `git diff` | 比较工作区与暂存区的差异。 |
| `git diff --staged` | 比较暂存区与 HEAD；--cached 是同义写法。 |
| `git diff HEAD` | 查看已跟踪文件的暂存及未暂存修改，相对 HEAD 的总变化。 |
| `git diff <提交A> <提交B>` | 比较两个提交的最终文件内容。 |
| `git diff --stat` | 用文件和行数统计显示未暂存差异。 |
| `git diff --check` | 检查当前未暂存补丁中的空白错误和冲突标记；提交前可加 `--staged`。 |
| `git ls-files` | 列出索引中的文件，通常用于看哪些文件已被跟踪。 |

[本组相关官方文档](https://git-scm.com/docs/git-diff)

<div><a name="git-commands-d"></a></div>

### D｜暂存与提交

基础与进阶：提交前检查实际暂存的内容。

| 命令 | 用途与注意事项 |
|---|---|
| `git add <文件>` | 暂存指定文件当前的修改。 |
| `git add .` | 暂存当前目录及子目录中的合适变化，包括删除。 |
| `git add -A` | 暂存整个仓库中的新增、修改和删除；忽略规则仍适用。 |
| `git add -u` | 暂存已跟踪文件的修改与删除，不加入新文件。 |
| `git add -p` | 分块选择要暂存的修改，适合拆分提交。 |
| `git restore --staged <文件>` | 取消指定文件的暂存，保留工作区修改。 |
| `git commit -m "说明"` | 把暂存区保存为一次本地提交。 |
| `git commit -am "说明"` | 自动暂存已跟踪文件的修改/删除并提交，不包含未跟踪新文件。 |
| `git commit --amend -m "新说明"` | 改写最近一次提交，并包含当前暂存内容；提交编号会改变。 |
| `git commit --amend --no-edit` | 把暂存内容补入最近一次提交，沿用说明，同样会改写提交。 |

[本组相关官方文档](https://git-scm.com/docs/git-commit)

<div><a name="git-commands-e"></a></div>

### E｜分支与切换

基础：分支名、远程跟踪引用、当前分支是不同概念。

| 命令 | 用途与注意事项 |
|---|---|
| `git branch` | 列出本地分支，星号是当前分支。 |
| `git branch --show-current` | 显示当前分支名；分离 HEAD 时通常为空。 |
| `git branch -a` | 列出本地分支和远程跟踪分支。 |
| `git branch -vv` | 查看本地分支、跟踪关系及基于本地信息的领先/落后情况。 |
| `git branch <分支>` | 创建分支，但不切换。 |
| `git switch <分支>` | 切换到指定分支。 |
| `git switch -c <分支>` | 创建并切换到新分支。 |
| `git switch -` | 切回上一次所在的分支/位置。 |
| `git switch --detach <提交>` | 临时查看历史提交，进入分离 HEAD；要保留新工作可再建分支。 |
| `git branch -m <新名字>` | 重命名当前本地分支，不会自动重命名远程分支。 |
| `git branch -d <分支>` | 删除满足 Git 已合并检查的本地分支，不删除远程分支。 |
| `git branch -D <分支>` | 【谨慎】强制删除本地分支引用，可能丢失容易找到未合并工作的入口。 |
| `git branch --merged` | 列出已合并到当前 HEAD 的分支。 |
| `git branch --no-merged` | 列出尚未完全合并到当前 HEAD 的分支。 |

[本组相关官方文档](https://git-scm.com/docs/git-branch)

<div><a name="git-commands-f"></a></div>

### F｜合并、变基与挑选提交

进阶：rebase 与 cherry-pick 会产生新的提交；不要随意改写共享历史。

| 命令 | 用途与注意事项 |
|---|---|
| `git merge <分支>` | 把指定分支合并到当前分支。 |
| `git merge --no-ff <分支>` | 即使可快进也创建合并提交，保留合并节点。 |
| `git merge --abort` | 在冲突合并过程中尝试中止合并，合并前应保持工作区干净。 |
| `git rebase <基础分支>` | 将当前分支的相关提交重放到新基础上，通常改变提交编号。 |
| `git rebase -i HEAD~3` | 交互整理最近 3 个提交；需有对应历史且理解各操作。 |
| `git rebase --continue` | 解决冲突并 add 后继续变基。 |
| `git rebase --abort` | 中止本次变基，返回开始前状态。 |
| `git rebase --skip` | 【谨慎】跳过当前正在重放的提交，可能丢掉它的改动。 |
| `git cherry-pick <提交>` | 把指定提交的改动应用到当前分支，通常生成新提交。 |
| `git cherry-pick --continue` | 冲突解决并 add 后，继续挑选操作。 |
| `git cherry-pick --abort` | 中止当前挑选提交操作。 |

[本组相关官方文档](https://git-scm.com/docs/git-rebase)

<div><a name="git-commands-g"></a></div>

### G｜远程连接、下载与上传

基础与进阶：fetch 只获取，pull 还会整合；push 上传提交。

| 命令 | 用途与注意事项 |
|---|---|
| `git remote -v` | 查看远程名字及获取/推送地址。 |
| `git remote add origin <地址>` | 添加名为 origin 的远程。 |
| `git remote set-url origin <地址>` | 修改 origin 的地址。 |
| `git remote rename origin upstream` | 重命名本地远程配置；不会给网站上的仓库改名。 |
| `git remote remove <远程名>` | 删除本地远程配置及相关跟踪引用，不删除网站仓库。 |
| `git remote show origin` | 查看远程和分支跟踪信息，通常需要访问远程。 |
| `git fetch origin` | 获取远程提交并更新远程跟踪引用，不自动合并当前分支。 |
| `git fetch --all --prune` | 获取各远程并清理过期的远程跟踪引用，不等于删除本地分支。 |
| `git pull --ff-only` | 获取并仅在可快进时更新当前分支。 |
| `git pull --rebase` | 获取后以变基方式整合本地提交，可能冲突或改写本地提交。 |
| `git push -u origin main` | 推送 main，并设置上游跟踪关系。 |
| `git push` | 按当前分支跟踪关系和配置推送。 |
| `git push origin <分支>` | 推送指定本地分支到远程。 |
| `git push origin --delete <分支>` | 【谨慎】删除远程分支，会影响协作者。 |
| `git push --force-with-lease` | 【谨慎】在远程引用符合预期时强制更新；仍可覆盖历史，且依赖预期引用信息。 |
| `git push --force` | 【高风险】强制更新远程引用，可能覆盖别人的提交，不是普通推送报错的通用解法。 |

[本组相关官方文档](https://git-scm.com/docs/git-push)

<div><a name="git-commands-h"></a></div>

### H｜撤销、恢复与 reset

先区分“改文件”“改暂存区”“移动分支”“新增反向提交”。

| 命令 | 用途与注意事项 |
|---|---|
| `git restore <文件>` | 【丢弃修改】默认从暂存区恢复工作区文件，覆盖该文件未暂存修改。 |
| `git restore --staged <文件>` | 默认用 HEAD 恢复暂存区条目，保留工作区内容。 |
| `git restore --source=<提交> -- <文件>` | 【覆盖文件】把某提交中的文件内容恢复到工作区，不自动提交。 |
| `git revert <提交>` | 新增反向提交来撤销指定提交的效果，可能冲突；合并提交需要额外理解主线。 |
| `git revert --no-edit HEAD` | 撤销当前提交的效果，使用自动说明。 |
| `git revert --continue` | 解决冲突并 add 后继续 revert。 |
| `git revert --abort` | 中止当前 revert 操作。 |
| `git reset --soft HEAD~1` | 【改历史】回退当前分支一个提交，保留暂存区和工作区。 |
| `git reset --mixed HEAD~1` | 【改历史】回退一个提交并重置暂存区，保留工作区内容。 |
| `git reset --hard <提交>` | 【高风险】移动分支并重置暂存区和工作区，会丢弃已跟踪修改，也可能覆盖挡路的未跟踪文件。 |
| `git reflog` | 查看本地 HEAD 的移动记录，帮助定位误操作前的提交；不是永久备份。 |
| `git branch rescue <提交>` | 给已经找到的提交建立救援分支引用，便于继续检查恢复。 |

[本组相关官方文档](https://git-scm.com/docs/git-reset)

<div><a name="git-commands-i"></a></div>

### I｜临时收起工作：stash

进阶：适合临时切换工作，不要当长期备份。

| 命令 | 用途与注意事项 |
|---|---|
| `git stash push -m "说明"` | 暂存并收起已跟踪文件的工作区/暂存区修改。 |
| `git stash push -u -m "说明"` | 额外包含未跟踪文件，不含被忽略文件。 |
| `git stash list` | 列出本地保存的 stash。 |
| `git stash show -p stash@{0}` | 查看最近一份 stash 的补丁。 |
| `git stash apply stash@{0}` | 恢复指定 stash，保留该 stash 记录；可能有冲突。 |
| `git stash pop` | 恢复最近 stash，成功时删除其记录；冲突时通常保留。 |
| `git stash drop stash@{0}` | 【谨慎】删除指定 stash，先确认内容已恢复或确实不需要。 |
| `git stash clear` | 【高风险】删除全部 stash 记录，不要拿它当普通清理命令。 |
| `git stash branch <分支> stash@{0}` | 从 stash 原来的基础创建分支并恢复；成功时删除指定 stash 记录。 |

[本组相关官方文档](https://git-scm.com/docs/git-stash)

<div><a name="git-commands-j"></a></div>

### J｜标签与版本发布

进阶：标签标记版本，不是继续开发用的分支。

| 命令 | 用途与注意事项 |
|---|---|
| `git tag` | 列出本地标签。 |
| `git tag v1.0.0` | 在当前提交创建轻量标签。 |
| `git tag -a v1.0.0 -m "第一个版本"` | 创建带说明和标记者信息的附注标签；与上一条是替代选项。 |
| `git show v1.0.0` | 查看该标签及对应内容。 |
| `git push origin v1.0.0` | 推送指定标签。 |
| `git push origin --tags` | 推送所有本地标签，先确认哪些标签应该公开。 |
| `git tag -d v1.0.0` | 【谨慎】删除本地标签，不自动删除远程标签。 |
| `git push origin --delete tag v1.0.0` | 【谨慎】删除远程标签，可能影响发布流程。 |
| `git tag --contains <提交>` | 列出包含指定提交的标签。 |

[本组相关官方文档](https://git-scm.com/docs/git-tag)

<div><a name="git-commands-k"></a></div>

### K｜文件操作与清理

清理前先预览。未提交且未备份的文件，被删除后 Git 未必能恢复。

| 命令 | 用途与注意事项 |
|---|---|
| `git mv <旧路径> <新路径>` | 移动/重命名文件并更新暂存区，之后仍需提交。 |
| `git rm <文件>` | 【删除文件】从工作区和暂存区移除跟踪文件，之后提交删除。 |
| `git rm --cached <文件>` | 只停止跟踪并暂存这项变化，保留工作区文件；旧历史仍在。 |
| `git clean -n` | 只预览将清理的未跟踪文件，不删除。 |
| `git clean -nd` | 预览未跟踪文件和目录。 |
| `git clean -ndx` | 预览包括被忽略文件在内的未跟踪内容。 |
| `git clean -f` | 【高风险】删除未被忽略的未跟踪文件。 |
| `git clean -fd` | 【高风险】还会删除未跟踪目录。 |
| `git clean -fdx` | 【极易误删】连被忽略的文件也清理，可能删掉本地 .env、缓存等。 |
| `git check-ignore -v <文件>` | 查看某文件命中了哪条忽略规则。 |

[本组相关官方文档](https://git-scm.com/docs/git-clean)

<div><a name="git-commands-l"></a></div>

### L｜搜索、定位问题与统计

进阶：遇到“谁改了这一行”“哪个版本开始坏了”时使用。

| 命令 | 用途与注意事项 |
|---|---|
| `git grep "关键词"` | 在跟踪的文件中搜索内容。 |
| `git log -S "关键词" -- <文件>` | 查找让指定字符串出现次数改变的提交。 |
| `git blame <文件>` | 查看各行最后由哪个提交修改，便于找上下文，不是判断责任。 |
| `git bisect start` | 开始二分查错会话。 |
| `git bisect bad` | 把当前版本标记为有问题。 |
| `git bisect good <提交>` | 提供已知正常的版本，开始缩小范围。 |
| `git bisect good` | 测试当前版本后，将它标记为正常。 |
| `git bisect skip` | 当前版本无法测试时跳过，可能使最终结果不唯一。 |
| `git bisect reset` | 结束查错并返回开始前的位置。 |
| `git shortlog -sn HEAD` | 按作者统计 HEAD 可达历史中的提交数量，数量不等于贡献质量。 |
| `git archive --format=zip -o source.zip HEAD` | 导出当前提交的跟踪内容为 ZIP，不包含 .git 历史。 |

[本组相关官方文档](https://git-scm.com/docs/git-bisect)

<div><a name="git-commands-m"></a></div>

### M｜子模块与多工作区

进阶：普通单项目可以暂时跳过。

| 命令 | 用途与注意事项 |
|---|---|
| `git submodule add <地址> <路径>` | 把另一个仓库作为子模块加入，父仓库记录其提交位置。 |
| `git submodule update --init --recursive` | 初始化并检出父仓库记录的子模块版本，不等于追到子模块最新开发版本。 |
| `git submodule status` | 查看子模块提交状态。 |
| `git worktree add -b <新分支> <路径>` | 为同一仓库创建新分支及独立工作目录。 |
| `git worktree add <路径> <已有分支>` | 在另一个目录检出已有分支；同一分支通常不能同时被多个工作区检出。 |
| `git worktree list` | 列出该仓库的工作区。 |
| `git worktree remove <路径>` | 【移除目录】移除干净的关联工作区；不等于删除对应分支，不用强制选项掩盖未保存修改。 |

[本组相关官方文档](https://git-scm.com/docs/git-worktree)

<div><a name="git-commands-n"></a></div>

### N｜看旧教程时会遇到的 checkout

了解即可：新手通常用 switch 管分支、restore 管文件，更容易区分。

| 命令 | 用途与注意事项 |
|---|---|
| `git checkout <分支>` | 切换分支，常可改用 git switch <分支>。 |
| `git checkout -b <分支>` | 创建并切换分支，常可改用 git switch -c <分支>。 |
| `git checkout -- <文件>` | 【丢弃修改】从暂存区恢复工作区文件，常可改用 git restore <文件>。 |
| `git checkout <提交>` | 检出历史提交，通常进入分离 HEAD；继续写代码前考虑建立新分支。 |

[本组相关官方文档](https://git-scm.com/docs/git-checkout)

### O｜符号读法与易混概念

| 符号或名称 | 含义 |
|---|---|
| `HEAD` | 当前检出的位置；正常分支状态下指向当前分支的最新提交。 |
| `HEAD~1` | 沿第一父提交向前走 1 步；HEAD~3 是 3 步。 |
| `HEAD^` | 第一父提交；HEAD^2 是第二父提交，通常出现在合并提交上。 |
| `origin` | 一个远程配置的名字，常用但并非固定关键字。 |
| `origin/main` | 本地保存的远程 main 状态，通常要 fetch 后才更新，不是实时网络视图。 |
| `--` | 常用于分隔选项/版本与文件路径，例如 `git log -- README.md`。 |
| `.` | 当前目录；cd .. 中的两个点表示上一级目录。 |
| `stash@{0}` | 最近一份 stash；编号会随着新增或删除而变化。 |
| `A..B` | 在 log 中表示 B 可达而 A 不可达的提交；在 diff 中通常比较两个端点。 |
| `A...B` | 在 log 中查看两侧独有提交；在 diff 中通常比较共同祖先到 B 的变化。 |
| 暂存区 / Index / Staging Area | 本次准备提交的内容。 |
| Repository / Repo | 仓库，可指本地或远程，要看上下文。 |
| Detached HEAD | 当前检出的是某个提交而非普通分支；想保留新提交时及时建分支。 |

### P｜先记住这几组区别

- **save / add / commit / push**：编辑器保存文件 → 暂存选择 → 本地版本 → 上传远程。
- **fetch / pull**：fetch 获取远程信息；pull 还会整合到当前分支。
- **restore / reset / revert**：restore 主要恢复文件；reset 可调整暂存区或移动分支；revert 新增反向提交。
- **merge / rebase**：merge 合并历史；rebase 重放提交，通常改变提交编号。
- **branch / tag**：分支跟随开发继续前进；标签通常固定标记版本。
- **clone / Download ZIP**：clone 通常带版本历史和远程关系；ZIP 通常只有文件快照。

不需要为了使用 Git 先学完这张表。先把正文里的小项目走一遍，再把 Git 用到自己的笔记、代码或网站项目中，遇到需求回来查就可以。

如果在某一步卡住，可以到 [GitHub 交流区](https://github.com/Milo-Guo/bytelife/discussions)说明：**系统环境、做到第几节、执行的命令、完整报错、`git status` 的结果**。发出来之前，先隐藏令牌、私人邮箱和私有仓库地址等信息。

## 欢迎补充和交流。
以上
