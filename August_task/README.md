# FSAC 锥桶检测 — 感知系统

中国大学生无人驾驶方程式大赛（FSAC）感知模块，覆盖 YOLOv8 锥桶检测 → 坐标转换 → ROS 发布全链路。

## 项目结构

```
August_task/
├── ros-pub/                     # ROS1 Noetic catkin 工作空间 ⭐
│   └── src/
│       ├── plumbing_pub_sub/    # 感知主包
│       │   ├── scripts/
│       │   │   └── cone_detector.py     # YOLOv8 检测 ROS 节点
│       │   ├── src/
│       │   │   ├── demo01_sub.cpp       # 像素→车体坐标转换
│       │   │   └── visualization_rviz.cpp # RViz MarkerArray 可视化
│       │   ├── launch/
│       │   │   ├── perception.launch     # 一键全链路启动
│       │   │   └── task.launch           # 旧版测试启动
│       │   └── msg/                      # 自定义消息定义
│       │       ├── ConeInfo.msg          # position(Point) + color
│       │       ├── ConeArray.msg         # Header + ConeInfo[]
│       │       ├── ConeDetection2D.msg   # 2D检测框+置信度
│       │       └── ConeDetection2DArray.msg
│       ├── dnb_msgs/             # pylon_camera 编译依赖(stub)
│       ├── camera_control_msgs/  # 相机控制消息(链接)
│       └── pylon_camera/         # Basler pylon 相机驱动(链接)
├── pylon-ros-camera/             # pylon 相机 ROS 驱动源码
│   ├── pylon_camera/             # 驱动本体
│   └── camera_control_msgs/      # 相机控制消息/服务/动作
├── results/                      # Python 工具脚本
│   ├── bag_info.py               # 查看 ROS bag 话题信息
│   ├── bag_yolo_detect.py        # bag 视频流 YOLO 推理 + MP4
│   ├── extract_frames.py         # 从 bag 抽帧
│   ├── cone_label_tool.py        # 交互式锥桶标注工具(GUI)
│   ├── prepare_dataset.py        # 数据集整理 + 格式转换
│   ├── train_cone.py             # YOLOv8 模型训练
│   └── best.pt                   # 训练好的锥桶模型
├── YOLOv8/
│   └── ultralytics/
│       └── runs/detect/cone_detect/weights/best.pt  # 训练产物
├── requirements.txt              # Python 依赖
└── README.md
```

## 感知数据流

```
📷 图像源 (rosbag / pylon相机)
  ↓
┌──────────────────────────┐
│ cone_detector.py         │  YOLOv8 锥桶检测
│ → /test/camera_cones     │  像素坐标 + 深度估算
└──────────┬───────────────┘
           ↓
┌──────────────────────────┐
│ demo01_sub.cpp           │  相机→车体坐标转换
│ →/yolov7/yolov7/all_cones│  X前 Y左 Z上, base_link
└──────────┬───────────────┘
           ↓  ← 下一组订阅此话题
┌──────────────────────────┐
│ visualization_rviz.cpp   │  MarkerArray 可视化
│ → /visual/cones          │  红蓝锥桶方体
└──────────┬───────────────┘
           ↓
       🖥️ RViz 显示
```

### 接口规范（给下一组）

| 项目 | 值 |
|------|-----|
| 话题 | `/yolov7/yolov7/all_cones` |
| 类型 | `plumbing_pub_sub/ConeArray` |
| 帧 | `base_link` |
| 坐标系 | X=前(m) Y=左(m) Z=上(m) |
| 颜色 | `red_cone` / `blue_cone` / `yellow_cone` |

---

## 环境准备（Ubuntu 20.04 + ROS Noetic）

### 1. ROS 系统依赖

```bash
sudo apt install -y \
    ros-noetic-rosbag ros-noetic-cv-bridge ros-noetic-sensor-msgs \
    ros-noetic-rviz ros-noetic-rviz-visual-tools \
    ros-noetic-camera-info-manager ros-noetic-image-transport \
    ros-noetic-image-geometry ros-noetic-diagnostic-updater \
    ros-noetic-roslint ros-noetic-rospy ros-noetic-tf
```

### 2. pylon 相机驱动 & 依赖 (缺口#2)

```bash
# pylon SDK (必须 v6.x, 推荐 6.2.0)
# 从 Basler 官网下载 pylon_6.2.0.21487-deb0_amd64.deb
sudo dpkg -i pylon_6.2.0.21487-deb0_amd64.deb

# 编译 ROS 工作空间
cd ros-pub
source /opt/ros/noetic/setup.bash
catkin_make
source devel/setup.bash
```

