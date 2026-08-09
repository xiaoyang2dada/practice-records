# 无人车感知 — Bag 视频流 YOLOv8 检测

## 📁 文件说明

| 文件 | 功能 |
|------|------|
| `bag_info.py` | 快速查看 ROS bag 文件的视频流话题信息（不加载 YOLO） |
| `bag_yolo_detect.py` | 完整检测脚本：读取 bag 视频流 → YOLOv8 推理 → 实时显示 + 保存 MP4 |

---

## 🔧 环境准备 (Ubuntu 20.04)

### 1. 安装 ROS Noetic（如未安装）
```bash
# 参考 http://wiki.ros.org/noetic/Installation/Ubuntu
```

### 2. 安装 Python 依赖
```bash
pip3 install ultralytics opencv-python numpy
```

### 3. 确保 ROS 环境已 source
```bash
source /opt/ros/noetic/setup.bash
```

---

## 🚀 使用步骤

### 第一步：查看 bag 信息（确认视频流话题）
```bash
cd ~/August_task/results/
python3 bag_info.py ../fifth_week_tasks/src/plumbing_pub_sub/bag/2026-07-16-16-56-05.bag
```
输出示例：
```
🎥 视频流话题:
  └─ /camera/image_raw/compressed
      类型: sensor_msgs/CompressedImage
      帧数: 1500
      频率: 15.0 Hz
```

### 第二步：运行 YOLOv8 检测
```bash
# 基础用法（只检测锥桶近似类别：traffic light + stop sign）
python3 bag_yolo_detect.py ../fifth_week_tasks/src/plumbing_pub_sub/bag/2026-07-16-16-56-05.bag

# 指定置信度阈值
python3 bag_yolo_detect.py ../fifth_week_tasks/.../2026-07-16-16-56-05.bag --conf 0.35

# 检测所有 COCO 80 类目标
python3 bag_yolo_detect.py ../fifth_week_tasks/.../2026-07-16-16-56-05.bag --all-classes

# 指定输出视频路径
python3 bag_yolo_detect.py ../fifth_week_tasks/.../2026-07-16-16-56-05.bag --output ./result.mp4

# 使用其他 YOLO 模型
python3 bag_yolo_detect.py ../fifth_week_tasks/.../2026-07-16-16-56-05.bag --model yolov8s.pt
```

### 操作控制
| 按键 | 功能 |
|------|------|
| `Q` | 退出处理 |
| `空格` | 暂停 / 继续 |
| `Ctrl+C` | 终端强制退出 |

---

## 📝 关于锥桶检测

YOLOv8 COCO 预训练模型的 80 个类别中**没有 "traffic cone"（交通锥桶）**。

当前脚本暂用以下近似类别替代：

| COCO ID | 类别 | 说明 |
|---------|------|------|
| 9 | traffic light | 交通信号灯 |
| 11 | stop sign | 停止标志 |

⚠️ **这只是一个临时方案**。如果需要精确检测锥桶，建议：
1. 准备锥桶标注数据集
2. 修改 `demo_train.py` 中的 `yolo-bvn.yaml` 配置
3. 训练自定义锥桶检测模型
4. 使用 `--model your_cone_model.pt` 加载自定义模型

---

## 🔄 与现有锥桶坐标程序的协作

```
bag 文件 (2026-07-16-16-56-05.bag)
    ├── 坐标流 (/test/camera_cones)  ──→  demo01_sub.cpp  (锥桶坐标处理)
    └── 视频流 (/camera/xxx)         ──→  bag_yolo_detect.py (YOLOv8 视频检测)
```

两个程序可以同时运行，互不干扰。
