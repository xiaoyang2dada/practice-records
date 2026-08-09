"""
prepare_voc_dataset.py — VOC XML 格式锥桶数据集 → YOLO 格式转换
==============================================================
功能：
  1. 读取 Pascal VOC XML 标注文件
  2. 转换为 YOLO 格式 (class_id cx cy w h, 归一化)
  3. 划分 train/val 数据集
  4. 生成 data.yaml 配置文件

用法：
  python3 prepare_voc_dataset.py "F:/桌面/dataset/my(BUAA+FZU+WUST)"
  python3 prepare_voc_dataset.py "F:/桌面/dataset/my(BUAA+FZU+WUST)" --split 0.85

数据集结构要求：
  dataset_root/
  ├── jpg/          # 图片文件
  └── xml/          # Pascal VOC XML 标注文件

输出：
  dataset_root/
  ├── labels/       # YOLO 格式标注 (与 jpg 中图片一一对应)
  └── cone_data.yaml  # YOLOv8 训练配置文件
"""

import os
import sys
import argparse
import random
import xml.etree.ElementTree as ET
from glob import glob
from pathlib import Path


# ============ 类别配置 ============
# VOC XML 中 <name> 标签 → YOLO class_id
CLASS_NAME_TO_ID = {
    'red': 0,
    'blue': 1,
    'yellow': 2,
    # 兼容中英文别名
    '红色锥桶': 0, 'red-cone': 0,
    '蓝色锥桶': 1, 'blue-cone': 1,
    '黄色锥桶': 2, 'yellow-cone': 2,
    'big-yellow-cone': 2,
}

# YOLO 类别名列表 (顺序必须与 class_id 一致)
CLASS_NAMES = ['red', 'blue', 'yellow']


