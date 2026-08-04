# FSAC 锥桶检测 — 推理使用指南

> 模型已完成初次训练，以下为 bag 视频流 → YOLO 锥桶检测 → 结果展示的完整流程。

## 环境准备（Ubuntu 20.04 + ROS Noetic）

```bash
# ROS 依赖
sudo apt install ros-noetic-rosbag ros-noetic-cv-bridge ros-noetic-sensor-msgs

# Python 依赖
cd August_task/results
pip3 install ultralytics opencv-python numpy torch -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 🚀 完整检测流程

### 第一步：查看 bag 信息

```bash
cd ~/August_task/results
source /opt/ros/noetic/setup.bash

python3 bag_info.py ../fifth_week_tasks/src/plumbing_pub_sub/bag/test.bag
```

输出示例：
```
🎥 视频流话题:
  └─ /camera/image_raw/compressed  (sensor_msgs/CompressedImage, 1500 帧)
```

---

### 第二步：运行锥桶检测

```bash
python3 bag_yolo_detect.py ../fifth_week_tasks/src/plumbing_pub_sub/bag/test.bag \
    --model best.pt \
    --conf 0.35 \
    --output ./cone_result.mp4
```

| 参数 | 说明 |
|------|------|
| `--model best.pt` | 训练好的锥桶检测模型 |
| `--conf 0.35` | 置信度阈值（0.35 推荐，越低框越多） |
| `--output` | 输出视频路径（默认 `output.mp4`） |

---

### 第三步：查看结果

```bash
# 用系统播放器打开
xdg-open cone_result.mp4

# 或在终端查看帧数/分辨率
ffprobe cone_result.mp4
```

---

## 🎮 运行时操作

| 按键 | 功能 |
|------|------|
| `Q` | 退出 |
| `空格` | 暂停 / 继续 |

---

## 📁 检测结果说明

输出视频中，锥桶用**颜色框**区分：

| 框色 | 类别 | 标签 |
|:--:|------|------|
| 🔴 红色框 | red | 红色锥桶 |
| 🔵 蓝色框 | blue | 蓝色锥桶 |
| 🩵 青色框 | yellow | 黄色锥桶 |

> 每个框标注格式：`类别名 置信度`，如 `red 0.87`

---

## 🔄 对接实时摄像头（待实现）

效果满意后，可切换到摄像头实时检测：

```bash
python3 ../YOLOv8/ultralytics/camera_detect.py --model best.pt
```
