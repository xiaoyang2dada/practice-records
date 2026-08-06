#!/bin/bash
# cone_detector.sh — venv 环境包装脚本
# 确保使用 venv Python 运行 cone_detector.py，同时能访问 ROS 包
exec /home/xiaoyang/桌面/August_task/.venv/bin/python3 \
    /home/xiaoyang/桌面/August_task/ros-pub/src/plumbing_pub_sub/scripts/cone_detector.py \
    "$@"
