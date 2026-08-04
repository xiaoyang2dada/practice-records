"""
bag_extract_video.py — 从 ROS Bag 提取原始视频（无 YOLO 检测）
============================================================
读取 ROS bag 中的图像话题，直接输出无标注的原始 MP4 视频。

用法：
    python3 bag_extract_video.py <bag文件路径> [--output 输出路径] [--topic 话题名] [--fps 帧率]

示例：
    # 自动检测图像话题，输出 raw_output.mp4
    python3 bag_extract_video.py test.bag

    # 指定话题和帧率
    python3 bag_extract_video.py test.bag --topic /camera/image_raw --fps 15

    # 指定输出路径
    python3 bag_extract_video.py test.bag --output ./my_raw_video.mp4

环境要求：
    - ROS Noetic
    - opencv-python
    - cv_bridge (ROS package)
"""

import os
import sys
import argparse
import cv2
import numpy as np

import rosbag
from cv_bridge import CvBridge, CvBridgeError
from sensor_msgs.msg import Image, CompressedImage


def get_image_topics(bag_path):
    """扫描 bag 中的所有图像话题"""
    bag = rosbag.Bag(bag_path, 'r')
    info = bag.get_type_and_topic_info()

    image_topics = []
    for topic_name, topic_info in info.topics.items():
        if topic_info.msg_type in ("sensor_msgs/Image", "sensor_msgs/CompressedImage"):
            image_topics.append((topic_name, topic_info.msg_type, topic_info.message_count))
    bag.close()
    return image_topics


def extract_video(bag_path, image_topic, msg_type, output_path, fps):
    """从 bag 提取原始视频"""
    bridge = CvBridge()
    bag = rosbag.Bag(bag_path, 'r')
    total = bag.get_message_count(topic_filters=[image_topic])

    print(f"话题: {image_topic}  ({msg_type}, {total} 帧)")
    print(f"输出: {output_path}")
    print(f"帧率: {fps} fps")
    print("-" * 50)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = None
    frame_count = 0

    try:
        for topic, msg, t in bag.read_messages(topics=[image_topic]):
            # --- 图像解码 ---
            try:
                if msg_type == "sensor_msgs/Image":
                    frame = bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
                elif msg_type == "sensor_msgs/CompressedImage":
                    np_arr = np.frombuffer(msg.data, np.uint8)
                    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                else:
                    continue
            except CvBridgeError as e:
                print(f"解码失败 (帧 {frame_count}): {e}")
                continue

            # --- 初始化 VideoWriter ---
            if writer is None:
                h, w = frame.shape[:2]
                writer = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
                print(f"分辨率: {w}×{h}")

            # --- 写入 ---
            writer.write(frame)
            frame_count += 1

            if frame_count % 100 == 0:
                print(f"已写入 {frame_count}/{total} 帧 ({100*frame_count/total:.1f}%)")

    except KeyboardInterrupt:
        print("\n用户中断。")
    finally:
        bag.close()
        if writer:
            writer.release()
        print(f"\n完成！共写入 {frame_count} 帧")
        print(f"输出: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="从 ROS Bag 提取原始视频")
    parser.add_argument("bag_path", help="ROS bag 文件路径")
    parser.add_argument("--output", "-o", default=None,
                        help="输出视频路径 (默认: 当前目录下 原始视频.mp4)")
    parser.add_argument("--topic", "-t", default=None,
                        help="图像话题名 (默认: 自动检测第一个图像话题)")
    parser.add_argument("--fps", "-f", type=float, default=10.0,
                        help="输出视频帧率 (默认: 10)")
    args = parser.parse_args()

    # --- 验证 bag 文件 ---
    if not os.path.exists(args.bag_path):
        print(f"文件不存在: {args.bag_path}")
        sys.exit(1)

    # --- 输出路径 ---
    if args.output:
        output_path = args.output
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, "原始视频.mp4")

    # --- 确定图像话题 ---
    if args.topic:
        image_topic = args.topic
        bag = rosbag.Bag(args.bag_path, 'r')
        info = bag.get_type_and_topic_info()
        if args.topic not in info.topics:
            print(f"话题 '{args.topic}' 不存在！")
            available = get_image_topics(args.bag_path)
            if available:
                print(f"可用图像话题: {[t[0] for t in available]}")
            bag.close()
            sys.exit(1)
        msg_type = info.topics[args.topic].msg_type
        bag.close()
    else:
        image_topics = get_image_topics(args.bag_path)
        if not image_topics:
            print("未找到任何图像话题！")
            sys.exit(1)
        image_topic, msg_type, _ = image_topics[0]
        print(f"自动选择话题: {image_topic}")

    # --- 提取 ---
    print("=" * 50)
    print(" ROS Bag → 原始视频提取")
    print("=" * 50)
    extract_video(args.bag_path, image_topic, msg_type, output_path, args.fps)


if __name__ == "__main__":
    main()
