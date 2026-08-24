# 接收 FSAC 锥桶数据 — 消息包使用说明

发布方（你们）的电脑上跑感知链路，会把锥桶检测结果发布到话题：

- 话题：`/yolov7/yolov7/all_cones`
- 类型：`yolov7_ros/ConeArray`

你要做的，就是让本机 ROS 能"认识" `yolov7_ros/ConeArray` 这个消息，然后订阅即可。
**不需要运行对方的任何检测程序，纯接收。**

> **类型是 `yolov7_ros/ConeArray`**（不是 main_pkg）。若你按 main_pkg 编译去订阅，话题名相同但类型不同，会订阅不上。

---

## 一、本目录是什么

本目录是一个**最小的消息包** `yolov7_ros`，只包含 2 个消息定义：

| 文件 | 用途 |
|------|------|
| `msg/ConeInfo.msg` | 单个锥桶：id + 坐标 + 颜色 + 置信度 |
| `msg/ConeArray.msg` | 一帧所有锥桶（订阅 `all_cones` 用它）|

`ConeInfo.msg` 依赖 `geometry_msgs/Point`（ROS 标准消息，无需提供）。

> 若你们本来就有 `yolov7_ros` 包（与 detect_ros.py 同包），直接用你们自己的即可，本目录可忽略。

---

## 二、怎么用

把本 `yolov7_ros` 文件夹放到你的 catkin 工作空间 `src/` 下：

```bash
mkdir -p ~/catkin_ws/src
cp -r <本文件夹位置>/yolov7_ros ~/catkin_ws/src/
cd ~/catkin_ws
catkin_make --only-pkg-with-deps yolov7_ros
source devel/setup.bash
```

---

## 三、配置连接对方的 master 并订阅

发布方（master）的 IP 是：**172.20.10.11**

```bash
export ROS_MASTER_URI=http://172.20.10.11:11311   # 指向发布方
export ROS_IP=<你本机的局域网IP>                   # 改成你自己的 IP

# 订阅锥桶坐标
rostopic echo /yolov7/yolov7/all_cones
```

能看到类似下面的输出，就说明接收成功了：

```
header:
  stamp: ...
  frame_id: "base_link"
cones:
  - id: 1
    position:
      x: 3.58
      y: -0.88
      z: 0.0
    color: "blue_cone"
    confidence: 0.94
```

---

## 四、常见问题

| 现象 | 原因 / 解决 |
|------|------|
| `rostopic echo` 没输出 | 1) 对方没启动；2) master URI 填错；3) 不在同一网段，先 `ping 172.20.10.11` |
| 报 `Connection refused` | master 没起/地址错，确认 `ROS_MASTER_URI` |
| 报找不到 `yolov7_ros` 消息 | 未编译消息包，重跑 `catkin_make` 并 `source devel/setup.bash` |
| 报类型不匹配 | 你的 msg 文件与发布方不一致（发布方在 `src/yolov7_ros/msg/`）|
