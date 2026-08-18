# FSAC 锥桶检测 — 感知系统

中国大学生无人驾驶方程式大赛（FSAC）感知模块，覆盖 YOLOv8 锥桶检测 → 坐标转换 → ROS 发布全链路。

## 文档导航

| 文档 | 内容 |
|------|------|
| [**`README.md`**](README.md) | 本文件：系统搭建、快速启动、流程总览 |
| [**`src/main_pkg/bag/README.md`**](src/main_pkg/bag/README.md) | bag 数据获取、全链路测试、从 bag 制作数据集 |
| [**`src/models/README.md`**](src/models/README.md) | 模型训练环境与训练流程 |


## 环境准备（Ubuntu 20.04 + ROS Noetic）

> **快捷方式（推荐）**：直接用 `setup` 脚本一键配置（含可选的 YOLO26/YOLOv7 环境）：
> ```bash
> cd ~/桌面/git/practice-records-main/August_task   # 改成你的实际路径
> ./setup.sh          # 全流程（会询问是否配置 YOLO26/YOLOv7）
> ./setup.sh 2b       # 也可只跑某一步（1 | 2 | 2b | 2c | 3）
> ```

<details>
<summary>手动步骤（可选，未用 setup 脚本时再看）</summary>

> 以下步骤默认在项目根目录 `August_task/` 下执行，先 `cd` 进来：
> ```bash
> cd ~/桌面/git/practice-records-main/August_task   # 改成你的实际路径
> ```

### 1. ROS 系统依赖

```bash
sudo apt install -y \
    ros-noetic-rosbag ros-noetic-cv-bridge ros-noetic-sensor-msgs \
    ros-noetic-rviz ros-noetic-camera-info-manager \
    ros-noetic-image-transport ros-noetic-image-geometry \
    ros-noetic-diagnostic-updater ros-noetic-roslint \
    ros-noetic-rospy ros-noetic-tf
```

### 2. Python 虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r src/requirements.txt

# 让 venv Python 能找到 ROS 包
echo "/opt/ros/noetic/lib/python3/dist-packages" >> .venv/lib/python3.*/site-packages/ros.pth
echo "$(pwd)/src/perception_ws/devel/lib/python3/dist-packages" >> .venv/lib/python3.*/site-packages/ros.pth
```

> **只用训练好的模型跑系统？** 到此为止即可，无需配置任何训练环境。
> 装 ultralytics 时 torch 等会自动带上，主环境 `.venv` 既能推理（用 `src/weights/trained/` 下的 best.pt），也能训练 YOLOv8。
> 需要自己训练模型或者要使用YOLO的其他版本模型时，见 [**`src/models/README.md`**](src/models/README.md)。

### 3. 编译工作空间

```bash
cd src/perception_ws
source /opt/ros/noetic/setup.bash
catkin_make --only-pkg-with-deps main_pkg dnb_msgs camera_control_msgs

# 必做：修复 Python relay 的 shebang，否则找不到 ultralytics/pypylon
VENV=$(cd ../.. && pwd)/.venv/bin/python3
sed -i "1s|#!/usr/bin/python3|#!$VENV|" \
    devel/lib/main_pkg/cone_detector.py \
    devel/lib/main_pkg/pylon_image_publisher.py

# YOLOv7 节点用 .venv-yolov7（若要用 v7 链路）
VENV7=$(cd ../.. && pwd)/.venv-yolov7/bin/python3
sed -i "1s|#!/usr/bin/python3|#!$VENV7|" \
    devel/lib/main_pkg/cone_detector_v7.py
```

</details>

---

## 快速启动

> 所有命令在 **项目根目录**（August_task/）下执行。先 `cd` 进来：
> ```bash
> cd ~/桌面/git/practice-records-main/August_task   # 改成你的实际路径
> ```

### 场景一：用 bag 测试全链路（无相机时）

```bash
# 环境（每个终端都要先 cd 到项目根目录）
source /opt/ros/noetic/setup.bash
source src/perception_ws/devel/setup.bash
export ROS_HOSTNAME=localhost
export ROS_MASTER_URI=http://localhost:11311

# 一键启动
# bag 文件需自备（4.7GB 不上传 GitHub），放入 src/main_pkg/bag/ 后替换下方路径
roslaunch main_pkg perception.launch \
    bag_path:=src/main_pkg/bag/<你的bag文件.bag> \
    model_path:=src/weights/trained/YOLOv8/best.pt \
    conf_threshold:=0.4 iou_threshold:=0.55 imgsz:=960 bag_rate:=1.0
