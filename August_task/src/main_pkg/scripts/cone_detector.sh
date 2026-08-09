#!/bin/bash
# cone_detector.sh — venv 环境包装脚本
# 确保使用 venv Python 运行 cone_detector.py，同时能访问 ROS 包
# 相对定位：scripts/ → ../../..  =  August_task/ 根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
exec "$ROOT_DIR/.venv/bin/python3" \
    "$SCRIPT_DIR/cone_detector.py" \
    "$@"
