"""
prepare_dataset.py — FSAC 锥桶数据准备脚本
==========================================
功能：
  1. 将图片 + 标注组织成 YOLOv8 训练所需的目录结构
  2. 生成数据集划分（train/val）
  3. 生成 data.yaml 配置文件
  4. 从 FSACOCO 标注格式转换为 YOLO 格式

用法：
  # 准备训练数据集（图片和标注在同一目录）
  python3 prepare_dataset.py <图片目录> --labels <标注目录>

  # 指定输出目录和划分比例
  python3 prepare_dataset.py ./frames_to_label --output ./cone_dataset --split 0.8

数据集输出结构：
  cone_dataset/
  ├── data.yaml          # YOLO 训练配置
  ├── train/
  │   ├── images/        # 训练图片
  │   └── labels/        # 训练标注
  └── val/
      ├── images/        # 验证图片
      └── labels/        # 验证标注
"""

import os
import sys
import argparse
import shutil
import random
from glob import glob


# ============ 配置 ============
CLASS_NAMES = ['red-cone', 'blue-cone', 'big-yellow-cone']

VALID_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.JPG', '.PNG'}

# FSACOCO 类名到 YOLO class_id 的映射
FSACOCO_CLASS_MAP = {
    'red-cone': 0,
    'blue-cone': 1,
    'big-yellow-cone': 2,
    # 兼容别名
    'r': 0, 'b': 1, 'y': 2,
    'red': 0, 'blue': 1, 'yellow': 2,
}


def find_images(directory):
    """查找目录下所有图片"""
    images = []
    for ext in VALID_EXTENSIONS:
        images.extend(glob(os.path.join(directory, '*' + ext)))
        images.extend(glob(os.path.join(directory, '*' + ext.lower())))
    return sorted(set(images))


