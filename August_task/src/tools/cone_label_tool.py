"""
基于 FSACOCO 标注规范，使用 Python 3 + OpenCV 实现的现代化标注工具。

类别（与 FSACOCO 一致）：
  0 = red-cone       (红色锥桶)
  1 = blue-cone      (蓝色锥桶)
  2 = big-yellow-cone (大黄色锥桶)

输出格式：
  - YOLO 格式：class_id cx cy w h (归一化，直接可用于训练)
  - FSACOCO 格式：x1 y1 x2 y2 class_name (像素坐标，兼容原格式)

用法：
  python3 cone_label_tool.py <图片目录> [--output 标注输出目录]

操作说明：
  鼠标              - 左键点击两次画框（起点→终点），右键取消
  键盘 1/2/3        - 切换类别：红/蓝/黄
  键盘 R/B/Y        - 同上：R=红, B=蓝, Y=黄
  键盘 A / ←        - 上一张图
  键盘 D / →        - 下一张图
  键盘 Delete       - 删除当前图最后一个框
  键盘 Space        - 暂停/恢复 自动保存提示
  键盘 Q / Esc      - 退出
"""

import os
import sys
import cv2
import numpy as np
from glob import glob

# ============ 配置 ============
CLASS_NAMES = {
    0: "red-cone",
    1: "blue-cone",
    2: "big-yellow-cone",
}
CLASS_COLORS = {
    0: (0, 0, 255),     # 红色 BGR
    1: (255, 0, 0),     # 蓝色 BGR
    2: (0, 255, 255),   # 黄色 BGR
}
# FSACOCO 格式的颜色顺序（红、蓝、黄）
# YOLO 格式 class_id 对应

VALID_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.JPG', '.PNG'}


