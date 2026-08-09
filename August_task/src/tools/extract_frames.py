"""
extract_frames.py — 从 ROS Bag 中提取视频帧用于标注
=====================================================
从 rosbag 的图像话题中抽取帧，保存为 PNG/JPG 图片，供 cone_label_tool.py 标注使用。

用法：
  # 抽取全部帧
  python3 extract_frames.py <bag文件路径> [--output 输出目录]

  # 每 N 帧抽一张（避免相邻帧太相似）
  python3 extract_frames.py <bag文件路径> --interval 10

  # 最多抽取 N 张
  python3 extract_frames.py <bag文件路径> --max-frames 200

  # 指定话题
  python3 extract_frames.py <bag文件路径> --topic /pylon_camera_node/image_raw

示例：
  python3 extract_frames.py ../fifth_week_tasks/src/plumbing_pub_sub/bag/2026-07-16-16-56-05.bag \
      --output ./frames_to_label --interval 3 --max-frames 150
"""

import os
import sys
import argparse
import cv2
import numpy as np

import rosbag
from cv_bridge import CvBridge, CvBridgeError
from sensor_msgs.msg import Image, CompressedImage


def extract_frames(bag_path, output_dir, topic=None, interval=1, max_frames=0, img_format='png'):
    """
    从 bag 文件中提取图像帧。

    Args:
        bag_path:    bag 文件路径
        output_dir:  输出目录
        topic:       图像话题（None 则自动检测第一个图像话题）
        interval:    抽帧间隔（每隔 N 帧抽一张）
        max_frames:  最多抽取帧数（0 表示不限制）
        img_format:  图片格式 (png/jpg)
    """
    bridge = CvBridge()

    # ---- 打开 bag ----
    print(f"正在分析 bag: {bag_path}")
    bag = rosbag.Bag(bag_path, 'r')
    info = bag.get_type_and_topic_info()

    # ---- 自动检测图像话题 ----
    if topic is None:
        for tname, tinfo in info.topics.items():
            if tinfo.msg_type in ('sensor_msgs/Image', 'sensor_msgs/CompressedImage'):
                topic = tname
                msg_type = tinfo.msg_type
                total = tinfo.message_count
                break
        if topic is None:
            print("未找到图像话题！")
            bag.close()
            return 0
    else:
        if topic not in info.topics:
            print(f"话题 '{topic}' 不在 bag 中")
            available = [t for t, i in info.topics.items()
                         if i.msg_type in ('sensor_msgs/Image', 'sensor_msgs/CompressedImage')]
            if available:
                print(f"   可用图像话题: {available}")
            bag.close()
            return 0
        msg_type = info.topics[topic].msg_type
        total = info.topics[topic].message_count

    print(f"话题: {topic}  ({msg_type}, {total} 帧)")
    print(f"输出目录: {output_dir}")
    print(f"抽帧间隔: 每 {interval} 帧取 1 张")
    if max_frames > 0:
        print(f"最多抽取: {max_frames} 张")
    print("-" * 60)

    # ---- 创建输出目录 ----
    os.makedirs(output_dir, exist_ok=True)

    # ---- 逐帧提取 ----
    saved_count = 0
    frame_idx = 0

    try:
        for topic_name, msg, t in bag.read_messages(topics=[topic]):
            frame_idx += 1

            # 跳帧
            if (frame_idx - 1) % interval != 0:
                continue

            # 解码
            try:
                if msg_type == 'sensor_msgs/Image':
                    cv_image = bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
                elif msg_type == 'sensor_msgs/CompressedImage':
                    np_arr = np.frombuffer(msg.data, np.uint8)
                    cv_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                else:
                    continue
            except (CvBridgeError, Exception) as e:
                print(f"第 {frame_idx} 帧解码失败: {e}")
                continue

            # 保存
            timestamp_ns = t.to_nsec()
            filename = f"frame_{saved_count:06d}_{timestamp_ns}.{img_format}"
            filepath = os.path.join(output_dir, filename)
            cv2.imwrite(filepath, cv_image)
            saved_count += 1

            if saved_count % 30 == 0:
                print(f"已提取 {saved_count} 帧 (进度 {frame_idx}/{total})")

            if max_frames > 0 and saved_count >= max_frames:
                break

    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        bag.close()

    print(f"\n完成！共提取 {saved_count} 帧到 {output_dir}")

    # ---- 统计信息 ----
    total_size = sum(
        os.path.getsize(os.path.join(output_dir, f))
        for f in os.listdir(output_dir)
        if os.path.isfile(os.path.join(output_dir, f))
    )
    print(f"总大小: {total_size / 1024 / 1024:.1f} MB")
    return saved_count


def main():
    parser = argparse.ArgumentParser(
        description="从 ROS Bag 提取视频帧用于标注"
    )
    parser.add_argument("bag_path", help="ROS bag 文件路径")
    parser.add_argument("--output", "-o", default="./frames_to_label",
                        help="输出目录 (默认: ./frames_to_label)")
    parser.add_argument("--topic", "-t", default=None,
                        help="图像话题名 (默认自动检测)")
    parser.add_argument("--interval", "-n", type=int, default=3,
                        help="抽帧间隔，每隔N帧抽一张 (默认: 3)")
    parser.add_argument("--max-frames", "-m", type=int, default=200,
                        help="最多抽取帧数 (默认: 200)")
    parser.add_argument("--format", "-f", choices=['png', 'jpg'], default='png',
                        help="图片格式 (默认: png)")
    args = parser.parse_args()

    if not os.path.exists(args.bag_path):
        print(f"文件不存在: {args.bag_path}")
        sys.exit(1)

    extract_frames(
        bag_path=args.bag_path,
        output_dir=os.path.abspath(args.output),
        topic=args.topic,
        interval=args.interval,
        max_frames=args.max_frames,
        img_format=args.format,
    )


if __name__ == "__main__":
    main()
