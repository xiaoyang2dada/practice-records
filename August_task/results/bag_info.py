#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bag_info.py
===========
快速查看 ROS bag 文件的详细信息（话题、类型、消息数、时间范围等）。

用法：
    python3 bag_info.py <bag文件路径>

无需加载 YOLOv8，仅依赖 rosbag 即可运行。
"""

import sys
import os
import rosbag
from datetime import datetime


def format_duration(seconds):
    """格式化时间长度"""
    if seconds < 60:
        return f"{seconds:.1f} 秒"
    elif seconds < 3600:
        return f"{seconds/60:.1f} 分钟"
    else:
        return f"{seconds/3600:.1f} 小时"


def main():
    if len(sys.argv) < 2:
        print("用法: python3 bag_info.py <bag文件路径>")
        sys.exit(1)

    bag_path = sys.argv[1]
    if not os.path.exists(bag_path):
        print(f" 文件不存在: {bag_path}")
        sys.exit(1)

    file_size = os.path.getsize(bag_path)
    bag = rosbag.Bag(bag_path, 'r')

    print("=" * 70)
    print(" ROS Bag 信息")
    print("=" * 70)

    # 基本信息
    print(f"\n 文件路径: {bag_path}")
    print(f" 文件大小: {file_size / (1024**3):.2f} GB ({file_size:,} bytes)")
    print(f" 消息总数: {bag.get_message_count()}")

    # 时间范围
    start_time = bag.get_start_time()
    end_time = bag.get_end_time()
    duration = end_time - start_time
    print(f" 开始时间: {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f" 结束时间: {datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱  持续时长: {format_duration(duration)}")

    # 话题信息
    print(f"\n 话题列表:")
    print("-" * 70)
    info = bag.get_type_and_topic_info()

    image_topics = []
    other_topics = []

    for topic_name, topic_info in sorted(info.topics.items()):
        msg_type = topic_info.msg_type
        msg_count = topic_info.message_count
        freq = msg_count / duration if duration > 0 else 0

        if msg_type in ["sensor_msgs/Image", "sensor_msgs/CompressedImage"]:
            image_topics.append((topic_name, msg_type, msg_count, freq))
        else:
            other_topics.append((topic_name, msg_type, msg_count, freq))

    # 先打印视频话题
    if image_topics:
        print("   视频流话题:")
        for name, mtype, count, freq in image_topics:
            print(f" {name}")
            print(f" 类型: {mtype}")
            print(f" 帧数: {count}")
            print(f" 频率: {freq:.1f} Hz")
            print()

    if other_topics:
        print("   其他话题:")
        for name, mtype, count, freq in other_topics:
            print(f" {name}")
            print(f" 类型: {mtype}")
            print(f" 消息数: {count}")
            print(f" 频率: {freq:.1f} Hz")
            print()

    print("-" * 70)
    print(f" 视频流话题数: {len(image_topics)}")
    print(f" 其他话题数:   {len(other_topics)}")

    bag.close()

    if image_topics:
        print(f"\n 提示: 运行以下命令开始 YOLOv8 检测:")
        print(f"   python3 bag_yolo_detect.py \"{bag_path}\"")
    else:
        print(f"\n 未找到视频流话题 (sensor_msgs/Image / CompressedImage)")
        print(f" 该 bag 可能不包含图像数据。")


if __name__ == "__main__":
    main()