class ConeLabelTool:
    """FSAC 锥桶标注工具"""

    def __init__(self, image_dir, output_dir=None):
        self.image_dir = os.path.abspath(image_dir)
        self.output_dir = os.path.abspath(output_dir) if output_dir else self.image_dir

        os.makedirs(self.output_dir, exist_ok=True)

        # 加载图片列表
        self.image_paths = []
        for ext in VALID_EXTENSIONS:
            self.image_paths.extend(glob(os.path.join(self.image_dir, '*' + ext)))
            self.image_paths.extend(glob(os.path.join(self.image_dir, '*' + ext.lower())))
        self.image_paths = sorted(set(self.image_paths))

        if not self.image_paths:
            print(f"在 {self.image_dir} 中未找到图片文件！")
            sys.exit(1)

        self.current_idx = 0
        self.current_class = 0  # 默认红色锥桶
        self.bboxes = []        # 当前图片的标注框: [(x1,y1,x2,y2,class_id), ...]
        self.drawing = False
        self.start_point = (-1, -1)
        self.end_point = (-1, -1)
        self.image = None
        self.display_image = None
        self.image_h = 0
        self.image_w = 0
        self.window_name = "FSAC Cone Label Tool"

        print(f"加载了 {len(self.image_paths)} 张图片")
        print(f"标注输出目录: {self.output_dir}")
        print("=" * 60)
        self._print_help()

    def _print_help(self):
        print("""
操作说明:
  1/2/3 或 R/B/Y  - 切换类别 (红/蓝/黄)
  鼠标左键点击两次 - 画框
  鼠标右键 / Esc   - 取消当前框
  A / ← 键        - 上一张
  D / → 键        - 下一张
  Delete 键       - 删除最后一个框
  Q 键            - 保存并退出
  Space 键        - 显示/隐藏帮助
""")

    # ========== 文件操作 ==========

    def _get_label_path(self, image_path, fmt='yolo'):
        """ 获取标注文件路径 """
        base = os.path.splitext(os.path.basename(image_path))[0]
        if fmt == 'yolo':
            return os.path.join(self.output_dir, base + '.txt')
        elif fmt == 'fsacoco':
            return os.path.join(self.output_dir, base + '_fsacoco.txt')

    def _load_labels(self, image_path):
        """加载已有 YOLO 标注"""
        self.bboxes = []
        label_path = self._get_label_path(image_path, 'yolo')
        if not os.path.exists(label_path):
            return

        with open(label_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 5:
                    cls_id = int(parts[0])
                    cx, cy, w, h = map(float, parts[1:])
                    # 转回像素坐标
                    x1 = int((cx - w / 2) * self.image_w)
                    y1 = int((cy - h / 2) * self.image_h)
                    x2 = int((cx + w / 2) * self.image_w)
                    y2 = int((cy + h / 2) * self.image_h)
                    self.bboxes.append((x1, y1, x2, y2, cls_id))

    def _save_labels(self, image_path):
        """保存标注（YOLO + FSACOCO 双格式）"""
        if not self.bboxes:
            # 删除空标注文件
            for fmt in ['yolo', 'fsacoco']:
                lp = self._get_label_path(image_path, fmt)
                if os.path.exists(lp):
                    os.remove(lp)
            return

        # YOLO 格式
        yolo_path = self._get_label_path(image_path, 'yolo')
        with open(yolo_path, 'w') as f:
            for (x1, y1, x2, y2, cls_id) in self.bboxes:
                cx = ((x1 + x2) / 2) / self.image_w
                cy = ((y1 + y2) / 2) / self.image_h
                w = abs(x2 - x1) / self.image_w
                h = abs(y2 - y1) / self.image_h
                f.write(f"{cls_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")

        # FSACOCO 兼容格式
        fsacoco_path = self._get_label_path(image_path, 'fsacoco')
        with open(fsacoco_path, 'w') as f:
            f.write(f"{len(self.bboxes)}\n")
            for (x1, y1, x2, y2, cls_id) in self.bboxes:
                class_name = CLASS_NAMES[cls_id]
                f.write(f"{x1} {y1} {x2} {y2} {class_name} 0.0 0.0\n")

    # ========== 绘制 ==========

    def _draw_all(self):
        """重绘整个画面"""
        self.display_image = self.image.copy()

        # 绘制已有标注框
        for (x1, y1, x2, y2, cls_id) in self.bboxes:
            color = CLASS_COLORS[cls_id]
            cv2.rectangle(self.display_image, (x1, y1), (x2, y2), color, 2)
            name = CLASS_NAMES[cls_id]
            cv2.putText(self.display_image, name, (x1, max(y1 - 5, 15)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # 绘制当前正在画的框
        if self.drawing and self.start_point != (-1, -1):
            cv2.rectangle(self.display_image, self.start_point, self.end_point,
                          CLASS_COLORS[self.current_class], 1)

        # 顶部信息栏
        info = (
            f"Image: {self.current_idx + 1}/{len(self.image_paths)} | "
            f"Class: [{self.current_class}] {CLASS_NAMES[self.current_class]} | "
            f"Boxes: {len(self.bboxes)}"
        )
        cv2.putText(self.display_image, info, (10, self.image_h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2,
                    cv2.LINE_AA)

        # 当前类别颜色指示
        color_block = np.zeros((30, 30, 3), dtype=np.uint8)
        color_block[:] = CLASS_COLORS[self.current_class]
        self.display_image[10:40, 10:40] = color_block
        cv2.putText(self.display_image, CLASS_NAMES[self.current_class],
                    (48, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    CLASS_COLORS[self.current_class], 2)

    def _show(self):
        """显示图片"""
        self._draw_all()
        cv2.imshow(self.window_name, self.display_image)

    # ========== 导航 ==========

    def _load_image(self):
        """加载当前图片及已有标注"""
        path = self.image_paths[self.current_idx]
        self.image = cv2.imread(path)
        if self.image is None:
            print(f"无法读取图片: {path}")
            return False
        self.image_h, self.image_w = self.image.shape[:2]
        self._load_labels(path)
        self.start_point = (-1, -1)
        self.end_point = (-1, -1)
        self.drawing = False
        return True

    def go_next(self):
        """下一张"""
        self._save_labels(self.image_paths[self.current_idx])
        if self.current_idx < len(self.image_paths) - 1:
            self.current_idx += 1
            self._load_image()
            self._show()
        else:
            print("已经是最后一张了")

    def go_prev(self):
        """上一张"""
        self._save_labels(self.image_paths[self.current_idx])
        if self.current_idx > 0:
            self.current_idx -= 1
            self._load_image()
            self._show()
        else:
            print("已经是第一张了")

    # ========== 鼠标回调 ==========

    def _mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if not self.drawing:
                # 第一次点击：起点
                self.start_point = (x, y)
                self.end_point = (x, y)
                self.drawing = True
            else:
                # 第二次点击：完成框
                x1 = min(self.start_point[0], x)
                y1 = min(self.start_point[1], y)
                x2 = max(self.start_point[0], x)
                y2 = max(self.start_point[1], y)

                # 过滤太小的框（最小 10 像素）
                if abs(x2 - x1) >= 10 and abs(y2 - y1) >= 10:
                    self.bboxes.append((x1, y1, x2, y2, self.current_class))
                    print(f" 添加 {CLASS_NAMES[self.current_class]}: "
                          f"({x1},{y1})-({x2},{y2})")

                self.drawing = False
                self.start_point = (-1, -1)
                self._show()

        elif event == cv2.EVENT_MOUSEMOVE and self.drawing:
            self.end_point = (x, y)
            self._show()

        elif event == cv2.EVENT_RBUTTONDOWN:
            # 右键取消当前框
            self.drawing = False
            self.start_point = (-1, -1)
            self._show()

    # ========== 键盘处理 ==========

    def _handle_key(self, key):
        if key == -1:
            return True

        # 数字键 1/2/3 切换类别
        if key == ord('1') or key == ord('r') or key == ord('R'):
            self.current_class = 0
            print(f"切换到: {CLASS_NAMES[self.current_class]}")
        elif key == ord('2') or key == ord('b') or key == ord('B'):
            self.current_class = 1
            print(f"切换到: {CLASS_NAMES[self.current_class]}")
        elif key == ord('3') or key == ord('y') or key == ord('Y'):
            self.current_class = 2
            print(f"切换到: {CLASS_NAMES[self.current_class]}")

        # 导航
        elif key == ord('d') or key == ord('D') or key == 83:  # → 键
            self.go_next()
        elif key == ord('a') or key == ord('A') or key == 81:  # ← 键
            self.go_prev()

        # 删除最后一个框
        elif key == 127 or key == 8:  # Delete / Backspace
            if self.bboxes:
                removed = self.bboxes.pop()
                print(f"  已删除: {CLASS_NAMES[removed[4]]}")
                self._show()

        # 取消当前框
        elif key == 27:  # Esc
            self.drawing = False
            self.start_point = (-1, -1)
            self._show()

        # 帮助
        elif key == ord(' '):
            self._print_help()

        # 退出
        elif key == ord('q') or key == ord('Q'):
            self._save_labels(self.image_paths[self.current_idx])
            print(f"\n标注已保存。共标注 {len(self.image_paths)} 张图片。")
            return False

        return True

    # ========== 主循环 ==========

    def run(self):
        """运行标注工具"""
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(self.window_name, self._mouse_callback)

        self._load_image()
        self._show()

        running = True
        while running:
            key = cv2.waitKey(50) & 0xFF
            running = self._handle_key(key)

            # 检查窗口是否被关闭
            if cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) < 1:
                break

        cv2.destroyAllWindows()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="FSAC 比赛锥桶标注工具")
    parser.add_argument("image_dir", help="图片目录路径")
    parser.add_argument("--output", "-o", default=None, help="标注输出目录 (默认与图片同目录)")
    args = parser.parse_args()

    if not os.path.isdir(args.image_dir):
        print(f"目录不存在: {args.image_dir}")
        sys.exit(1)

    tool = ConeLabelTool(args.image_dir, args.output)
    tool.run()


if __name__ == "__main__":
    main()
