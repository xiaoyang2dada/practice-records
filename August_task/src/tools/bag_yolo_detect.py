""" 
功能：读取 ROS bag 文件中的视频流，使用 YOLOv8 进行目标检测，实时显示并保存为 MP4 视频。

用法：
    python3 bag_yolo_detect.py <bag文件路径> [--output 输出视频路径] [--conf 置信度阈值]

示例：
    # COCO 预训练模型（默认）
    python3 bag_yolo_detect.py ../fifth_week_tasks/src/plumbing_pub_sub/bag/test.bag

    # 自定义锥桶模型
    python3 bag_yolo_detect.py ../fifth_week_tasks/src/plumbing_pub_sub/bag/test.bag --model best.pt

环境要求：
    - Ubuntu 20.04
    - ROS Noetic
    - ultralytics (YOLOv8)
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

from ultralytics import YOLO

# ============ 颜色定义 ============
# 锥桶类别 → BGR 颜色
CONE_COLORS = {
    0:  (0, 0, 255),    # red   → 红色框
    1:  (255, 0, 0),    # blue  → 蓝色框
    2:  (0, 255, 255),  # yellow → 青色框
}

# COCO 默认颜色（其他类别用）
COCO_COLORS = {
    9:  (0, 255, 255),    # traffic light → 青色
    11: (0, 165, 255),    # stop sign → 橙色
}


def is_custom_model(model):
    """判断是否为自定义锥桶模型（非 COCO 80 类）"""
    names = model.names if hasattr(model, 'names') else {}
    # COCO 模型有 80 个类，第一个是 'person'
    if len(names) == 80 and names.get(0, '').lower() == 'person':
        return False
    # 自定义锥桶模型通常 3 个类
    if len(names) <= 5:
        return True
    return False


def get_color_map(model):
    """根据模型类型返回颜色映射表"""
    if is_custom_model(model):
        # 自定义锥桶模型：用锥桶专用颜色
        return CONE_COLORS
    else:
        # COCO 模型：用默认颜色
        return COCO_COLORS


def get_bag_info(bag_path):
    """打印 bag 文件基本信息，找到视频流话题"""
    print("=" * 60)
    print(f" 正在分析 bag 文件: {bag_path}")
    print("=" * 60)

    bag = rosbag.Bag(bag_path, 'r')
    info = bag.get_type_and_topic_info()

    print(f"\n话题总数: {len(info.topics)}")
    print("-" * 60)

    image_topics = []
    for topic_name, topic_info in info.topics.items():
        msg_type = topic_info.msg_type
        msg_count = topic_info.message_count
        print(f"  话题: {topic_name}")
        print(f"    类型: {msg_type}")
        print(f"    消息数: {msg_count}")

        # 识别图像类型的话题
        if msg_type in ["sensor_msgs/Image", "sensor_msgs/CompressedImage"]:
            image_topics.append((topic_name, msg_type, msg_count))
        print()

    bag.close()

    if not image_topics:
        print("未找到 sensor_msgs/Image 或 sensor_msgs/CompressedImage 类型的话题！")
        print("   请检查 bag 文件中是否包含视频流数据。")
        sys.exit(1)

    print("-" * 60)
    print(f"找到 {len(image_topics)} 个视频流话题:")
    for i, (t, m, c) in enumerate(image_topics):
        print(f"  [{i}] {t}  ({m}, {c} 帧)")
    print("-" * 60)

    return image_topics


def select_image_topic(image_topics):
    """选择要处理的视频流话题"""
    if len(image_topics) == 1:
        chosen = image_topics[0]
        print(f"自动选择唯一视频话题: {chosen[0]}")
        return chosen
    else:
        while True:
            try:
                idx = int(input(f"请选择话题编号 [0-{len(image_topics)-1}]: "))
                if 0 <= idx < len(image_topics):
                    return image_topics[idx]
            except ValueError:
                pass
            print("输入无效，请重试。")


def process_bag(bag_path, image_topic, msg_type, output_path, conf_threshold, model_path, raw_mode=False):
    """主处理函数：逐帧读取 bag 图像 → YOLOv8 检测 → 显示 + 保存视频"""

    # ---------- 初始化 YOLOv8 ----------
    model = None
    custom_model = False
    color_map = {}
    class_names = None

    if not raw_mode:
        print(f"\n 加载 YOLOv8 模型: {model_path}")
        model = YOLO(model_path)

        # --- 检测模型类型 ---
        custom_model = is_custom_model(model)
        color_map = get_color_map(model)
        class_names = model.names if custom_model else None

        if custom_model:
            print(f"检测到自定义锥桶模型 ({len(model.names)} 类): {list(model.names.values())}")
        else:
            print(f"COCO 预训练模型 (80 类)，只显示 traffic light / stop sign")
    else:
        print(f"\n原始视频模式（跳过 YOLOv8 推理）")

    # ---------- 初始化 CvBridge ----------
    bridge = CvBridge()

    # ---------- 打开 bag ----------
    bag = rosbag.Bag(bag_path, 'r')
    total_msgs = bag.get_message_count(topic_filters=[image_topic])
    print(f"共 {total_msgs} 帧待处理")

    # ---------- 初始化 VideoWriter ----------
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = None
    fps = None
    frame_size = None

    # ---------- 逐帧处理 ----------
    frame_count = 0
    try:
        for topic, msg, t in bag.read_messages(topics=[image_topic]):
            # --- 图像转换 ---
            try:
                if msg_type == "sensor_msgs/Image":
                    cv_image = bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
                elif msg_type == "sensor_msgs/CompressedImage":
                    np_arr = np.frombuffer(msg.data, np.uint8)
                    cv_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                else:
                    continue
            except CvBridgeError as e:
                print(f"图像转换失败 (帧 {frame_count}): {e}")
                continue

            # --- 初始化 VideoWriter（需要首帧确定尺寸） ---
            if video_writer is None:
                h, w = cv_image.shape[:2]
                frame_size = (w, h)
                # 估算 FPS（从时间戳）
                video_writer = cv2.VideoWriter(
                    output_path, fourcc, 10.0, frame_size
                )
                print(f"视频输出: {output_path}  ({w}x{h})")

            # --- YOLOv8 推理（原始模式跳过） ---
            if not raw_mode:
                results = model(cv_image, conf=conf_threshold, imgsz=1280, iou=0.43, verbose=False)
            else:
                results = None

            # --- 绘制检测框 ---
            annotated_frame = cv_image.copy()
            if not raw_mode and results and len(results) > 0:
                boxes = results[0].boxes
                if boxes is not None:
                    for box in boxes:
                        cls_id = int(box.cls[0])
                        conf = float(box.conf[0])

                        # 自定义模型：显示所有类别（红/蓝/黄锥桶）
                        # COCO 模型：只显示 traffic light (9) 和 stop sign (11)
                        if not custom_model and cls_id not in (9, 11):
                            continue

                        # 边界框坐标
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

                        # 标签
                        if custom_model and class_names:
                            name = class_names.get(cls_id, f"cls_{cls_id}")
                        else:
                            name = results[0].names.get(cls_id, f"cls_{cls_id}")
                        label_text = f"{name} {conf:.2f}"

                        # 颜色
                        color = color_map.get(cls_id, (0, 255, 0))

                        # 绘制
                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                        cv2.putText(annotated_frame, label_text, (x1, y1 - 8),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # --- 添加帧信息叠加 ---
            cv2.putText(annotated_frame, f"Frame: {frame_count}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # --- 显示 ---
            cv2.imshow("YOLOv8 Bag Video Detection", annotated_frame)

            # --- 写入视频 ---
            video_writer.write(annotated_frame)

            frame_count += 1
            if frame_count % 30 == 0:
                print(f"已处理 {frame_count}/{total_msgs} 帧 ({100*frame_count/total_msgs:.1f}%)")

            # --- 按键控制 ---
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("用户中断。")
                break
            elif key == ord(' '):
                print(" 暂停中，按任意键继续...")
                cv2.waitKey(0)

    except KeyboardInterrupt:
        print("\n用户中断 (Ctrl+C)。")
    finally:
        # ---------- 清理 ----------
        bag.close()
        if video_writer:
            video_writer.release()
        cv2.destroyAllWindows()
        print(f"\n处理完毕！共处理 {frame_count} 帧")
        print(f"输出视频: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="ROS Bag 视频流 YOLOv8 目标检测工具"
    )
    parser.add_argument(
        "bag_path",
        help="ROS bag 文件路径"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="输出视频路径 (默认: 与脚本同目录下的 output.mp4)"
    )
    parser.add_argument(
        "--conf", "-c",
        type=float,
        default=0.25,
        help="YOLOv8 置信度阈值 (默认: 0.25)"
    )
    parser.add_argument(
        "--model", "-m",
        default="yolov8n.pt",
        help="YOLOv8 模型路径 (默认: yolov8n.pt)"
    )
    parser.add_argument(
        "--topic", "-t",
        default=None,
        help="直接指定视频流话题名 (跳过自动检测，例如: /camera/image_raw)"
    )
    parser.add_argument(
        "--all-classes", "-a",
        action="store_true",
        help="显示所有 COCO 80 类目标 (默认只显示 traffic light 和 stop sign)"
    )
    parser.add_argument(
        "--raw", "-r",
        action="store_true",
        help="原始视频模式：跳过 YOLOv8 推理，直接输出 bag 原始视频"
    )
    args = parser.parse_args()

    # 设置是否为锥桶近似模式
    global CONE_LIKE_CLASSES
    if args.all_classes:
        CONE_LIKE_CLASSES = None

    # 验证 bag 文件存在
    if not os.path.exists(args.bag_path):
        print(f"文件不存在: {args.bag_path}")
        sys.exit(1)

    # 设置输出路径
    if args.output:
        output_path = args.output
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, "output.mp4")

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # 1. 确定视频流话题
    if args.topic:
        # 用户手动指定了话题
        image_topic = args.topic
        # 需要确认消息类型：先打开 bag 查看
        bag = rosbag.Bag(args.bag_path, 'r')
        info = bag.get_type_and_topic_info()
        if args.topic not in info.topics:
            print(f"话题 '{args.topic}' 不在 bag 文件中！")
            print(f"   可用话题: {list(info.topics.keys())}")
            bag.close()
            sys.exit(1)
        msg_type = info.topics[args.topic].msg_type
        msg_count = info.topics[args.topic].message_count
        bag.close()
        if msg_type not in ["sensor_msgs/Image", "sensor_msgs/CompressedImage"]:
            print(f"话题 '{args.topic}' 类型为 {msg_type}，不是图像类型！")
            sys.exit(1)
        print(f"使用指定话题: {args.topic} ({msg_type}, {msg_count} 帧)")
    else:
        # 自动检测
        image_topics = get_bag_info(args.bag_path)
        image_topic, msg_type, msg_count = select_image_topic(image_topics)

    # 3. 开始处理
    print(f"\n开始处理...")
    print(f"   Bag 文件:    {args.bag_path}")
    print(f"   视频话题:    {image_topic}")
    print(f"   消息类型:    {msg_type}")
    print(f"   置信度阈值:  {args.conf}")
    print(f"   输出视频:    {output_path}")

    # 预先加载模型判断类型（原始模式跳过）
    if not args.raw:
        temp_model = YOLO(args.model)
        if is_custom_model(temp_model):
            print(f"   模型类型:    自定义锥桶检测 ({list(temp_model.names.values())})")
        else:
            print(f"   模型类型:    COCO 预训练 (仅显示 traffic light / stop sign)")
    else:
        print(f"   模式:        原始视频（无检测）")
    print("-" * 60)

    process_bag(
        bag_path=args.bag_path,
        image_topic=image_topic,
        msg_type=msg_type,
        output_path=output_path,
        conf_threshold=args.conf,
        model_path=args.model,
        raw_mode=args.raw,
    )


if __name__ == "__main__":
    main()
