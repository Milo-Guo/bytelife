# 信息学实习 B：计算器、人物检测与 3D 点云复现包

课程日期：2026-10-23。中文解析：https://milo-guo.github.io/bytelife/articles/colab-ai-spatial-lab/

## 文件与对应关系

| 文件 | 用途 |
| --- | --- |
| calc.py | 加法、乘法计算器完成版 |
| camera_input.py | 摄像头拍照后进行 YOLO 物体检测，完成版 |
| human_detect.py | 上传 MP4，逐帧只检测人，输出视频和人数曲线，完成版 |
| pointcloud.py | 课程原始完整点云程序，按原样保留 |
| 四份 .ipynb | 公开复现版：明确安装依赖、挂载 Drive、编辑脚本、隐藏输入令牌、启动和停止 |
| launch_colab.py | 新增的课堂启动辅助脚本，检测端口和网页响应，不结束别的进程 |
| work_space_video.mp4 | 原课程示例视频，1280×720、30 FPS、601 帧 |
| building1_garden.ply | 原课程彩色点云，651990 个顶点 |
| originals/ | 三个未完成模板、四份清空令牌和输出的原课件笔记本，供比较；复现优先运行上层完成版 |
| verify_materials.py | 数据完整性、语法与点云核心函数验证，不加载 YOLO 模型 |
| SHA256SUMS.txt | 本包文件的 SHA-256 清单（不含清单自身） |

## 最省事：在 Google Colab 运行

1. 解压 ZIP，把 `colab-ai-spatial-2026` 整个文件夹上传到 Google Drive 的“我的云端硬盘（My Drive）”。不要只上传 .ipynb。
2. 打开 https://colab.research.google.com/ ，选择 `File → Upload notebook`（文件→上传笔记本），按章节打开对应 .ipynb。
3. 依次执行安装依赖、挂载 Drive、切换文件夹、查看代码单元。挂载时用自己账号授权。若目录不同，修改 `os.chdir(...)`，用目录输出确认文件存在。
4. 在 https://dashboard.ngrok.com/get-started/your-authtoken 取得自己账号的 authtoken。执行启动单元后在隐藏输入框粘贴；不写入公开代码或笔记本输出。
5. 打开输出的 HTTPS ngrok 地址；出现 ngrok 提示页时，确认地址后点 `Visit Site`。首次 YOLO 自动下载 `yolov8s.pt`，需要联网。
6. 摄像头课题：允许浏览器摄像头权限，点击 `Take photo` 拍照；视频课题：上传本包 MP4；点云课题：上传 PLY，先点①，再点②。
7. 切换课题之前执行最后的 `stop_app(...)` 单元。只关闭浏览器标签并不会停止云端服务。

四份笔记本依次对应：序章→calc.py，第１章v1→camera_input.py，第１章v2→human_detect.py，第２章→pointcloud.py。

点云默认 10000 点；本次课堂调参使用 100000 点、点大小 1、迭代 2000、距离 0.020、角度 10°。参数只是该样例的可用起点，随机算法每次结果可能有变化。

## 在 Windows 本机运行

先安装支持这些库的 Python 3（建议先用 Python 3.11 或 3.12 创建独立环境）、FFmpeg，并确保 ffmpeg 能在终端找到。打开 PowerShell，进入解压文件夹：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
ffmpeg -version
.\.venv\Scripts\python.exe -m streamlit run calc.py
```

如果没有 Python 3.12，先用 `py --list` 查看已装版本；不要照抄不存在的版本。浏览器打开终端给出的 `http://localhost:8501`。在本机运行时 localhost 就是本机，通常不需要 ngrok。

在终端按 Ctrl+C 停止，再把最后一条命令的文件名换成 camera_input.py、human_detect.py 或 pointcloud.py。摄像头应在 localhost/HTTPS 下使用；摄像头权限由浏览器管理。

## 如何确认成功

- 计算器：数字 2 和 4，`掛け算`，输出 8。
- 摄像头：拍照后显示原图和带检测框的输出图；照片中若没检测出对象，也可能没有框。
- 视频：处理进度结束后可播放带框视频，并出现横轴秒、纵轴人数的折线图。输出视频不保留原音轨。
- 点云：读取显示 651,990 点；①后出现 3D 场景，②后部分近水平面标红，可拖动旋转。
- 验证包：`python verify_materials.py`，成功显示完整性、语法、采样和 RANSAC 检查通过。

## 出错先检查

- 找不到文件：确认 os.chdir 的目录、文件名和 Drive 上传是否完成。
- 只有标题：确认云端打开的是上层完成版 .py，保存后点击网页 Rerun。
- ngrok 8012：检查 Colab `/content/logs.txt`，确认 Streamlit 端口和隧道一致；先检查服务，再刷新 HTTPS 地址。
- 8501 被占用：先执行上一份笔记本的 stop_app；不要一口气运行四份的启动单元。
- 视频转换失败：先检查 `ffmpeg -version` 和磁盘剩余空间；不要仅安装名叫 ffmpeg 的 Python 包。
- 点云只红一部分：阈值决定平面厚度，台阶/斜坡不在同一平面；保持同一采样再比较参数。

## 复现范围与来源

四个应用已在本次课堂 Colab 中实际使用；打包后另做语法、哈希、数据格式及点云核心算法检查。新增启动器经过静态检查和本机受控启动/停止测试；新环境仍可能需要按库和平台更新调整依赖。

本包不是离线镜像：首次安装依赖及 YOLO 权重需要联网。requirements.txt 列出直接依赖，没有假装提供完整锁定环境。课堂观察到 Python 3.13、Streamlit 1.66.1、pyngrok 9.0.2、Ultralytics 8.4.184、NumPy 2.1.3、pandas 2.2.3、OpenCV 5.0.0.93；这是当时环境记录，不代表其他环境唯一可用版本，也不是全量 pip freeze。

程序及视频/点云素材源于《情報学実習B》课程配布资料；PLY 文件头标注由 Scaniverse 创建。中文说明、补全代码、启动器与验证脚本为本次学习整理。保留原有日文注释，未另行改变原素材许可。个人照片、课程账号、真实 ngrok 令牌和完整讲义 PDF 不在复现包中。

Colab 运行时会回收；这个流程用于课堂实验。长期运行的 Web 应用应放到适合持续部署的平台，并按 Colab 当前资源规则使用。
