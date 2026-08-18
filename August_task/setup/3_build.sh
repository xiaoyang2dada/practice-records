#!/bin/bash
# 3. 编译工作空间 + 修复 relay shebang
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/src/perception_ws"

source /opt/ros/noetic/setup.bash
catkin_make --only-pkg-with-deps main_pkg dnb_msgs camera_control_msgs

# 修复 Python relay 的 shebang（主环境）
VENV="$ROOT/.venv/bin/python3"
sed -i "1s|#!/usr/bin/python3|#!$VENV|" \
    devel/lib/main_pkg/cone_detector.py \
    devel/lib/main_pkg/pylon_image_publisher.py

# YOLOv7 节点用 .venv-yolov7（若存在）
if [ -x "$ROOT/.venv-yolov7/bin/python3" ]; then
    VENV7="$ROOT/.venv-yolov7/bin/python3"
    sed -i "1s|#!/usr/bin/python3|#!$VENV7|" devel/lib/main_pkg/cone_detector_v7.py
fi

echo "3. 编译完成"
