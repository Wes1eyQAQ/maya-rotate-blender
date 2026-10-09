# Maya Rotate：Blender 旋转球

让控制器原地旋转，减少正交视角下拖动旋转圆环的跳变。

[English](README.md) · [安装包 v1.9.1](downloads/StableRotate-1.9.1.zip) · [使用指南](docs/USER_GUIDE.zh-CN.md)

## 主要功能

- 红绿蓝圆环控制轴向旋转；圆环侧对视角时使用连续拖动，减少鼠标穿过中心造成的 180° 跳变。
- 拖动球内区域进行自由三维旋转；黄色外圈绕当前视线旋转。
- 只负责旋转，保留位置与缩放；同时选中多个控制器时各自原地转动。
- 激活此工具后，按 + / - 调整球的大小；支持数字小键盘。
- 可调整透明度、颜色饱和度、线条粗细，保留悬停高亮。
- Shift 精细调整，Esc 或右键取消；支持物体与姿态模式。
- 支持全局、局部、视图及自定义工具坐标方向。其他方向类型当前回退到全局。
- 开启 Blender 自动打帧时，确认操作只插入旋转关键帧。
- 默认英文，按钮循环切换英文、中文和日文，与配套 Maya 工具共用语言偏好。

## 安装

下载 **StableRotate-1.9.1.zip**，在 Blender 的 Edit → Preferences → Add-ons → Install from Disk 安装，启用 **Stable Axis Rotate**。

选择物体或姿态骨骼，在 3D 视图按 N，打开 **Maya → Stable Rotate**，点击 **Use Maya Rotate 1.9**。仅启用插件不会自动切换到此工具。升级后重启 Blender，避免旧代码继续运行。

已验证环境：Windows / Blender 4.4.3 / 64 位；其他版本和平台尚未验证。插件不修改骨骼静置轴向；现有约束、驱动和父子关系仍可能影响最终姿态。多个目标始终各自原地旋转，不会绕共享枢轴公转。

许可证：GPL-3.0-or-later。独立社区项目，与 Autodesk、Blender Foundation 无隶属关系。
