#!/bin/bash
# 2b. YOLO26 独立环境（可选，训练/用 YOLOv26 时需要）
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 -m venv .venv-yolo26
.venv-yolo26/bin/python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

# 装 torch（与主环境同版本）
.venv-yolo26/bin/python -m pip install "torch==2.4.1" "torchvision==0.19.1" \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 装含 YOLO26 的 ultralytics（GitHub main 分支，pip install git+ 可能 TLS 失败，改用源码包）
.venv-yolo26/bin/python -c "
import urllib.request
urllib.request.urlretrieve(
    'https://codeload.github.com/ultralytics/ultralytics/tar.gz/refs/heads/main',
    'ultralytics-main.tar.gz')
"
tar xzf ultralytics-main.tar.gz
.venv-yolo26/bin/python -m pip install ./ultralytics-main -i https://pypi.tuna.tsinghua.edu.cn/simple
rm -rf ultralytics-main ultralytics-main.tar.gz

# 下载 YOLO26 预训练权重（GitHub 大文件慢/易超时，用 wget 断点续传）
wget -c --tries=8 --timeout=90 \
    -O src/weights/pretrained/yolo26n.pt \
    "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n.pt"

echo "2b. YOLO26 环境就绪"