### 3. Python 虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 让 venv Python 能找到 ROS 包
echo "/opt/ros/noetic/lib/python3/dist-packages" >> .venv/lib/python3.*/site-packages/ros.pth
echo "$(pwd)/ros-pub/devel/lib/python3/dist-packages" >> .venv/lib/python3.*/site-packages/ros.pth
```

---

## 🚀 快速启动

### 方式一：一键全链路（推荐）

```bash
# 环境
source /opt/ros/noetic/setup.bash
source ros-pub/devel/setup.bash
export ROS_HOSTNAME=localhost
export ROS_MASTER_URI=http://localhost:11311

# 从 bag 回放检测
roslaunch plumbing_pub_sub perception.launch \
    bag_path:=ros-pub/src/plumbing_pub_sub/bag/2026-07-16-16-56-05.bag \
    model_path:=results/best.pt \
    conf_threshold:=0.3 iou_threshold:=0.45 imgsz:=1280 bag_rate:=0.5

# 用 pylon 相机实时检测（上车后）
roslaunch plumbing_pub_sub perception.launch \
    model_path:=results/best.pt
```

### 方式二：手动分步（调试用）

| 终端 | 命令 |
|------|------|
| 1 | `roscore` |
| 2 | `rosrun plumbing_pub_sub cone_detector.py _model_path:=.../results/best.pt` |
| 3 | `rosbag play .../bag/xxx.bag --topic /pylon_camera_node/image_raw -r 0.5` |
| 4 | `rostopic echo /yolov7/yolov7/all_cones -n 1` |

### 可调参数

| 参数 | 默认 | 说明 |
|------|------|------|
| `conf_threshold` | 0.5 | 置信度, ↓多检出 ↑少但准 |
| `iou_threshold` | 0.45 | NMS重叠阈值 |
| `imgsz` | 1280 | 推理尺寸, 320快 / 640均衡 / 1280高精 |
| `bag_rate` | 0.5 | bag 播放倍速, <1 给推理留时间 |
| `fx/fy` | 1379/1378 | 相机焦距 (标定后填入) |
| `cx/cy` | 984/611 | 相机光心 |
| `camera_x/y/z` | 0.3/0/0.5 | 相机安装位置(m) — 前0.3m, 上0.5m |

---

## 工作流程（数据准备）

```
ROS Bag 录制 → 抽帧提取 → 标注锥桶 → 数据集准备 → 模型训练 → 推理检测
```

### ① 查看 bag 信息
```bash
cd results
python3 bag_info.py <bag文件路径>
```

### ② 抽帧
```bash
python3 extract_frames.py <bag文件路径> --interval 3 --max-frames 150
```

### ③ 标注
```bash
python3 cone_label_tool.py ./frames_to_label
```

### ④ 准备数据集
```bash
python3 prepare_dataset.py ./frames_to_label --labels ./labels --output ./cone_dataset
```

### ⑤ 训练
```bash
python3 train_cone.py --data ./cone_dataset/data.yaml --epochs 100
```

### ⑥ 推理（离线）
```bash
python3 bag_yolo_detect.py <bag文件路径> --model best.pt
```

---

## 🎯 正常使用教程（感知系统日常操作）

### 场景一：用 bag 测试全链路（无相机时）

```bash
# 1. 环境准备（每个终端都要 source）
source /opt/ros/noetic/setup.bash
source ~/桌面/August_task/ros-pub/devel/setup.bash
export ROS_HOSTNAME=localhost
export ROS_MASTER_URI=http://localhost:11311

# 2. 一键启动（roscore + 检测 + 坐标转换 + 可视化 + bag回放）
roslaunch plumbing_pub_sub perception.launch \
    bag_path:=~/桌面/August_task/ros-pub/src/plumbing_pub_sub/bag/2026-07-16-16-56-05.bag \
    model_path:=~/桌面/August_task/results/best.pt
```

**启动后看什么：**
- 终端滚动 YOLO 日志 `检测到 X 个锥桶`
- RViz 弹出，显示红/蓝锥桶方体
- 打开新终端看数据：`rostopic echo /yolov7/yolov7/all_cones -n 1`

### 场景二：上车实时检测（有相机时，无需 pylon C++ SDK）

> 前提：相机必须插 **USB3.0** 口；首次使用需 `pip install pypylon` 到 venv

```bash
# -------- 终端1：启动 ROS Master --------
source /opt/ros/noetic/setup.bash
roscore

# -------- 终端2：启动相机图像桥接 --------
source /opt/ros/noetic/setup.bash
source ~/桌面/git/practice-records-main/August_task/ros-pub/devel/setup.bash
rosrun plumbing_pub_sub pylon_image_publisher.py

