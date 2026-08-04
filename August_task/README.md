# FSAC 锥桶检测 — 感知系统开发

中国大学生无人驾驶方程式大赛（FSAC）感知模块，覆盖从数据采集、标注、训练到推理的完整工具链。

## 项目结构

```
August_task/
├── results/                  # 核心脚本
│   ├── bag_info.py           # 查看 ROS bag 视频话题信息
│   ├── extract_frames.py     # 从 bag 抽帧保存为图片
│   ├── cone_label_tool.py    # 交互式锥桶标注工具（GUI）
│   ├── prepare_dataset.py    # 数据集整理 + FSACOCO → YOLO 格式转换
│   ├── train_cone.py         # YOLOv8 锥桶检测模型训练
│   └── bag_yolo_detect.py    # bag 视频流 YOLO 推理 + 保存 MP4
├── FSACOCO/                  # FSAC 开源锥桶数据集
├── YOLOv8/                   # YOLOv8 demo 脚本
├── fifth_week_tasks/         # ROS catkin 工作空间
├── requirements.txt          # Python 依赖
└── README.md
```

## 环境准备（Ubuntu 20.04 + ROS Noetic）

### 1. ROS 系统依赖

```bash
sudo apt install ros-noetic-rosbag ros-noetic-cv-bridge ros-noetic-sensor-msgs
```

### 2. Python 虚拟环境

```bash
cd results
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
```

## 工作流程

```
ROS Bag 录制 → 抽帧提取 → 标注锥桶 → 数据集准备 → 模型训练 → 推理检测
```

### ① 查看 bag 信息
```bash
python3 bag_info.py <bag文件路径>
```

### ② 抽帧
```bash
python3 extract_frames.py <bag文件路径> --interval 3 --max-frames 150
```

### ③ 标注
```bash
python3 cone_label_tool.py ./frames_to_label
```

### ④ 准备数据集
```bash
python3 prepare_dataset.py ./frames_to_label --labels ./labels --output ./cone_dataset
```

### ⑤ 训练
```bash
python3 train_cone.py --data ./cone_dataset/data.yaml --epochs 100
```

### ⑥ 推理
```bash
python3 bag_yolo_detect.py <bag文件路径> --model runs/detect/cone_detect/weights/best.pt
```
