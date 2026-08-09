"""
camera_detect.py — 摄像头实时锥桶检测
======================================
用法：
    # 默认用 yolov8n.pt
    python camera_detect.py

    # 用训练好的锥桶模型
    python camera_detect.py --model ../weights/trained/YOLOv8/best.pt

    # 指定摄像头 + 置信度
    python camera_detect.py --model best.pt --camera 0 --conf 0.5

按键：
    Q — 退出
"""

import argparse
import cv2
from ultralytics import YOLO

# 锥桶类别颜色 (BGR)
CONE_COLORS = {
    0: (0, 0, 255),    # red   → 红色框
    1: (255, 0, 0),    # blue  → 蓝色框
    2: (0, 255, 255),  # yellow → 青色框
}


def main():
    parser = argparse.ArgumentParser(description="摄像头实时锥桶检测")
    parser.add_argument("--model", "-m", default="yolov8n.pt",
                        help="模型路径 (默认: yolov8n.pt)")
    parser.add_argument("--camera", "-c", type=int, default=0,
                        help="摄像头编号 (默认: 0)")
    parser.add_argument("--conf", type=float, default=0.5,
                        help="置信度阈值 (默认: 0.5)")
    parser.add_argument("--no-flip", action="store_true",
                        help="不左右翻转画面")
    args = parser.parse_args()

    print(f"📷 加载模型: {args.model}")
    model = YOLO(args.model)
    print(f"   类别: {list(model.names.values())}")
    print(f"🎥 打开摄像头 {args.camera}...")
    print(f"   按 Q 退出\n")

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print("❌ 无法打开摄像头！")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 左右翻转（取消镜像，让画面更自然）
        if not args.no_flip:
            frame = cv2.flip(frame, 1)

        # 推理
        results = model(frame, conf=args.conf, verbose=False)

        # 绘制
        annotated = results[0].plot(boxes=True, conf=True)

        # 叠加 FPS（需要额外计算，这里简单显示模型名）
        cv2.putText(annotated, f"Model: {args.model}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("Cone Detection - Camera", annotated)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("退出。")


if __name__ == "__main__":
    main()