```

**启动后看什么：**
- 终端滚动 `=== 接收锥桶: N 个 ===` 日志
- RViz 弹出，显示红/蓝锥桶方体
- 新终端看数据：`rostopic echo /yolov7/yolov7/all_cones -n 1`

### 场景一b：用 YOLOv7 权重检测（预留模型）

> 与场景一同链路，仅检测节点换成 `cone_detector_v7`（用 `.venv-yolov7`），
> 权重为 `src/weights/trained/YOLOv7/best.pt`（预留模型，本地保留、未随仓库上传，需自行放置），默认 conf=0.3 / iou=0.45 / imgsz=640。

```bash
source /opt/ros/noetic/setup.bash
source src/perception_ws/devel/setup.bash
export ROS_HOSTNAME=localhost
export ROS_MASTER_URI=http://localhost:11311

roslaunch main_pkg perception_v7.launch \
    bag_path:=src/main_pkg/bag/<你的bag文件.bag> \
    model_path:=src/weights/trained/YOLOv7/best.pt \
    conf_threshold:=0.3 iou_threshold:=0.45 imgsz:=640 bag_rate:=1.0
```

**启动后看什么：**
- 终端滚动 `=== 接收锥桶: N 个 ===` 日志（每帧 10~20 个为正常，视场景而定）
- RViz 红/蓝/黄锥桶方体；`rostopic echo /yolov7/yolov7/all_cones -n 1` 看坐标

### 场景二：上车实时检测（有相机时，无需 pylon C++ SDK）

> 前提：相机必须插 **USB3.0** 口；首次需 `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r src/requirements.txt`
> 所有终端先 `cd` 到项目根目录

```bash
# 终端1：ROS Master
source /opt/ros/noetic/setup.bash
roscore
```

```bash
# 终端2：相机图像桥接
source /opt/ros/noetic/setup.bash
source src/perception_ws/devel/setup.bash
rosrun main_pkg pylon_image_publisher.py
```

```bash
# 终端3：感知全链路（看到 "开始发布图像" 后执行）
source /opt/ros/noetic/setup.bash
source src/perception_ws/devel/setup.bash
roslaunch main_pkg perception.launch \
    model_path:=src/weights/trained/YOLOv8/best.pt \
    conf_threshold:=0.4 iou_threshold:=0.55 imgsz:=960
```

**启动后看什么：**
- 终端3 滚动 `=== 接收锥桶: N 个 ===` 日志
- RViz 锥桶 3D 方体，Subcribe `/test/camera_annotated` 看检测标注画面
- `rostopic echo /yolov7/yolov7/all_cones -n 1` 看坐标

### 可调参数

| 参数 | 默认 | 说明 |
|------|------|------|
| `conf_threshold` | 0.4 | 置信度, ↓多检出 ↑少但准 |
| `iou_threshold` | 0.55 | NMS重叠阈值 |
| `imgsz` | 960 | 推理尺寸, 640均衡 / 960高精 |
| `bag_rate` | 1.0 | bag 播放倍速, <1 给推理留时间 |
| `fx/fy` | 1379/1378 | 相机焦距 (标定后填入) |
| `cx/cy` | 984/611 | 相机光心 |
| `camera_x/y/z` | 0.3/0/0.5 | 相机安装位置(m) |

---

## 工作流程（数据准备）

```
ROS Bag 录制 → 抽帧提取 → 标注锥桶 → 数据集准备 → 模型训练 → 推理检测
```

> **只用训练好的模型跑系统？** 跳过数据准备与训练，直接用 `src/weights/trained/` 下的 best.pt 推理即可（见「快速启动」）。
> 完整流程（①~⑥）仅当你要**从零制作数据集并自己训练**时才需要。
> - ①~④ 从 bag 制作数据集：见 [**`src/main_pkg/bag/README.md`**](src/main_pkg/bag/README.md)
> - ⑤ 模型训练：见 [**`src/models/README.md`**](src/models/README.md)
> - ⑥ 离线推理：下方命令（在项目根目录执行）

```bash
cd src/tools

# ⑥ 推理（离线）
python3 bag_yolo_detect.py <bag文件路径> --model ../weights/trained/YOLOv8/best.pt
```

---

## 日常维护

> 所有命令在项目根目录下执行

### 修改代码后重编译

```bash
cd src/perception_ws
source /opt/ros/noetic/setup.bash
catkin_make --only-pkg-with-deps main_pkg

