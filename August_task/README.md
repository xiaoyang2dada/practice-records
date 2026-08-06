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