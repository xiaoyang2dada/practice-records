# FSAC 锥桶检测 — 感知系统

中国大学生无人驾驶方程式大赛（FSAC）感知模块，覆盖 YOLOv8 锥桶检测 → 坐标转换 → ROS 发布全链路。

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
│   │   ├── YOLOv8/train.py     # YOLOv8 训练脚本
│   │   │   └── ultralytics/camera_detect.py
│   ├── weights                 # 模型权重
│   │   ├── trained/YOLOv8/best.pt   # 训练好的锥桶模型
│   │   └── pretrained/yolov8n.pt
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

## 环境准备（Ubuntu 20.04 + ROS Noetic）

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
cd August_task
python3 -m venv .venv
source .venv/bin/activate
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r src/requirements.txt

# 让 venv Python 能找到 ROS 包
echo "/opt/ros/noetic/lib/python3/dist-packages" >> .venv/lib/python3.*/site-packages/ros.pth
echo "$(pwd)/src/perception_ws/devel/lib/python3/dist-packages" >> .venv/lib/python3.*/site-packages/ros.pth
```

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
```

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
    conf_threshold:=0.3 iou_threshold:=0.5 imgsz:=960 bag_rate:=0.5
```

**启动后看什么：**
- 终端滚动 `=== 接收锥桶: N 个 ===` 日志
- RViz 弹出，显示红/蓝锥桶方体
- 新终端看数据：`rostopic echo /yolov7/yolov7/all_cones -n 1`

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
    conf_threshold:=0.3 iou_threshold:=0.5 imgsz:=960
```

**启动后看什么：**
- 终端3 滚动 `=== 接收锥桶: N 个 ===` 日志
- RViz 锥桶 3D 方体，Subcribe `/test/camera_annotated` 看检测标注画面
- `rostopic echo /yolov7/yolov7/all_cones -n 1` 看坐标

### 可调参数

| 参数 | 默认 | 说明 |
|------|------|------|
| `conf_threshold` | 0.5 | 置信度, ↓多检出 ↑少但准 |
| `iou_threshold` | 0.45 | NMS重叠阈值 |
| `imgsz` | 1280 | 推理尺寸, 640均衡 / 960高精 |
| `bag_rate` | 0.5 | bag 播放倍速, <1 给推理留时间 |
| `fx/fy` | 1379/1378 | 相机焦距 (标定后填入) |
| `cx/cy` | 984/611 | 相机光心 |
| `camera_x/y/z` | 0.3/0/0.5 | 相机安装位置(m) |

---

## 工作流程（数据准备）

```
ROS Bag 录制 → 抽帧提取 → 标注锥桶 → 数据集准备 → 模型训练 → 推理检测
```

```bash
cd src/tools

# ① 查看 bag 信息
python3 bag_info.py <bag文件路径>

# ② 抽帧
python3 extract_frames.py <bag文件路径> --interval 3 --max-frames 150

# ③ 标注
python3 cone_label_tool.py ./frames_to_label

# ④ 准备数据集
python3 prepare_dataset.py ./frames_to_label --labels ./labels --output ./cone_dataset

# ⑤ 训练（模型输出到 weights/trained/YOLOv8/）
python3 models/YOLOv8/train.py --data ./cone_dataset/data.yaml --epochs 100

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

# 必做：修复 relay shebang
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

## 常见问题速查

| 现象 | 原因 | 解决 |
|------|------|------|
| `rosrun: command not found` | venv 污染 PATH | `deactivate` 退出 venv |
| `exit code -9` (进程被杀) | 内存不足 OOM | `imgsz:=640`，关 GUI |
| `rostopic echo` 卡住 | master 挂了 / URI 错 | 确认 `ROS_MASTER_URI=localhost:11311` |
| RViz 没显示锥桶 | 话题/节点没启动 | 检查 `/visual/cones` + 重启前 `killall -9 roslaunch` |
| `ModuleNotFoundError: ultralytics` | catkin_make 重置 relay | 重跑 shebang 修复命令 |
| `rosbag play` 打不开文件 | `~` 没展开 / bag 未索引 | 用绝对路径；`rosbag reindex <文件>` |
| 相机无画面 | USB2.0 / 相机被占用 | 换 USB3.0 口；`pkill -9 -f pylon` 后重试 |
| 锥桶坐标偏斜 | 相机内参/安装未标定 | 更新 `fx/fy/cx/cy/camera_*` |
