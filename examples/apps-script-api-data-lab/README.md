# 信息学实习B：API与数据分析学习代码

配合 ByteLife 文章 `apps-script-api-data-lab` 使用。这里是根据课堂练习重新整理的中文注释版，函数名尽量沿用课堂。它不是老师原文的逐字副本，也不是自动同步到你学校账号的代码。

| 文件 | 在哪里运行 | 看什么结果 |
| --- | --- | --- |
| `apps_script/01_postal.gs` | Google Sheets绑定的Apps Script | 单元格公式返回邮编对应地区 |
| `apps_script/02_youtube.gs` | Apps Script，添加YouTube服务 | 执行日志显示两个频道的统计 |
| `apps_script/03_chat/Code.gs` 和 `index.html` | 同一个Apps Script项目，部署为网页 | 网页发送消息并收到回复 |
| `apps_script/04_places.gs` | Google Sheets绑定的Apps Script | 新结果工作表显示店铺数据 |
| `05_sales_skill_prompt.md` | Gemini技能设置中的指令 | 每次重新读取所指定的表格 |
| `python/analyze_cycling.py` | 本机Python | 汇总JSON和4张图 |

## 先看懂最小例子

先运行邮编查询，再看YouTube数组和循环，然后看聊天网页的前后端。`.gs` 使用Google提供的运行环境，不能直接用 `python` 或 `node` 执行。

## 邮编

1. 打开Google Sheets，选择「拡張機能」→「Apps Script」。
2. 把01文件内容粘贴到 `コード.gs` 并保存。
3. 返回表格，A列设为纯文本，A1输入 `1000000`，B1输入 `=ZIP_ADDRESS(A1)`。
4. 应返回东京都千代田区一带的邮编地区信息。此接口不提供具体门牌号。

## YouTube

1. 新建独立Apps Script项目，复制02文件。
2. 左侧「サービス」点加号，添加 `YouTube Data API v3`。
3. 保存，顶部函数选 `getChannelData2`，点「実行」，按本人账号完成授权。
4. 「実行ログ」应出现频道名、订阅数、公开视频数和观看数。数字会随时间变化。

## 聊天网页

1. 新建项目，把 `Code.gs` 内容粘到默认的 `コード.gs`。
2. 文件区点「＋」→「HTML」，文件名填 `index`，粘贴 `index.html` 的全部内容。
3. 左侧齿轮「プロジェクトの設定」→「スクリプト プロパティ」：添加 `GEMINI_API_KEY`，值填自己获准使用的密钥；可添加 `GEMINI_MODEL` 指定账号可用的模型。
4. 默认模型为 `gemini-3.5-flash-lite`，以后如不可用，以自己AI Studio中的可用模型为准。Gemini网页能聊天不等于API项目有可用配额。
5. 「デプロイ」→「新しいデプロイ」→「ウェブアプリ」。课堂一般选择以自己身份执行；访问范围按课程要求设置。公开链接的访问者会使用该项目的API配额，密钥留在服务器并不能防止他人通过网页消耗配额。
6. 完成授权，打开部署后的 `/exec` 地址。发送问候、介绍名字后再问名字、询问现实地址，分别观察通信、短期上下文和角色提示词。
7. 修改代码后，用「デプロイを管理」编辑部署并选新版本。仅保存编辑器不一定更新已有 `/exec` 网页。

本学习版增加了长度检查和错误提示，但没有账号系统、每日配额限制或数据库，适合受控课堂练习，不作为开放运营服务。刷新会清空浏览器中的 `chatHistory`。可选朗读来自浏览器Web Speech API，具体音色与是否发声取决于浏览器和系统。

## Places

1. 在新Google Sheet中打开Apps Script并复制04文件。
2. 脚本属性添加 `PLACES_API_KEY`。使用自己或明确获准使用的项目；项目需启用Places API (New)并满足结算要求。
3. 修改 `textQuery` 可换搜索词，`pageSize: 5` 表示最多取这一页的5个地点。
4. 运行 `getPlacesReviewsNew`，回表格查看新建的 `Places_...` 页。

老师例子里的 `sheet.clear()` 会清当前活动页；学习版改为成功后新建结果页。示例不自动抓取全部分页，API评论也不是店铺全部评论。代码保留了评论作者及链接；如果另做公开展示，应按Google Maps平台的归属和内容保存要求处理。调用可能产生费用，以项目控制台为准。

## Python：重新计算课堂Excel

需要老师提供的原始Excel，资料包不包含含用户信息的原始记录。打开解压后的 `python` 文件夹，在PowerShell里运行：

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe analyze_cycling.py "C:\你的文件夹\课堂数据.xlsx" --out results
```

将路径换成自己的实际位置。若没有 `py`，使用已安装Python的完整路径创建环境。脚本会校验本课固定月份和4918行，处理其他月份需要相应修改条件。

成功时输出“核对通过”，`results` 内有 `summary.json`、`day-type.png`、`hour-counts.png`、`rain.png`、`hour-duration.png`。没有“下载图表”按钮也没关系，这些文件已在本机文件夹内。

`平日・休日` 沿用源列；小时从 `利用開始日時` 读取。降水数据采用2026年3月完整744小时，包含零利用小时；时长采用 `利用時間`，单位统一为分钟。总量校验失败就停止，不输出猜测结果。

## 常见排错

| 现象 | 先检查 |
| --- | --- |
| `YouTube is not defined` | 左侧服务是否已添加，而不只是复制代码 |
| HTTP 403 | API是否启用、密钥限制和项目权限 |
| HTTP 404 | 模型名称、接口路径、版本及项目可用范围 |
| HTTP 429 | 配额、速率限制或结算状态；不要连续猛点重试 |
| `google is not defined` | 是否直接双击HTML，应该打开部署URL |
| 老师Places例子一直转圈 | 回Google Sheet查看是否在等 `alert` 的OK |
| 图表日文或中文变方框 | 安装CJK字体，或在脚本里指定已安装字体 |
| Python找不到Excel | 带空格的完整路径必须放在英文双引号中 |

本包的本地验证方法与实际结果见论坛文章末尾。真实Google服务调用仍需要自己的账号与权限。
