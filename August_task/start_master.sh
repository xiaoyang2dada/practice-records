#!/bin/bash
# ============================================================
# start_master.sh — 本机作为 ROS master + 发布方
# 向局域网发布 /yolov7/yolov7/all_cones (yolov7_ros/ConeArray)
# 用法：
#   bash start_master.sh                     # 默认 IP + 默认 bag
#   MY_IP=192.168.x.x bash start_master.sh   # 指定本机 IP
#   SHOW_RVIZ=true bash start_master.sh      # 本机打开 RViz
#   bash start_master.sh /path/to.bag        # 指定 bag
# 队友连接：
#   export ROS_MASTER_URI=http://<MY_IP>:11311
#   export ROS_IP=<队友自己的IP>
#   rostopic echo /yolov7/yolov7/all_cones -n 1
# ============================================================

# ---------- 可配置 ----------
MY_IP="${MY_IP:-172.20.10.11}"     # 本机局域网 IP
SHOW_RVIZ="${SHOW_RVIZ:-false}"    # 本机是否开 RViz(对接发布时可关省CPU)
BAG="${1:-src/main_pkg/bag/2026-07-16-16-56-05.bag}"
# ---------------------------

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# 0. 清理残留进程(避免节点注册混乱/双发布者导致对方连不上)
pkill -9 -f "rosbag/play" 2>/dev/null || true
pkill -9 -f "devel/lib/main_pkg" 2>/dev/null || true
pkill -9 -f roscore 2>/dev/null || true
pkill -9 -f rosmaster 2>/dev/null || true
pkill -9 -f roslaunch 2>/dev/null || true
rm -f ~/.ros/roscore-*.pid 2>/dev/null || true
sleep 2

# 环境(关键: ROS_IP 让节点注册成 IP 而非主机名, 队友才能直连)
source /opt/ros/noetic/setup.bash
source src/perception_ws/devel/setup.bash
export ROS_MASTER_URI=http://$MY_IP:11311
export ROS_IP=$MY_IP

# 1. roscore(监听 0.0.0.0 对外可达)
nohup roscore > /tmp/roscore.log 2>&1 &
sleep 5
if ! ss -tln 2>/dev/null | grep -q 11311; then
    echo "WARN: roscore 未在 5s 内监听 11311, 继续尝试(看 /tmp/roscore.log)"
else
    echo "OK: roscore 已监听 11311"
fi

# 2. 检测 + 坐标转换节点
nohup rosrun main_pkg cone_detector.py __name:=cone_detector \
    _image_topic:=/pylon_camera_node/image_raw \
    _model_path:=src/weights/trained/YOLOv8/best.pt \
    _conf_threshold:=0.5 _iou_threshold:=0.6 _imgsz:=320 \
    _infer_stride:=1 _show_gui:=false _publish_2d:=false > /tmp/cone.log 2>&1 &
nohup rosrun main_pkg demo01_sub > /tmp/demo.log 2>&1 &

# 可选: 本机可视化
if [ "$SHOW_RVIZ" = "true" ]; then
    nohup rosrun main_pkg visualization_rviz > /tmp/vis.log 2>&1 &
    nohup rosrun rviz rviz -d src/main_pkg/rviz/config.rviz > /tmp/rviz.log 2>&1 &
fi
echo "OK: 节点已启动"

# 3. 回放 bag(只回放图像; 位姿由队友 localizer 提供)
sleep 3
nohup rosbag play -l "$BAG" --topics /pylon_camera_node/image_raw -q > /tmp/bag.log 2>&1 &
echo "OK: bag 回放已启动"

echo ""
echo "======== 启动完成 ========"
echo " 本机 IP    : $MY_IP"
echo " master URI : http://$MY_IP:11311"
echo " show_rviz  : $SHOW_RVIZ"
echo " 队友请设   : export ROS_MASTER_URI=http://$MY_IP:11311 ; export ROS_IP=<队友IP>"
echo " 自检       : 见 README.md「发布方自检」小节"
echo "======================"
