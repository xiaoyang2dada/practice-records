"""
train.py — FSAC 锥桶检测 YOLOv7 训练脚本
使用 YOLOv7 官方训练代码（src/lib/yolov7）训练 FSAC 比赛锥桶检测模型。

用法：
  # 指定 data.yaml（推荐）
  .venv-yolov7/bin/python src/models/YOLOv7/train.py --data ./cone_dataset/data.yaml

  # 从预留权重继续训练 / 微调
  .venv-yolov7/bin/python src/models/YOLOv7/train.py \
      --data ./cone_dataset/data.yaml \
      --weights src/weights/trained/YOLOv7/best.pt \
      --epochs 50

  # CPU 训练 + 小批次
  .venv-yolov7/bin/python src/models/YOLOv7/train.py \
      --data ./cone_dataset/data.yaml --device cpu --batch-size 4 --epochs 50

注意：
  - 需在 .venv-yolov7 环境运行（YOLOv7 官方代码不依赖 ultralytics）
  - 数据集需为 YOLO 格式（images/ + labels/ + data.yaml）
  - 训练完权重自动输出到 src/weights/trained/YOLOv7/best.pt
"""

import os
import sys
import shutil
import argparse
import subprocess


def detect_device():
    """自动检测最佳训练设备"""
    import torch
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        print(f"检测到 GPU: {gpu_name}")
        return "0"
    else:
        print("未检测到 GPU，使用 CPU 训练")
        return "cpu"


def main():
    parser = argparse.ArgumentParser(
        description="FSAC 锥桶检测 YOLOv7 训练",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 指定 data.yaml（推荐）
  python train.py --data ./cone_dataset/data.yaml

  # 从预留权重微调
  python train.py --data ./cone_dataset/data.yaml \\
      --weights src/weights/trained/YOLOv7/best.pt --epochs 50

  # CPU 训练 + 小批次
  python train.py --data ./cone_dataset/data.yaml --device cpu --batch-size 4
"""
    )

    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 官方 YOLOv7 训练代码位置
    yolo_dir = os.path.normpath(os.path.join(script_dir, "../../lib/yolov7"))
    # 预训练/默认权重位置
    default_weights = os.path.normpath(
        os.path.join(script_dir, "../../weights/trained/YOLOv7/best.pt"))

    # 数据
    parser.add_argument("--data", "-d", default=None,
                        help="data.yaml 配置文件路径（必填，YOLO 格式数据集）")

    # 模型
    parser.add_argument("--weights", "-w", default=default_weights,
                        help=f"预训练/初始权重路径 (默认: {default_weights})")
    parser.add_argument("--cfg", default="",
                        help="模型结构 yaml 路径（默认用官方 yolov7.yaml）")
    parser.add_argument("--epochs", "-e", type=int, default=100,
                        help="训练轮数 (默认: 100)")
    parser.add_argument("--batch-size", "-b", type=int, default=8,
                        help="批次大小 (默认: 8, CPU 建议 2~4)")
    parser.add_argument("--img-size", "-s", nargs="+", type=int, default=[640, 640],
                        help="[训练, 测试] 输入尺寸 (默认: 640 640)")
    parser.add_argument("--device", default="auto",
                        help="训练设备 (默认: auto 自动检测 GPU, 可指定 cpu / 0)")
    parser.add_argument("--workers", type=int, default=4,
                        help="数据加载线程数 (默认: 4)")
    parser.add_argument("--resume", nargs="?", const=True, default=False,
                        help="从上次中断处继续训练")
    parser.add_argument("--name", "-n", default="YOLOv7",
                        help="训练任务名称 (默认: YOLOv7)")
    parser.add_argument("--adam", action="store_true",
                        help="使用 Adam 优化器（默认 SGD）")
    parser.add_argument("--hyp", default="data/hyp.scratch.custom.yaml",
                        help="超参数配置（默认用官方 custom 超参）")

    args = parser.parse_args()

    # 1. 校验
    if not args.data:
        print("错误: 必须指定 --data data.yaml 路径")
        sys.exit(1)
    data_yaml = os.path.abspath(args.data)
    if not os.path.exists(data_yaml):
        print(f"data.yaml 不存在: {data_yaml}")
        sys.exit(1)

    if not os.path.isdir(yolo_dir):
        print(f"未找到 YOLOv7 官方代码: {yolo_dir}")
        sys.exit(1)

    if not args.resume and not os.path.exists(args.weights):
        print(f"警告: 初始权重不存在 {args.weights}，YOLOv7 将从随机初始化训练")
        print("       （如需迁移学习请提供 --weights 指向预训练权重）")

    # 2. 设备
    if args.device == "auto":
        device = detect_device()
    else:
        device = args.device
        print(f"使用指定设备: {device}")

    # 3. 打印配置
    print("\n" + "=" * 60)
    print("  FSAC 锥桶检测 — YOLOv7 训练")
    print("=" * 60)
    print(f"  数据配置:  {data_yaml}")
    print(f"  官方代码:  {yolo_dir}")
    print(f"  权重:      {args.weights}")
    print(f"  训练轮数:  {args.epochs}")
    print(f"  批次大小:  {args.batch_size}")
    print(f"  图片尺寸:  {args.img_size}")
    print(f"  设备:      {device}")
    print("-" * 60)

    # 4. 构建命令（调用官方 train.py）
    cmd = [
        sys.executable, os.path.join(yolo_dir, "train.py"),
        "--data", data_yaml,
        "--weights", args.weights,
        "--epochs", str(args.epochs),
        "--batch-size", str(args.batch_size),
        "--img-size", *map(str, args.img_size),
        "--device", device,
        "--workers", str(args.workers),
        "--project", "runs/train",
        "--name", args.name,
        "--exist-ok",
    ]
    if args.cfg:
        cmd += ["--cfg", args.cfg]
    if args.resume:
        cmd += ["--resume"] if args.resume is True else ["--resume", str(args.resume)]
    if args.adam:
        cmd += ["--adam"]
    if args.hyp:
        cmd += ["--hyp", os.path.normpath(os.path.join(yolo_dir, args.hyp))]

    # 5. 在官方代码目录下运行（其内部路径依赖相对位置）
    print("  命令: " + " ".join(cmd))
    print("=" * 60)
    try:
        subprocess.run(cmd, cwd=yolo_dir)
    except KeyboardInterrupt:
        print("\n训练被中断")
        sys.exit(1)

    # 6. 同步 best.pt 到标准位置
    best_path = os.path.join(yolo_dir, "runs", "train", args.name, "weights", "best.pt")
    target_dir = os.path.normpath(os.path.join(script_dir, "../../weights/trained/YOLOv7"))
    os.makedirs(target_dir, exist_ok=True)
    target_best = os.path.join(target_dir, "best.pt")

    if os.path.exists(best_path):
        shutil.copy2(best_path, target_best)
        print(f"\n已同步最佳模型: {target_best}")
    else:
        print(f"\n未找到 best.pt: {best_path}")
        print("  训练可能被中断或未保存最佳模型")

    print("\n" + "=" * 60)
    print("  训练完成！")
    print(f"  最佳模型: {target_best}")
    print("=" * 60)


if __name__ == "__main__":
    main()
