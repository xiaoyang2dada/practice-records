# Bag 数据存放目录

本目录存放 ROS bag 数据包，用于离线全链路测试（无相机时）。

##注意

bag 文件体积大（约 4.7GB），**不会上传到 GitHub**。clone 项目后本目录为空属正常。

## 如何获取 bag 数据

### 方式一：从学长/团队拷贝
找到 `2026-07-16-16-56-05.bag` 放入本目录即可。

### 方式二：自己录制
```bash
# 1. 启动相机后录制图像话题
rosbag record /pylon_camera_node/image_raw -O <输出名>.bag

# 2. 或回放现有 bag 转存
rosbag record /pylon_camera_node/image_raw -O new.bag &
rosbag play old.bag
```

## 使用 bag 测试全链路

```bash
cd /home/xiaoyang/桌面/git/practice-records-main/August_task
source /opt/ros/noetic/setup.bash
source src/perception_ws/devel/setup.bash

roslaunch main_pkg perception.launch \
    bag_path:=src/main_pkg/bag/<你的bag文件>.bag \
    model_path:=src/weights/trained/YOLOv8/best.pt
```

> 提示：bag 文件如果提示 `bag unindexed`，先运行 `rosbag reindex <文件>` 修复。