def convert_fsacoco_to_yolo(fsacoco_path, image_w, image_h, yolo_path):
    """
    将 FSACOCO 标注格式转换为 YOLO 格式。

    FSACOCO 格式:
      Line 1: N (标注框数量)
      后续行: x1 y1 x2 y2 class_name dist_w dist_h

    YOLO 格式:
      每行: class_id cx cy w h  (归一化)
    """
    if not os.path.exists(fsacoco_path):
        return 0

    yolo_lines = []
    with open(fsacoco_path, 'r') as f:
        lines = f.readlines()

    if not lines:
        return 0

    # 第一行是数量
    start = 1
    try:
        n_boxes = int(lines[0].strip())
    except ValueError:
        # 可能已经是 YOLO 格式了
        n_boxes = 0
        start = 0

    for line in lines[start:]:
        parts = line.strip().split()
        if len(parts) < 5:
            continue

        try:
            x1, y1, x2, y2 = map(int, parts[:4])
            class_name = parts[4]
        except ValueError:
            continue

        if class_name not in FSACOCO_CLASS_MAP:
            print(f"  未知类别: {class_name}，跳过")
            continue

        class_id = FSACOCO_CLASS_MAP[class_name]

        # 转换为 YOLO 归一化坐标
        cx = ((x1 + x2) / 2) / image_w
        cy = ((y1 + y2) / 2) / image_h
        w = abs(x2 - x1) / image_w
        h = abs(y2 - y1) / image_h

        yolo_lines.append(f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")

    if yolo_lines:
        with open(yolo_path, 'w') as f:
            f.write('\n'.join(yolo_lines) + '\n')

    return len(yolo_lines)


def is_yolo_label(label_path):
    """判断标注文件是否已经是 YOLO 格式"""
    if not os.path.exists(label_path):
        return False
    with open(label_path, 'r') as f:
        first_line = f.readline().strip()
    parts = first_line.split()
    # YOLO 格式: 5 个字段 (class_id cx cy w h)
    if len(parts) == 5:
        try:
            cls_id = int(parts[0])
            floats = [float(x) for x in parts[1:]]
            return 0 <= cls_id <= 2 and all(0 <= x <= 1 for x in floats)
        except ValueError:
            pass
    return False


def prepare_dataset(image_dir, label_dir, output_dir, split_ratio=0.8, seed=42):
    """
    准备 YOLOv8 训练数据集。

    Args:
        image_dir:    图片目录
        label_dir:    标注目录（YOLO .txt 或 FSACOCO .txt）
        output_dir:   输出目录
        split_ratio:  训练集比例
        seed:         随机种子
    """
    random.seed(seed)

    # ---- 创建目录结构 ----
    train_img_dir = os.path.join(output_dir, 'train', 'images')
    train_lbl_dir = os.path.join(output_dir, 'train', 'labels')
    val_img_dir = os.path.join(output_dir, 'val', 'images')
    val_lbl_dir = os.path.join(output_dir, 'val', 'labels')

    for d in [train_img_dir, train_lbl_dir, val_img_dir, val_lbl_dir]:
        os.makedirs(d, exist_ok=True)

    # ---- 查找图片 ----
    images = find_images(image_dir)
    if not images:
        print(f"在 {image_dir} 中未找到图片！")
        return

    print(f"找到 {len(images)} 张图片")

    # ---- 匹配图片和标注 ----
    paired = []
    skipped_no_label = 0
    skipped_no_yolo = 0

    for img_path in images:
        base = os.path.splitext(os.path.basename(img_path))[0]

        # 查找标注文件
        yolo_label = os.path.join(label_dir, base + '.txt')
        fsacoco_label = os.path.join(label_dir, base + '_fsacoco.txt')

        label_source = None
        if os.path.exists(yolo_label) and is_yolo_label(yolo_label):
            label_source = yolo_label
        elif os.path.exists(fsacoco_label):
            label_source = fsacoco_label
        elif os.path.exists(yolo_label):
            # 尝试从 FSACOCO 转换
            label_source = yolo_label

        if label_source is None:
            skipped_no_label += 1
            continue

        # 如果是 FSACOCO 格式，需要转换
        if label_source.endswith('_fsacoco.txt') or not is_yolo_label(label_source):
            import cv2
            img = cv2.imread(img_path)
            if img is None:
                continue
            h, w = img.shape[:2]
            converted = convert_fsacoco_to_yolo(label_source, w, h, yolo_label)
            if converted == 0:
                skipped_no_yolo += 1
                continue
            label_source = yolo_label

        paired.append((img_path, label_source))

    print(f"有效配对: {len(paired)} 张")
    if skipped_no_label > 0:
        print(f"无标注文件: {skipped_no_label} 张（跳过）")
    if skipped_no_yolo > 0:
        print(f"无有效标注: {skipped_no_yolo} 张（跳过）")

    if len(paired) == 0:
        print("没有可用的图片-标注配对！")
        return

    # ---- 随机划分 ----
    random.shuffle(paired)
    split_idx = int(len(paired) * split_ratio)
    train_pairs = paired[:split_idx]
    val_pairs = paired[split_idx:]

    # ---- 复制文件 ----
    def copy_pairs(pairs, img_dir, lbl_dir, desc):
        for img_path, lbl_path in pairs:
            ext = os.path.splitext(img_path)[1]
            base = os.path.splitext(os.path.basename(img_path))[0]

            dst_img = os.path.join(img_dir, base + ext)
            dst_lbl = os.path.join(lbl_dir, base + '.txt')

            shutil.copy2(img_path, dst_img)
            if os.path.abspath(lbl_path) != os.path.abspath(dst_lbl):
                shutil.copy2(lbl_path, dst_lbl)

        print(f"{desc}: {len(pairs)} 张")

    copy_pairs(train_pairs, train_img_dir, train_lbl_dir, "训练集")
    copy_pairs(val_pairs, val_img_dir, val_lbl_dir, "验证集")

    # ---- 生成 data.yaml ----
    yaml_path = os.path.join(output_dir, 'data.yaml')
    yaml_content = f"""# FSAC 锥桶检测数据集配置
# 自动生成 by prepare_dataset.py

path: {os.path.abspath(output_dir)}
train: train/images
val: val/images

# 类别数
nc: 3

# 类别名称
names:
  0: red-cone
  1: blue-cone
  2: big-yellow-cone
"""
    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(yaml_content)

    print(f"\n数据集准备完成！")
    print(f"输出目录: {os.path.abspath(output_dir)}")
    print(f"配置文件: {yaml_path}")
    print(f"\n训练命令:")
    print(f"yolo train data={yaml_path} model=yolov8n.pt epochs=100 batch=16 imgsz=640")


def main():
    parser = argparse.ArgumentParser(
        description="FSAC 锥桶数据准备工具 — 组织数据集并生成 YOLO 训练配置"
    )
    parser.add_argument("image_dir", help="图片目录")
    parser.add_argument("--labels", "-l", default=None,
                        help="标注目录 (默认: 与图片同目录)")
    parser.add_argument("--output", "-o", default="./cone_dataset",
                        help="输出数据集目录 (默认: ./cone_dataset)")
    parser.add_argument("--split", "-s", type=float, default=0.8,
                        help="训练集比例 (默认: 0.8)")
    parser.add_argument("--seed", type=int, default=42,
                        help="随机种子 (默认: 42)")
    args = parser.parse_args()

    if not os.path.isdir(args.image_dir):
        print(f"图片目录不存在: {args.image_dir}")
        sys.exit(1)

    label_dir = args.labels if args.labels else args.image_dir
    if not os.path.isdir(label_dir):
        print(f"标注目录不存在: {label_dir}")
        sys.exit(1)

    prepare_dataset(
        image_dir=os.path.abspath(args.image_dir),
        label_dir=os.path.abspath(label_dir),
        output_dir=os.path.abspath(args.output),
        split_ratio=args.split,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
