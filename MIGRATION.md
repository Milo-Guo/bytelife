# 从论坛迁到这里

2026-10-22，ByteLife 从 `bytelife.discourse.group` 迁到 GitHub，文章在 GitHub Pages 阅读，源码和修改记录留在仓库。

## 迁了哪些内容

| 原主题 | 新位置 | 处理 |
| --- | --- | --- |
| 7：Git 零基础完整教程 | [Git 入门](content/git-basics.md) | 保留正文、命令速查和自定义章节直达 |
| 8：Minecraft Java 模组入门（主楼和续篇） | [Minecraft Mod](content/minecraft-mod.md) | 两楼合并；修订 PCL 变化、安装和启动器选择 |
| 10：WindowsApps 与软件入口 | [软件入口](content/windowsapps.md) | 保留文字与配图 |
| 11：桌面图标恢复 | [桌面图标](content/desktop-icons.md) | 保留文字与配图 |

共 4 篇公开教程、5 楼文章。14 处正文配图引用涉及 13 张不同的原图；同一张应用列表截图被两篇文章使用。原图全部保存到仓库，不再靠旧论坛链接显示。

本次修订另外补入 2 张 Fabric 官方文档的安装界面截图，图下注明版本差异和许可。全部图片的来源说明见仓库 `assets/IMAGE-SOURCES.md`。

Minecraft 的旧版 PCL 图文保存在[历史存档](archive/minecraft-pcl-2026-10-05.md)。PCL 更新部分区分已有环境、本地导入与新装游戏；不会把“取消下载”写成“所有旧版本都不能玩”。新启动器项目的状态以 2026-10-22 核实结果为准，未经安装测试的项目有明确标注。

## 保留和检查

- 迁移源取自当日公开主题，包含作者在论坛上的近期修改。
- 原图地址、仓库文件名、大小和 SHA-256 记录在 `migration-images.json`。
- 构建检查覆盖站内文件、图片、章节锚点和重复 ID。Git 自定义的 `git-section-…` 直达锚点保留。
- 私有数据库备份、用户资料、私信和管理内容没有发布。完整数据库备份与原始公开主题导出另存在作者本机备份目录。
- 历史 PCL 存档不进入站内全文索引，网页设置了 `noindex`，避免旧安装步骤混入当前搜索结果。
- 代码示例的迁移和网站构建检查，不等于已经编译、运行 Minecraft 模组；文章保留了未完成游戏内验收的说明。

原论坛和原主题没有删除；此站的交流入口使用 GitHub Discussions。Discourse 账号、权限、通知和 Google 所有权验证不会自动迁移为 GitHub 功能。