# -------- 终端3：启动感知全链路（看到 "开始发布图像" 后执行） --------
source /opt/ros/noetic/setup.bash
source ~/桌面/git/practice-records-main/August_task/ros-pub/devel/setup.bash
roslaunch plumbing_pub_sub perception.launch \
    model_path:=~/桌面/git/practice-records-main/August_task/results/best.pt \
    conf_threshold:=0.3 iou_threshold:=0.5 imgsz:=960
```

**启动后看什么：**
- 终端3 滚动 `=== 接收锥桶: N 个 ===` 日志
- RViz 弹出锥桶 3D 方体（`/visual/cones`），Subcribe `/test/camera_annotated` 可看检测标注画面
- `rostopic echo /yolov7/yolov7/all_cones -n 1` 看锥桶车体坐标

### 场景三：手动分步调试

| 终端 | 命令 | 作用 |
|------|------|------|
| 1 | `roscore` | ROS 大脑 |
| 2 | `~/桌面/August_task/ros-pub/devel/lib/plumbing_pub_sub/cone_detector.py _model_path:=.../best.pt _imgsz:=640` | YOLO 检测 |
| 3 | `rosbag play .../bag/xxx.bag --topic /pylon_camera_node/image_raw -r 0.5` | 喂图像 |
| 4 | `rostopic echo /yolov7/yolov7/all_cones -n 1` | 看锥桶坐标 |

### 调试检测效果（调参）

```bash
# 误检多 → 提高置信度
roslaunch plumbing_pub_sub perception.launch \
    bag_path:=... conf_threshold:=0.7

# 漏检多 → 降低置信度 + 提高分辨率
roslaunch plumbing_pub_sub perception.launch \
    bag_path:=... conf_threshold:=0.25 imgsz:=1280

# 锥桶抖动（重叠框多）→ 提高 IoU
roslaunch plumbing_pub_sub perception.launch \
    bag_path:=... iou_threshold:=0.7

# 推理跟不上 → 降低 bag 倍速
roslaunch plumbing_pub_sub perception.launch \
    bag_path:=... bag_rate:=0.25
```

### 替换新训练模型

```bash
# 训练好的模型放到 results/ 下
roslaunch plumbing_pub_sub perception.launch \
    bag_path:=... \
    model_path:=~/桌面/August_task/results/新模型.pt
```

### 查看感知结果

```bash
# 话题频率（确认在发）
rostopic hz /yolov7/yolov7/all_cones

# 锥桶车体坐标（X前 Y左 Z上）
rostopic echo /yolov7/yolov7/all_cones -n 1

# RViz 可视化话题
rostopic echo /visual/cones -n 1
```

---

## 🔧 日常维护

### 修改代码后重编译

```bash
cd ~/桌面/August_task/ros-pub
catkin_make

# ⚠️ 必做：catkin_make 会重置 Python relay 的 shebang
sed -i '1s|#!/usr/bin/python3|#!/home/xiaoyang/桌面/August_task/.venv/bin/python3|' \
    devel/lib/plumbing_pub_sub/cone_detector.py
```

### 清理 ROS 日志 / 重启

```bash
rosclean purge    # 清日志
killall -9 rosmaster roscore 2>/dev/null  # 强制重启 master
```

### 环境变量（写入 ~/.bashrc 免每次配置）

```bash
echo 'source /opt/ros/noetic/setup.bash' >> ~/.bashrc
echo 'source ~/桌面/August_task/ros-pub/devel/setup.bash' >> ~/.bashrc
echo 'export ROS_HOSTNAME=localhost' >> ~/.bashrc
echo 'export ROS_MASTER_URI=http://localhost:11311' >> ~/.bashrc
```

---

## 🐞 常见问题速查

| 现象 | 原因 | 解决 |
|------|------|------|
| `rosrun: command not found` | venv 污染 PATH | `deactivate` 退出 venv |
| `exit code -9` (进程被杀) | 内存不足 OOM | `imgsz:=320`，关 GUI |
| `rostopic echo` 卡住 | master 挂了 / URI 错 | 确认 `ROS_MASTER_URI=localhost:11311` |
| RViz 没显示 | MarkerArray 话题不对 | 检查 RViz 里 Topic=`/visual/cones` |
| `ModuleNotFoundError: ultralytics` | catkin_make 重置了 relay | 重跑 shebang 修复命令 |
| `rosbag play` 打不开文件 | `~` 没展开 | 用绝对路径或 `$HOME` |
| 锥桶坐标偏斜 | 相机内参/安装未标定 | 重标定后更新 `fx/fy/cx/cy/camera_*` |
