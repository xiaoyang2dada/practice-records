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
│   │   ├── trained/YOLOv7/best.pt   # YOLOv7 训练好的锥桶模型
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

> **只用训练好的模型跑系统？** 到此为止即可，无需配置任何训练环境。
> 装 ultralytics 时 torch 等会自动带上，主环境 `.venv` 既能推理（用 `src/weights/trained/` 下的 best.pt），也能训练 YOLOv8。
> 需要自己训练模型时，再看下方「训练者配置（可选）」。

### 2a. 训练者配置（可选）

> 仅当你需要**自己训练/微调模型**时才需要看这节。普通用户跳过。

- **训练 YOLOv8**：直接用主环境 `.venv`（第 2 步已装好），按「工作流程」第 ⑤ 步操作即可，无需额外配置。
- **训练 YOLOv26**：需要额外独立环境 `.venv-yolo26`（因 YOLO26 架构只在 GitHub main 版 ultralytics 中），见下方「2b」。

### 2b. YOLO26 独立环境（可选，仅训练/用 YOLOv26 时需要）

> YOLO26 目前**不在 PyPI**（最新 PyPI 版不含 yolo26 模型），只在 ultralytics 的 GitHub main 分支。
> 为保证不破坏主环境 `.venv`（ROS 管线 + YOLOv8），单独建 `.venv-yolo26`，二者互不影响。

```bash
cd August_task

# 1. 创建独立环境
python3 -m venv .venv-yolo26
.venv-yolo26/bin/python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

# 2. 装 torch（与主环境同版本）
.venv-yolo26/bin/python -m pip install "torch==2.4.1" "torchvision==0.19.1" \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 装含 YOLO26 的 ultralytics（GitHub main 分支，pip install git+ 可能 TLS 失败，改用源码包）
.venv-yolo26/bin/python -c "
import urllib.request
urllib.request.urlretrieve(
    'https://codeload.github.com/ultralytics/ultralytics/tar.gz/refs/heads/main',
    'ultralytics-main.tar.gz')
"
tar xzf ultralytics-main.tar.gz
.venv-yolo26/bin/python -m pip install ./ultralytics-main -i https://pypi.tuna.tsinghua.edu.cn/simple
rm -rf ultralytics-main ultralytics-main.tar.gz

# 4. 下载 YOLO26 预训练权重（GitHub 大文件慢/易超时，用 wget 断点续传）
wget -c --tries=8 --timeout=90 \
    -O src/weights/pretrained/yolo26n.pt \
    "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n.pt"
```

> 说明：`yolo26n.pt` 是 COCO 预训练（80 类），用于训练锥桶需用 `train.py` 微调；
> 训练完权重自动输出到 `src/weights/trained/YOLOv26/`。

### 2c. YOLOv7 独立环境（可选，跑 YOLOv7 老权重时需要）

> 学长的 YOLOv7 权重（`src/weights/trained/YOLOv7/best.pt`）需要官方 YOLOv7 推理代码（已放好：`src/lib/yolov7`），
> 与 ultralytics 的 YOLOv8 推理接口不同，因此单独建 `.venv-yolov7`，二者互不影响。
> 只跑 YOLOv8/YOLOv26 的话可跳过本节。

```bash
# 1. 创建独立环境
python3 -m venv .venv-yolov7
.venv-yolov7/bin/python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

# 2. 装 torch（CPU 够用，与主环境同版本）
.venv-yolov7/bin/python -m pip install "torch==2.4.1" "torchvision==0.19.1" \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 装推理所需依赖（YOLOv7 仓库依赖 + ROS 连接）
.venv-yolov7/bin/python -m pip install tqdm thop "protobuf<4.21.3" netifaces \
    rospkg catkin_pkg opencv-python numpy \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 4. 让 venv Python 能找到 ROS 包（同主环境做法）
echo "/opt/ros/noetic/lib/python3/dist-packages" >> .venv-yolov7/lib/python3.8/site-packages/ros.pth
echo "$(pwd)/src/perception_ws/devel/lib/python3/dist-packages" >> .venv-yolov7/lib/python3.8/site-packages/ros.pth
```

> 说明：官方 YOLOv7 的权重文件是 74MB 的 best.pt，已放到 `src/weights/trained/YOLOv7/`，类别为红/蓝/黄三色锥桶。
> 推理脚本 `camera_detect_v7.py` 与 v8 的 `camera_detect.py` 用法一致。

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
> 权重为 `src/weights/trained/YOLOv7/best.pt`，默认 conf=0.3 / iou=0.45 / imgsz=640。

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

> **只用训练好的模型跑系统？** 跳过 ①~⑤，直接用 `src/weights/trained/` 下的 best.pt 推理即可（见「快速启动」）。
> 完整流程（①~⑥）仅当你要**从零制作数据集并自己训练**时才需要。
> 注意：以下命令均在项目根目录 `August_task/` 下执行，先 `cd` 进来。

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

# ⑤ 训练 YOLOv8（模型输出到 weights/trained/YOLOv8/）
python3 models/YOLOv8/train.py --data ./cone_dataset/data.yaml --epochs 100

# ⑤b 训练 YOLOv26（需独立环境 .venv-yolo26，输出到 weights/trained/YOLOv26/）
.venv-yolo26/bin/python src/models/YOLOv26/train.py --data ./cone_dataset/data.yaml --epochs 100

# ⑤c 训练/微调 YOLOv7（需独立环境 .venv-yolov7，输出到 weights/trained/YOLOv7/）
.venv-yolov7/bin/python src/models/YOLOv7/train.py --data ./cone_dataset/data.yaml --epochs 100

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

## 常见问题速查

| 现象 | 原因 | 解决 |
|------|------|------|
| `rosrun: command not found` | venv 污染 PATH | `deactivate` 退出 venv |
| `exit code -9` (进程被杀) | 内存不足 OOM | `imgsz:=640`，关 GUI |
| `rostopic echo` 卡住 | master 挂了 / URI 错 | 确认 `ROS_MASTER_URI=localhost:11311` |
| RViz 没显示锥桶 | 话题/节点没启动 | 检查 `/visual/cones` + 重启前 `killall -9 roslaunch` |
| `ModuleNotFoundError: ultralytics` | catkin_make 重置 relay | 重跑 shebang 修复命令 |
| v7 节点报 `KeyError: 16` / cv_bridge 错 | .venv-yolov7 新版 OpenCV 与 ros cv_bridge 不兼容 | 已改为手动构造 Image，重新 catkin_make + 修复 relay |
| v7 加载权重报找不到文件（路径含大写） | 官方 attempt_download 会小写化路径 | 已用自定义 load_model，勿改权重路径大小写 |
| v7 检测框巨大/错位 | 双重 xywh2xyxy 转换（NMS 内部已转一次） | 已修复：原始 pred 直接传 NMS + letterbox/scale_coords |
| 每帧检测 300+ 个 | letterbox/坐标处理错误 | 已用官方 detect.py 流程（已修复） |
| `YOLO('yolo26n.pt')` 报不认识该模型 | PyPI 版 ultralytics 不含 YOLO26 | 用 `.venv-yolo26` 环境（含 GitHub main 分支版），见「2b」 |
| `rosbag play` 打不开文件 | `~` 没展开 / bag 未索引 | 用绝对路径；`rosbag reindex <文件>` |
| 相机无画面 | USB2.0 / 相机被占用 | 换 USB3.0 口；`pkill -9 -f pylon` 后重试 |
| 锥桶坐标偏斜 | 相机内参/安装未标定 | 更新 `fx/fy/cx/cy/camera_*` |
