#!/bin/bash
# 一键环境配置入口（分步执行，便于维护）
# 用法：
#   ./setup.sh         全流程（核心步骤 + 询问可选的 YOLO26/YOLOv7）
#   ./setup.sh 1       只跑某一步（1 | 2 | 2b | 2c | 3）
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
SETUP_DIR="$ROOT/setup"

run() {
    echo "运行 $1 ..."
    bash "$SETUP_DIR/$1.sh"
}

# 指定步骤
if [ $# -gt 0 ]; then
    case "$1" in
        1) run 1_ros ;;
        2) run 2_venv ;;
        2b) run 2b_yolo26 ;;
        2c) run 2c_yolov7 ;;
        3) run 3_build ;;
        *) echo "用法: ./setup.sh [1|2|2b|2c|3]"; exit 1 ;;
    esac
    echo "完成"
    exit 0
fi

# 全流程：核心步骤
run 1_ros
run 2_venv
run 3_build

# 可选步骤
read -p "需要配置 YOLO26 环境吗？(y/N) " ans
if [[ "$ans" =~ ^[Yy]$ ]]; then run 2b_yolo26; fi

read -p "需要配置 YOLOv7 环境吗？(y/N) " ans
if [[ "$ans" =~ ^[Yy]$ ]]; then run 2c_yolov7; fi

echo "全部完成"
