# 02c 功能设计与安全要求同步：学习资料包

本包配合 ByteLife 文章《02c 功能设计实操》使用，依据1103上下半场材料重写，包含技术校正和整理补充。不是老师提示词原文件、完整会考系统源码或可启动应用。

## 打开与使用

1. 用 Windows 资源管理器解压 ZIP。
2. 打开 VS Code，点 `File → Open Folder`（文件→打开文件夹），打开解压目录，先读本 README。
3. 在你自己的项目内建 `prompts` 目录，复制 `02c功能设计.prompt`；管理端、小程序端各复制一份，每份只选一个端。
4. 按真实项目填写输入路径、版本、端、输出文件。已有项目先查看 Git 状态，保留当前改动。
5. 在能读写该项目的 Agent 会话中，先核对输入，再引用文件或粘贴填好的全文。
6. 输出后打开真实文档，按七项模板和核对表逐项检查。有冲突或关键待确认时先澄清。

完成标志是目标文档非空、F/AC/API映射可追踪、接口和数据库一致、缺口与待确认状态清楚。没有统一启动命令，因为这里是文本材料；实际工程的启动和测试命令应让Agent读取真实配置后给出。

## 文件

| 文件 | 用途 |
| --- | --- |
| 02c功能设计.prompt | 按一端一份生成、补录功能设计 |
| 单功能规格模板.md | 入口至覆盖AC的七项，以及完整契约检查 |
| 多端输入输出核对表.md | 对齐文件路径、版本、端与统计口径 |
| 变更同步清单.md | 新需求回写上游，确认后再交接 |
| 指挥Agent操作手册.md | 核对、生成、抽查、修订、拆任务和续接话术 |

## 技术范围

资料包使用HTTPS/TLS、成熟密码库、服务端授权与校验等基础要求。课堂自定义`esc(...)`、MD5、Base64“两层加密”等内容仅作为文章中的讲解记录，不作为本包推荐方案。Base64是编码，密码存储通常使用单向哈希；应用层额外加密需要独立的威胁模型和协议设计。

没有老师项目全部文件，未独立执行课堂数据库与检查器，不能据本资料包认定老师应用已通过安全测评或上线。

参考：[OWASP密码存储](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)、[TLS](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html)、[授权](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)、[认证](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)。