def parse_voc_xml(xml_path):
    """
    解析 Pascal VOC XML 文件，返回:
      - size: (width, height)
      - objects: [(class_name, xmin, ymin, xmax, ymax), ...]
    如果解析失败返回 None
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        size_elem = root.find('size')
        if size_elem is None:
            return None
        width = int(size_elem.find('width').text)
        height = int(size_elem.find('height').text)

        objects = []
        for obj in root.findall('object'):
            name = obj.find('name').text.strip()
            bndbox = obj.find('bndbox')
            xmin = int(float(bndbox.find('xmin').text))
            ymin = int(float(bndbox.find('ymin').text))
            xmax = int(float(bndbox.find('xmax').text))
            ymax = int(float(bndbox.find('ymax').text))
            objects.append((name, xmin, ymin, xmax, ymax))

        return (width, height), objects
    except Exception as e:
        print(f"  ⚠ 解析失败 {xml_path}: {e}")
        return None


def voc_to_yolo(size, obj):
    """
    将 VOC 格式的单个标注框转换为 YOLO 格式。

    VOC: (xmin, ymin, xmax, ymax)
    YOLO: (class_id, cx, cy, w, h)  全部归一化到 [0, 1]
    """
    class_name, xmin, ymin, xmax, ymax = obj
    width, height = size

    # 类别映射
    class_id = CLASS_NAME_TO_ID.get(class_name, -1)
    if class_id == -1:
        return None  # 未知类别，跳过

    # 边界检查
    xmin = max(0, min(xmin, width - 1))
    ymin = max(0, min(ymin, height - 1))
    xmax = max(1, min(xmax, width))
    ymax = max(1, min(ymax, height))

    # 转为中心点 + 宽高，归一化
    cx = ((xmin + xmax) / 2.0) / width
    cy = ((ymin + ymax) / 2.0) / height
    w = (xmax - xmin) / width
    h = (ymax - ymin) / height

    # 防止超出边界
    cx = max(0.0, min(cx, 1.0))
    cy = max(0.0, min(cy, 1.0))
    w = max(0.0, min(w, 1.0))
    h = max(0.0, min(h, 1.0))

    return (class_id, cx, cy, w, h)


def find_image_file(jpg_dir, xml_name):
    """根据 xml 文件名查找对应的图片文件"""
    base = os.path.splitext(xml_name)[0]
    for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.JPG', '.JPEG', '.PNG']:
        img_path = os.path.join(jpg_dir, base + ext)
        if os.path.exists(img_path):
            return img_path
    return None


def main():
    parser = argparse.ArgumentParser(
        description="VOC XML 锥桶数据集 → YOLO 格式转换"
    )
    parser.add_argument(
        "dataset_root",
        help="数据集根目录 (包含 jpg/ 和 xml/ 子目录)"
    )
    parser.add_argument(
        "--split", "-s", type=float, default=0.85,
        help="训练集比例 (默认: 0.85, 即 85%% 训练 / 15%% 验证)"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="随机种子 (默认: 42)"
    )
    parser.add_argument(
        "--no-shuffle", action="store_true",
        help="不打乱数据顺序"
    )
    args = parser.parse_args()

    dataset_root = os.path.abspath(args.dataset_root)
    jpg_dir = os.path.join(dataset_root, 'jpg')
    xml_dir = os.path.join(dataset_root, 'xml')
    # 标注直接放在 jpg/ 目录中，与图片同名 .txt（YOLOv8 自动识别）
    labels_dir = jpg_dir
    yaml_path = os.path.join(dataset_root, 'cone_data.yaml')

    # 验证目录
    if not os.path.isdir(jpg_dir):
        print(f"图片目录不存在: {jpg_dir}")
        sys.exit(1)
    if not os.path.isdir(xml_dir):
        print(f"标注目录不存在: {xml_dir}")
        sys.exit(1)

    # 创建 labels 输出目录
    os.makedirs(labels_dir, exist_ok=True)

    # ============ 第1步: 扫描 XML 文件并转换 ============
    print("=" * 60)
    print("VOC XML → YOLO 格式转换")
    print("=" * 60)
    print(f"数据集根目录: {dataset_root}")
    print(f"图片目录:     {jpg_dir}")
    print(f"标注目录:     {xml_dir}")
    print(f"输出目录:     {labels_dir}")
    print(f"训练集比例:   {args.split:.0%}")
    print("-" * 60)

    xml_files = sorted(glob(os.path.join(xml_dir, '*.xml')))
    print(f"找到 {len(xml_files)} 个 XML 标注文件\n")

    samples = []  # [(img_path, label_path), ...]
    total_boxes = 0
    class_counts = {name: 0 for name in CLASS_NAMES}
    skipped_unknown = 0
    skipped_no_img = 0
    skipped_parse_error = 0

    for i, xml_path in enumerate(xml_files):
        xml_name = os.path.basename(xml_path)

        # 查找对应图片
        img_path = find_image_file(jpg_dir, xml_name)
        if img_path is None:
            skipped_no_img += 1
            if (i + 1) % 500 == 0:
                print(f"  进度: {i+1}/{len(xml_files)} ...")
            continue

        # 解析 XML
        result = parse_voc_xml(xml_path)
        if result is None:
            skipped_parse_error += 1
            continue

        size, objects = result

        # 转换为 YOLO 格式
        yolo_lines = []
        for obj in objects:
            yolo_result = voc_to_yolo(size, obj)
            if yolo_result is None:
                skipped_unknown += 1
                continue
            class_id, cx, cy, w, h = yolo_result
            yolo_lines.append(f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
            class_counts[CLASS_NAMES[class_id]] += 1
            total_boxes += 1

        # 写入 YOLO label 文件
        base_name = os.path.splitext(xml_name)[0]
        label_path = os.path.join(labels_dir, base_name + '.txt')
        with open(label_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(yolo_lines))

        samples.append((img_path, label_path))

        if (i + 1) % 500 == 0:
            print(f"  进度: {i+1}/{len(xml_files)}... (已转换 {total_boxes} 个框)")

    print(f"\n转换完成！")
    print(f"  有效样本数:   {len(samples)}")
    print(f"  总标注框数:   {total_boxes}")
    print(f"  各类统计:")
    for name in CLASS_NAMES:
        print(f"    {name}: {class_counts[name]}")
    if skipped_no_img:
        print(f"  无对应图片:   {skipped_no_img}")
    if skipped_parse_error:
        print(f"  解析失败:     {skipped_parse_error}")
    if skipped_unknown:
        print(f"  未知类别:     {skipped_unknown}")

    if len(samples) == 0:
        print("\n❌ 没有有效样本，请检查数据集！")
        sys.exit(1)

    # ============ 第2步: 划分 train/val ============
    print(f"\n{'=' * 60}")
    print("划分训练集 / 验证集")
    print("=" * 60)

    if not args.no_shuffle:
        random.seed(args.seed)
        random.shuffle(samples)

    split_idx = int(len(samples) * args.split)
    train_samples = samples[:split_idx]
    val_samples = samples[split_idx:]

    print(f"  训练集: {len(train_samples)} 张")
    print(f"  验证集: {len(val_samples)} 张")

    # 生成图片路径列表文件（相对于 dataset_root）
    train_txt_path = os.path.join(dataset_root, 'train.txt')
    val_txt_path = os.path.join(dataset_root, 'val.txt')

    with open(train_txt_path, 'w', encoding='utf-8') as f:
        for img_path, _ in train_samples:
            f.write(img_path + '\n')

    with open(val_txt_path, 'w', encoding='utf-8') as f:
        for img_path, _ in val_samples:
            f.write(img_path + '\n')

    print(f"  train 列表: {train_txt_path}")
    print(f"  val 列表:   {val_txt_path}")

    # ============ 第3步: 生成 data.yaml ============
    print(f"\n{'=' * 60}")
    print("生成 data.yaml 配置文件")
    print("=" * 60)

    # YOLOv8 data.yaml: train/val 指向图片路径列表文件
    # 标注 .txt 文件与图片在同一目录（jpg/），YOLOv8 自动匹配
    yaml_content = f"""# FSAC 锥桶检测数据集配置 (YOLOv8)
# 自动生成 — {len(train_samples)} train / {len(val_samples)} val / {len(CLASS_NAMES)} classes
# 标注文件与图片同目录 ({jpg_dir})

path: {dataset_root}
train: {train_txt_path}
val: {val_txt_path}
test: {val_txt_path}

nc: {len(CLASS_NAMES)}
names:
"""
    for i, name in enumerate(CLASS_NAMES):
        yaml_content += f"  {i}: {name}\n"

    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(yaml_content)

    print(f"  ✅ {yaml_path}")
    print(f"\n{'=' * 60}")
    print("全部完成！")
    print("=" * 60)
    print(f"\n数据集统计:")
    print(f"  图片总数: {len(samples)}")
    print(f"  标注框数: {total_boxes}")
    for name in CLASS_NAMES:
        print(f"  {name}: {class_counts[name]}")
    print(f"\n开始训练 (Windows):")
    print(f"  cd results")
    print(f"  python train.py --data \"{yaml_path}\"")
    print(f"\n或直接使用默认路径一键训练:")
    print(f"  python train.py")


if __name__ == "__main__":
    main()
