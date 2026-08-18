#!/bin/bash
# 2c. YOLOv7 独立环境（可选，跑 YOLOv7 老权重时需要）
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 -m venv .venv-yolov7
.venv-yolov7/bin/python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

# 装 torch（CPU 够用，与主环境同版本）
.venv-yolov7/bin/python -m pip install "torch==2.4.1" "torchvision==0.19.1" \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 装推理所需依赖（YOLOv7 仓库依赖 + ROS 连接）
.venv-yolov7/bin/python -m pip install tqdm thop "protobuf<4.21.3" netifaces \
    rospkg catkin_pkg opencv-python numpy \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 让 venv Python 能找到 ROS 包
site_pkg="$ROOT/.venv-yolov7/lib/python3.*/site-packages"
echo "/opt/ros/noetic/lib/python3/dist-packages" >> $site_pkg/ros.pth
echo "$ROOT/src/perception_ws/devel/lib/python3/dist-packages" >> $site_pkg/ros.pth

echo "2c. YOLOv7 环境就绪"
