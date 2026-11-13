# Unity VR／AR 实习配套复习材料

课程日期：2026-11-06。整理日期：2026-11-13。

完整教程：https://milo-guo.github.io/bytelife/articles/unity-vr-ar-lab/

这是一份配合教程的脚本与练习包，**不是可直接打开运行的完整 Unity 工程**。课堂模型、动画、材质和原课件不在包中。`PlaceOnPlane.cs` 是本次 APK 构建使用的修正版；其余文件是复习说明。

## 文件用途

| 文件 | 用途 |
| --- | --- |
| `PlaceOnPlane.cs` | 安全读取触摸，在已检测平面内放置指定 Prefab 一次 |
| `01-对象和坐标练习.md` | 理解 Scene、Prefab、层级、局部坐标和地形 |
| `02-人物和相机练习.md` | 核对人物输入、CharacterController、Animator 与相机跟随 |
| `03-AR接线与运行.md` | 逐项连接 ARSession、XR Origin、管理器、相机和两个 Prefab |
| `04-构建和排错速查.md` | Windows 与 Android 输出区别、构建参数和验证步骤 |
| `versions.json` | 本次工程中核对的版本记录，不会自动安装依赖 |

## 使用前提

1. 准备自己的 Unity 工程副本，使用 Unity `6000.3.12f1` 复现这次课程；不直接在唯一原件上试验。
2. 做 Android AR 需在对应 Editor 安装 Android Build Support、SDK & NDK Tools、OpenJDK。
3. 本次实际使用 AR Foundation `6.3.5`、ARCore XR Plugin `6.3.5`、XR Plug-in Management `4.5.4`。
4. 真机要支持 ARCore，并具备所需服务和相机权限。

`PlaceOnPlane.cs` 使用旧 `UnityEngine.Input`。原课堂工程为兼容旧控制器与 XR 新输入而采用 Both，Unity Android 会提示不支持；本次构建成功不代表该输入方案适合所有新项目。请对照正文第 8 节理解历史配置；如果新工程只启用新 Input System，需要先迁移触摸读取，不能只复制脚本就期待它工作。

## 把脚本用到已有课程 AR 工程

1. 先看 `03-AR接线与运行.md`，确认 Session、XR Origin、相机和 ARCore 已配置。
2. 检查工程里是否已有同名 `PlaceOnPlane` 类；如果要替换，备份并只保留一份同名类，避免重复定义。
3. 将脚本导入 Assets，等 Unity 编译完成。
4. 选 XR Origin，把脚本添加到这个对象。确认同一对象有 AR Raycast Manager。
5. 在 `Place On Plane → Spawn Object` 指定要生成的 Base Prefab。
6. 在支持手机上 Build and Run 或安装 APK，允许相机，扫描有纹理平面后点击。

成功的预期是生成一份 Base；第二次点击不再生成。编辑器里仅有鼠标输入并不能凭空产生真实平面，需配置模拟环境或真机测试。

## 验证记录与边界

原课堂完成版记录：Android APK 构建成功、0 个错误、21 条警告；签名、文件对齐、传输哈希、安装和启动验证通过。最后留存的设备检查时相机权限尚未授权，没有实景平面放置成功的完整记录。

本次整理核对了实际代码和场景引用，没有重新启动 Unity 或重建作业。这里的练习步骤没有替读者执行。修改代码、输入系统、尺度或插件后，需要重新构建和真机验证。

## 阅读顺序

先做 01、02，再理解正文的 VR 部分；做手机 AR 时对照 03，最后用 04 检查构建和交付。

原工程路径因人而异，公开材料使用相对目录，不依赖作者电脑用户名。
