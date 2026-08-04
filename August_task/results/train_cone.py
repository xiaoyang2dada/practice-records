"""
train_cone.py — FSAC 锥桶检测 YOLOv8 训练脚本
==============================================
使用 YOLOv8 训练 FSAC 比赛锥桶检测模型。

用法：
  # 基础训练
  python3 train_cone.py --data ./cone_dataset/data.yaml

  # 指定模型和参数
  python3 train_cone.py --data ./cone_dataset/data.yaml --model yolov8s.pt --epochs 150 --batch 8

  # 从已有权重继续训练
  python3 train_cone.py --data ./cone_dataset/data.yaml --model runs/detect/train/weights/last.pt --resume

模型选择建议：
  yolov8n.pt  - 最小最快，适合低配机器 (3.2M 参数)
  yolov8s.pt  - 平衡速度和精度 (11.2M 参数)
  yolov8m.pt  - 更高精度，需要更多内存 (25.9M 参数)
"""

import os
import sys
import argparse
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(description="FSAC 锥桶检测 YOLOv8 训练")
    parser.add_argument("--data", "-d", required=True,
                        help="data.yaml 配置文件路径")
    parser.add_argument("--model", "-m", default="yolov8n.pt",
                        help="预训练模型路径 (默认: yolov8n.pt)")
    parser.add_argument("--epochs", "-e", type=int, default=100,
                        help="训练轮数 (默认: 100)")
    parser.add_argument("--batch", "-b", type=int, default=16,
                        help="批次大小 (默认: 16, 内存不足时改为 4 或 8)")
    parser.add_argument("--imgsz", "-s", type=int, default=640,
                        help="输入图片尺寸 (默认: 640)")
    parser.add_argument("--device", default="cpu",
                        help="训练设备 (默认: cpu, 有显卡可用 cuda:0)")
    parser.add_argument("--workers", "-w", type=int, default=4,
                        help="数据加载线程数 (默认: 4)")
    parser.add_argument("--resume", action="store_true",
                        help="从上次中断处继续训练")
    parser.add_argument("--name", "-n", default="cone_detect",
                        help="训练任务名称 (默认: cone_detect)")
    parser.add_argument("--patience", type=int, default=20,
                        help="早停耐心值，N轮无提升则停止 (默认: 20)")
    args = parser.parse_args()

    # 验证文件
    if not os.path.exists(args.data):
        print(f"data.yaml 不存在: {args.data}")
        sys.exit(1)
    if not args.resume and not os.path.exists(args.model):
        print(f"模型文件不存在: {args.model}")
        sys.exit(1)

    print("=" * 60)
    print("FSAC 锥桶检测 — YOLOv8 训练")
    print("=" * 60)
    print(f"数据配置:  {args.data}")
    print(f"模型:      {args.model}")
    print(f"训练轮数:  {args.epochs}")
    print(f"批次大小:  {args.batch}")
    print(f"图片尺寸:  {args.imgsz}")
    print(f"设备:      {args.device}")
    print(f"任务名称:  {args.name}")
    if args.resume:
        print(f"继续训练模式")
    print("-" * 60)

    # 加载模型
    model = YOLO(args.model)

    # 开始训练
    results = model.train(
        data=args.data,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=args.device,
        workers=args.workers,
        resume=args.resume,
        name=args.name,
        patience=args.patience,
        # 数据增强（对锥桶这种规律物体，适度增强即可）
        hsv_h=0.015,        # 色调增强（锥桶颜色固定，不宜太大）
        hsv_s=0.4,          # 饱和度增强
        hsv_v=0.3,          # 明度增强
        degrees=5.0,        # 旋转角度（锥桶通常是正向的）
        translate=0.1,      # 平移
        scale=0.3,          # 缩放
        fliplr=0.5,         # 水平翻转
        mosaic=0.8,         # Mosaic 增强
        # 优化器
        optimizer='AdamW',
        lr0=0.001,          # 初始学习率
        lrf=0.01,           # 最终学习率因子
        momentum=0.937,
        weight_decay=0.0005,
        warmup_epochs=3,
        warmup_momentum=0.8,
        # 损失权重
        box=7.5,            # 框损失权重
        cls=0.5,            # 分类损失权重
        dfl=1.5,            # DFL 损失权重
    )

    # 输出最佳模型路径
    best_path = os.path.join(
        os.path.dirname(results.save_dir or 'runs/detect'),
        args.name, 'weights', 'best.pt'
    )
    print(f"\n训练完成！")
    print(f"最佳模型: {best_path}")
    print(f"\n验证模型:")
    print(f"yolo val data={args.data} model={best_path}")
    print(f"\n使用模型检测:")
    print(f"python3 bag_yolo_detect.py <bag文件> --model {best_path}")


if __name__ == "__main__":
    main()
