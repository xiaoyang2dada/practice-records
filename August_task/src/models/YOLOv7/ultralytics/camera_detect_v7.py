"""
camera_detect_v7.py — 摄像头实时锥桶检测 (YOLOv7)
注意: 需独立环境 .venv-yolov7 运行 (含 YOLOv7 官方库, 主环境 .venv 无法加载 YOLOv7 权重)。
请在项目根目录 (August_task/) 下运行:
  .venv-yolov7/bin/python src/models/YOLOv7/ultralytics/camera_detect_v7.py ...

用法:
    # 用训练好的 YOLOv7 锥桶模型
    .venv-yolov7/bin/python src/models/YOLOv7/ultralytics/camera_detect_v7.py --model src/weights/trained/YOLOv7/best.pt

    # 指定摄像头 + 置信度
    .venv-yolov7/bin/python src/models/YOLOv7/ultralytics/camera_detect_v7.py --model src/weights/trained/YOLOv7/best.pt --camera 0 --conf 0.3

按键:
    Q — 退出
"""

import argparse
import os
import sys

# 加入 YOLOv7 官方库 (相对脚本位置: src/lib/yolov7)
_YOLOV7_LIB = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'lib', 'yolov7'))
if os.path.isdir(_YOLOV7_LIB) and _YOLOV7_LIB not in sys.path:
    sys.path.insert(0, _YOLOV7_LIB)

import cv2
import numpy as np
import torch
import torch.nn as nn
from models.common import Conv
from utils.general import non_max_suppression, scale_coords

# 锥桶类别颜色 (BGR)
CONE_COLORS = {
    0: (0, 0, 255),    # red   -> 红色框
    1: (255, 0, 0),    # blue  -> 蓝色框
    2: (0, 255, 255),  # yellow -> 青色框
}


def letterbox(img, new_shape=(640, 640), color=(114, 114, 114), auto=True, scaleFill=False, scaleup=True, stride=32):
    # 与官方 detect.py 一致的 letterbox: 等比例缩放 + 灰边填充 (保持宽高比, 避免目标变形)
    shape = img.shape[:2]  # current shape [height, width]
    if isinstance(new_shape, int):
        new_shape = (new_shape, new_shape)

    # Scale ratio (new / old)
    r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
    if not scaleup:  # only scale down, do not scale up (for better test mAP)
        r = min(r, 1.0)

    # Compute padding
    ratio = r, r  # width, height ratios
    new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
    dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]  # wh padding
    if auto:  # minimum rectangle
        dw, dh = np.mod(dw, stride), np.mod(dh, stride)  # wh padding
    elif scaleFill:  # stretch
        dw, dh = 0.0, 0.0
        new_unpad = (new_shape[1], new_shape[0])
        ratio = new_shape[1] / shape[1], new_shape[0] / shape[0]  # width, height ratios

    dw /= 2  # divide padding into 2 sides
    dh /= 2

    if shape[::-1] != new_unpad:  # resize
        img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)  # add border
    return img, ratio, (dw, dh)


def load_model(weights, device='cpu'):
    # 绕过 attempt_load 的 attempt_download (会因路径小写化找不到含大写路径的文件)
    ckpt = torch.load(weights, map_location=device)
    model = ckpt['ema' if ckpt.get('ema') else 'model'].float()
    model.fuse().eval()
    for m in model.modules():
        if type(m) in [nn.Hardswish, nn.LeakyReLU, nn.ReLU, nn.ReLU6, nn.SiLU]:
            m.inplace = True
        elif type(m) is nn.Upsample:
            m.recompute_scale_factor = None
        elif type(m) is Conv:
            m._non_persistent_buffers_set = set()
    return model


def infer(model, img0, conf, iou=0.45, imgsz=640):
    # 与官方 detect.py / v8 一致: letterbox 保比例 + 灰边, 避免拉伸变形导致框偏大
    stride = int(model.stride.max())
    img, _, _ = letterbox(img0, new_shape=imgsz, stride=stride)
    img = img.transpose((2, 0, 1))[::-1]
    img = np.ascontiguousarray(img)
    t = torch.from_numpy(img).float() / 255.0
    t = t.unsqueeze(0)

    with torch.no_grad():
        pred = model(t)[0]  # (1, N, 8) cxcywh, 直接传给 NMS (内部会转 xyxy)
    det = non_max_suppression(pred, conf, iou)[0]
    # 坐标映射回原图 (scale_coords 正确处理 letterbox 的缩放与灰边 pad)
    if det is not None and len(det) > 0:
        det[:, :4] = scale_coords(t.shape[2:], det[:, :4], img0.shape[:2]).round()
    return det


def draw_boxes(img0, det, names):
    if det is None:
        return img0
    annotated = img0.copy()
    for *xyxy, conf, cls in det.tolist():
        c = int(cls)
        x1, y1, x2, y2 = map(int, xyxy)
        color = CONE_COLORS.get(c, (0, 255, 0))
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        label = f"{names[c]} {conf:.2f}"
        cv2.putText(annotated, label, (x1, max(y1 - 5, 15)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return annotated


def main():
    parser = argparse.ArgumentParser(description="摄像头实时锥桶检测 (YOLOv7)")
    parser.add_argument("--model", "-m", default="src/weights/trained/YOLOv7/best.pt",
                        help="模型路径 (默认: src/weights/trained/YOLOv7/best.pt)")
    parser.add_argument("--camera", "-c", type=int, default=0,
                        help="摄像头编号 (默认: 0)")
    parser.add_argument("--conf", type=float, default=0.3,
                        help="置信度阈值 (默认: 0.3)")
    parser.add_argument("--imgsz", type=int, default=640,
                        help="推理尺寸 (默认: 640)")
    parser.add_argument("--no-flip", action="store_true",
                        help="不左右翻转画面")
    args = parser.parse_args()

    print(f"加载模型: {args.model}")
    model = load_model(args.model, device='cpu')
    names = list(model.names.values()) if isinstance(model.names, dict) else list(model.names)
    print(f"   类别: {names}")
    print(f"打开摄像头 {args.camera}...")
    print(f"   按 Q 退出\n")

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print("无法打开摄像头！")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if not args.no_flip:
            frame = cv2.flip(frame, 1)

        det = infer(model, frame, args.conf, imgsz=args.imgsz)
        annotated = draw_boxes(frame, det, model.names)

        cv2.putText(annotated, f"Model: {args.model}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("Cone Detection - Camera (YOLOv7)", annotated)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("退出。")


if __name__ == "__main__":
    main()
