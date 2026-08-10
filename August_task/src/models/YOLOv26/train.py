"""
train.py — FSAC 锥桶检测 YOLO26 训练脚本 (Windows / Linux 通用)
使用 YOLO26 训练 FSAC 比赛锥桶检测模型。

注意：YOLO26 需要独立环境 .venv-yolo26 运行（当前主环境 .venv 不含 YOLO26 支持）。
请在项目根目录 (August_task/) 下运行：
  .venv-yolo26/bin/python src/models/YOLOv26/train.py ...

用法：
  # 方式1：直接指定外部数据集目录（自动转换 VOC→YOLO）
  .venv-yolo26/bin/python src/models/YOLOv26/train.py --dataset "F:/桌面/dataset/my(BUAA+FZU+WUST)"

  # 方式2：指定已准备好的 data.yaml
  .venv-yolo26/bin/python src/models/YOLOv26/train.py --data "F:/桌面/dataset/my(BUAA+FZU+WUST)/cone_data.yaml"

  # 方式3：无参数运行（使用默认数据集路径）
  .venv-yolo26/bin/python src/models/YOLOv26/train.py

  # 指定模型和参数
  .venv-yolo26/bin/python src/models/YOLOv26/train.py --model src/weights/pretrained/yolo26s.pt --epochs 150 --batch 8

  # 从已有权重继续训练
  .venv-yolo26/bin/python src/models/YOLOv26/train.py --model runs/detect/cone_detect/weights/last.pt --resume

模型选择建议（预训练权重位于 src/weights/pretrained/）：
  yolo26n.pt  - 最小最快，适合低配机器 (2.4M 参数)
  yolo26s.pt  - 平衡速度和精度 (9.5M 参数)
  yolo26m.pt  - 更高精度，需要更多内存 (20.4M 参数)
"""

import os
import sys
import shutil
import argparse
import subprocess
from ultralytics import YOLO

# 默认数据集路径 (Windows)
DEFAULT_DATASET_DIR = r"F:\桌面\dataset\my(BUAA+FZU+WUST)"


def detect_device():
    """自动检测最佳训练设备"""
    import torch
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        print(f"GPU: {gpu_name}")
        return "cuda:0"
    else:
        print("未检测到 GPU，使用 CPU 训练")
        return "cpu"


