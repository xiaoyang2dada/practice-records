# 模型训练文档

本文档涵盖各模型（YOLOv8 / YOLOv26 / YOLOv7）的训练环境配置与训练流程。
主 README 的「环境准备」只保留跑通系统所需的部分，训练相关均在此处。

> 阅读顺序：主 README（搭系统环境）→ bag/README（制作数据集）→ 本文件（训练）。
> 返回总览见 [**`../../README.md`**](../../README.md)。

## 模型结构

```
src/models/
├── YOLOv8/train.py                  # YOLOv8 训练脚本（主环境 .venv）
│   └── ultralytics/camera_detect.py # YOLOv8 单图调试
├── YOLOv26/train.py                 # YOLOv26 训练脚本（独立环境 .venv-yolo26）
│   └── ultralytics/camera_detect.py
├── YOLOv7/train.py                  # YOLOv7 训练/微调脚本（独立环境 .venv-yolov7）
│   └── ultralytics/camera_detect_v7.py
└── README.md                        # 本文件
```

## 训练者配置（可选）

> 仅当你需要**自己训练/微调模型**时才需要。普通用户跳过。

- **训练 YOLOv8**：直接用主环境 `.venv`（主 README「环境准备」第 2 步已装好），按下方「训练流程」操作即可，无需额外配置。
- **训练 YOLOv26**：需要独立环境 `.venv-yolo26`，见下方「2b」。
- **训练/跑 YOLOv7**：需要独立环境 `.venv-yolov7`，见下方「2c」。

可用 setup 脚本一键配置对应环境（与下方手动命令一致）：
```bash
cd ~/桌面/git/practice-records-main/August_task   # 改成你的实际路径
./setup.sh 2b    # YOLO26 环境
./setup.sh 2c    # YOLOv7 环境
```

## 2b. YOLO26 独立环境

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

## 2c. YOLOv7 独立环境

> 预留的 YOLOv7 权重（`src/weights/trained/YOLOv7/best.pt`）需要官方 YOLOv7 推理代码（已放好：`src/lib/yolov7`），
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

> 说明：官方 YOLOv7 的权重文件是 74MB 的 best.pt。该权重为预留模型，未纳入版本控制（本地保留），clone 后需自行放到 `src/weights/trained/YOLOv7/`，类别为红/蓝/黄三色锥桶。
> 推理脚本 `camera_detect_v7.py` 与 v8 的 `camera_detect.py` 用法一致。

## 训练流程

> 前提：已完成数据集准备（①~④，见 [**`src/main_pkg/bag/README.md`**](../main_pkg/bag/README.md)「从 bag 制作训练数据集」）。

在项目根目录训练各模型：

```bash
# ⑤ 训练 YOLOv8（模型输出到 weights/trained/YOLOv8/）
python3 models/YOLOv8/train.py --data ./cone_dataset/data.yaml --epochs 100

# ⑤b 训练 YOLOv26（需独立环境 .venv-yolo26，输出到 weights/trained/YOLOv26/）
.venv-yolo26/bin/python src/models/YOLOv26/train.py --data ./cone_dataset/data.yaml --epochs 100

# ⑤c 训练/微调 YOLOv7（需独立环境 .venv-yolov7，输出到 weights/trained/YOLOv7/）
.venv-yolov7/bin/python src/models/YOLOv7/train.py --data ./cone_dataset/data.yaml --epochs 100
```
