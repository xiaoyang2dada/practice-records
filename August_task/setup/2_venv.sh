#!/bin/bash
# 2. 主 Python 虚拟环境（ROS 推理 + YOLOv8 训练）
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
.venv/bin/python -m pip install -r src/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 让 venv Python 能找到 ROS 包
site_pkg="$ROOT/.venv/lib/python3.*/site-packages"
echo "/opt/ros/noetic/lib/python3/dist-packages" >> $site_pkg/ros.pth
echo "$ROOT/src/perception_ws/devel/lib/python3/dist-packages" >> $site_pkg/ros.pth

echo "2. 主环境 .venv 就绪"