# 必做：修复 relay shebang 即让程序找到虚拟环境
VENV=$(cd ../.. && pwd)/.venv/bin/python3
sed -i "1s|#!/usr/bin/python3|#!$VENV|" \
    devel/lib/main_pkg/cone_detector.py \
    devel/lib/main_pkg/pylon_image_publisher.py
```

### 替换新训练模型

```bash
# 训练好的 best.pt 放入 src/weights/trained/ 后
roslaunch main_pkg perception.launch \
    model_path:=src/weights/trained/YOLOv8/best.pt
```

### 清理 / 重启

```bash
rosclean purge                          # 清日志
killall -9 roslaunch rosmaster roscore  # 强制重启 master（每次启动前建议执行）
```

### 环境变量（写入 ~/.bashrc 免每次配置）

在项目根目录下执行：
```bash
PROJ=$(pwd)
echo 'source /opt/ros/noetic/setup.bash' >> ~/.bashrc
echo "source $PROJ/src/perception_ws/devel/setup.bash" >> ~/.bashrc
echo 'export ROS_HOSTNAME=localhost' >> ~/.bashrc
echo 'export ROS_MASTER_URI=http://localhost:11311' >> ~/.bashrc
```

---

## 项目结构

```
August_task/
├── src/                        # 统一代码目录
│   ├── main_pkg/               # 主包部分
│   │   ├── launch/perception.launch   # 一键全链路启动
│   │   ├── scripts/                   
│   │   │   ├── cone_detector.py,
│   │   │   ├── pylon_image_publisher.py
│   │   │   ├── cone_detector.sh  # 手动调试用
│   │   ├── cpp/                       
│   │   │   ├── demo01_sub.cpp
│   │   │   ├── visualization_rviz.cpp
│   │   ├── msg/                # 自定义消息
│   │   ├── bag/                # bag 数据放这！
│   │   └── rviz/config.rviz    # RViz配置文件
│   ├── perception_ws/          # 工作空间
│   │   └── src/main_pkg → ../../main_pkg
│   ├── tools
│   │   ├── bag_yolo_detect.py  # bag 视频流推理
│   │   ├── cone_label_tool.py  # 交互式锥桶标注
│   │   ├── extract_frames.py   # 抽帧
│   │   ├── prepare_dataset.py / prepare_voc_dataset.py
│   ├── models                  # 各模型训练入口
│   │   ├── YOLOv8/train.py     # YOLOv8 训练脚本（主环境 .venv）
│   │   │   └── ultralytics/camera_detect.py
│   │   ├── YOLOv26/train.py    # YOLOv26 训练脚本（独立环境 .venv-yolo26）
│   │   │   └── ultralytics/camera_detect.py
│   │   └── YOLOv7/
│   │       ├── train.py                  # YOLOv7 训练脚本（独立环境 .venv-yolov7）
│   │       └── ultralytics/camera_detect_v7.py  # YOLOv7 单图调试脚本
│   ├── lib
│   │   └── yolov7/            # 官方 YOLOv7 仓库（WongKinYiu/yolov7）源码库
│   ├── weights                 # 模型权重
│   │   ├── trained/YOLOv8/best.pt   # YOLOv8 训练好的锥桶模型
│   │   ├── trained/YOLOv7/best.pt   # YOLOv7 训练好的锥桶模型（预留，本地保留，未随仓库上传）
│   │   ├── trained/YOLOv26/         # YOLOv26 训练输出
│   │   └── pretrained/              # 预训练权重 yolov8n.pt / yolo26n.pt
│   └── requirements.txt
```

## 感知数据流

```
图像源 (rosbag / pylon相机)
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
           ↓
┌──────────────────────────┐
│ visualization_rviz.cpp   │  MarkerArray 可视化
│ → /visual/cones          │  红蓝锥桶方体
└──────────┬───────────────┘
           ↓
       RViz 显示
```

### 接口规范（给下一组）

| 项目 | 值 |
|------|-----|
| 话题 | `/yolov7/yolov7/all_cones` |
| 类型 | `main_pkg/ConeArray` |
| 帧 | `base_link` |
| 坐标系 | X=前(m) Y=左(m) Z=上(m) |
| 颜色 | `red_cone` / `blue_cone` / `yellow_cone` |

---