def run_voc_conversion(dataset_dir):
    """调用 prepare_voc_dataset.py 转换 VOC 数据集"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    convert_script = os.path.normpath(os.path.join(script_dir, "../../tools/prepare_voc_dataset.py"))

    if not os.path.exists(convert_script):
        print(f"转换脚本: {convert_script}")
        print("请确保 tools/prepare_voc_dataset.py 存在")
        return None

    print(f"\n首次使用，自动转换 VOC 数据集...")
    print(f"   数据集: {dataset_dir}")
    print(f"   转换脚本: {convert_script}")

    cmd = [sys.executable, convert_script, dataset_dir]

    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        if result.returncode != 0:
            print("\n数据集转换失败！")
            return None
    except Exception as e:
        print(f"\n运行转换脚本出错: {e}")
        return None

    yaml_path = os.path.join(dataset_dir, "cone_data.yaml")
    if os.path.exists(yaml_path):
        print(f"转换完成: {yaml_path}")
        return yaml_path
    else:
        print(f"\n转换后未找到 data.yaml: {yaml_path}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="FSAC 锥桶检测 YOLO26 训练",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例 (项目根目录 August_task/ 下运行):
  # 最简单用法（自动检测 GPU + 默认数据集）
  .venv-yolo26/bin/python src/models/YOLOv26/train.py

  # 指定数据集目录（自动转换 VOC XML）
  .venv-yolo26/bin/python src/models/YOLOv26/train.py --dataset "F:/桌面/dataset/my(BUAA+FZU+WUST)"

  # CPU 训练 + 小批次
  .venv-yolo26/bin/python src/models/YOLOv26/train.py --device cpu --batch 4 --epochs 50

  # GPU 训练 + 大模型
  .venv-yolo26/bin/python src/models/YOLOv26/train.py --model src/weights/pretrained/yolo26s.pt --batch 16 --epochs 200
"""
    )

    # 数据集参数
    parser.add_argument(
        "--dataset", "-ds",
        default=None,
        help=f"VOC 数据集根目录（含 jpg/ 和 xml/），默认: {DEFAULT_DATASET_DIR}"
    )
    parser.add_argument(
        "--data", "-d",
        default=None,
        help="data.yaml 配置文件路径（优先于 --dataset）"
    )

    # 模型参数 (默认指向本地预训练权重, 避免自动从网络下载)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_model = os.path.normpath(os.path.join(script_dir, "../../weights/pretrained/yolo26n.pt"))
    parser.add_argument("--model", "-m", default=default_model,
                        help=f"预训练模型路径 (默认: {default_model})")
    parser.add_argument("--epochs", "-e", type=int, default=100,
                        help="训练轮数 (默认: 100)")
    parser.add_argument("--batch", "-b", type=int, default=16,
                        help="批次大小 (默认: 16, 内存不足时改为 4 或 8)")
    parser.add_argument("--imgsz", "-s", type=int, default=640,
                        help="输入图片尺寸 (默认: 640)")
    parser.add_argument("--device", default="auto",
                        help="训练设备 (默认: auto 自动检测 GPU, 可手动指定 cpu / cuda:0)")
    parser.add_argument("--workers", "-w", type=int, default=4,
                        help="数据加载线程数 (默认: 4, Windows 建议 <= 4)")
    parser.add_argument("--resume", action="store_true",
                        help="从上次中断处继续训练")
    parser.add_argument("--name", "-n", default="cone_detect",
                        help="训练任务名称 (默认: cone_detect)")
    parser.add_argument("--patience", type=int, default=20,
                        help="早停耐心值，N轮无提升则停止 (默认: 20)")
    parser.add_argument("--skip-convert", action="store_true",
                        help="跳过自动转换，直接使用已有数据")

    args = parser.parse_args()

    # 1. 确定数据配置
    data_yaml = args.data

    if data_yaml is None:
        dataset_dir = args.dataset or DEFAULT_DATASET_DIR

        if not os.path.isdir(dataset_dir):
            print(f"数据集目录不存在: {dataset_dir}")
            print(f"   请通过 --dataset 或 --data 指定正确路径")
            sys.exit(1)

        expected_yaml = os.path.join(dataset_dir, "cone_data.yaml")

        if os.path.exists(expected_yaml) and args.skip_convert:
            data_yaml = expected_yaml
        elif os.path.exists(expected_yaml):
            data_yaml = expected_yaml
            print(f"使用已有配置: {data_yaml}")
        else:
            if not args.skip_convert:
                data_yaml = run_voc_conversion(dataset_dir)
                if data_yaml is None:
                    sys.exit(1)
            else:
                print(f"未找到 data.yaml 且指定了 --skip-convert")
                sys.exit(1)

    if not data_yaml or not os.path.exists(data_yaml):
        print(f"data.yaml 不存在: {data_yaml}")
        sys.exit(1)

    data_yaml = os.path.abspath(data_yaml)

    # 2. 确定设备
    if args.device == "auto":
        device = detect_device()
    else:
        device = args.device
        print(f"使用指定设备: {device}")

    # 3. 验证模型文件
    if not args.resume and not os.path.exists(args.model):
        print(f"本地未找到 {args.model}，YOLO26 将自动从网络下载...")

    # 4. 打印训练配置
    print("\n" + "=" * 60)
    print("  FSAC 锥桶检测 — YOLO26 训练")
    print("=" * 60)
    print(f"  数据配置:  {data_yaml}")
    print(f"  模型:      {args.model}")
    print(f"  训练轮数:  {args.epochs}")
    print(f"  批次大小:  {args.batch}")
    print(f"  图片尺寸:  {args.imgsz}")
    print(f"  设备:      {device}")
    print(f"  工作线程:  {args.workers}")
    print(f"  任务名称:  {args.name}")
    if args.resume:
        print(f"  模式:      继续训练")
    print("-" * 60)

    # 5. 加载模型并训练
    model = YOLO(args.model)

    # 训练输出目录: src/weights/trained/YOLOv26 (绝对路径, 直接生成权重)
    project_dir = os.path.normpath(os.path.join(script_dir, "../../weights/trained"))
    os.makedirs(project_dir, exist_ok=True)

    # 覆盖旧的权重目录 (删除旧 best.pt 等)
    trained_dir = os.path.join(project_dir, args.name)
    if os.path.exists(trained_dir):
        shutil.rmtree(trained_dir)
        print(f"已删除旧权重目录: {trained_dir}")

    results = model.train(
        data=data_yaml,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=device,
        workers=args.workers,
        resume=args.resume,
        project=project_dir,
        name=args.name,
        exist_ok=True,
        patience=args.patience,
        # 数据增强
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

    # 6. 输出结果
    save_dir = getattr(results, 'save_dir', None) or os.path.join(project_dir, args.name)
    best_path = os.path.join(save_dir, 'weights', 'best.pt')

    # 同步 best.pt 到 weights/trained/YOLOv26/best.pt (不带 weights 子目录)
    target_best = os.path.join(save_dir, 'best.pt')
    if os.path.exists(best_path):
        shutil.copy2(best_path, target_best)
        print(f"已同步: {target_best}")

    print(f"\n{'=' * 60}")
    print(f"  训练完成！")
    print(f"  最佳模型: {target_best}")
    print(f"{'=' * 60}")
    print(f"\n  验证模型 (项目根目录):")
    print(f"  .venv-yolo26/bin/python -m ultralytics val data={data_yaml} model={target_best}")
    print(f"\n  使用模型检测 (Ubuntu):")
    print(f"  .venv-yolo26/bin/python src/tools/bag_yolo_detect.py <bag文件> --model {target_best}")
    print(f"\n  使用模型检测 (Windows):")
    print(f"  yolo predict model={target_best} source=<图片/视频路径>")


if __name__ == "__main__":
    main()
