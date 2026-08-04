# 🖥️ 台式机训练操作手册

> 笔记本老，纯 CPU 太慢 → 回家用 CUDA 台式机训练，几分钟完事

---

## 📦 一、从笔记本拷到台式机

```
笔记本 → U盘/网盘 → 台式机
═══════════════════════════════════════
1. 数据集 (约 3GB)
   F:\桌面\dataset\my(BUAA+FZU+WUST)\
   ├── jpg/          # 图片 (0.jpg ~ 3082.jpg)
   └── xml/          # 标注 (Pascal VOC XML)

2. 脚本目录
   August_task\results\
   ├── train_cone.py              # 训练脚本
   ├── prepare_voc_dataset.py     # VOC→YOLO 转换脚本
   └── requirements.txt           # Python 依赖
```

---

## 🔧 二、台式机安装环境

```powershell
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

需要安装的包：`ultralytics`、`opencv-python`、`numpy`、`torch`

---

## ✏️ 三、修改数据集路径

打开 `train_cone.py`，找到第 27 行，改成台式机上的实际路径：

```python
# 修改前
DEFAULT_DATASET_DIR = r"F:\桌面\dataset\my(BUAA+FZU+WUST)"

# 修改后 (举例)
DEFAULT_DATASET_DIR = r"D:\datasets\cone_dataset"
```

---

## 🚀 四、开始训练

```powershell
cd results
python train_cone.py --model yolov8s.pt --epochs 200 --batch 16
```

| 参数 | 说明 |
|------|------|
| `--model yolov8s.pt` | 中等模型，精度和速度平衡 |
| `--epochs 200` | 训练 200 轮 |
| `--batch 16` | 批次大小（显卡够就 16，不够改 8） |

脚本会自动：
1. 检测到 GPU → 用 CUDA（秒级完成）
2. 读 VOC XML → 转 YOLO 格式
3. 85%/15% 划分训练/验证集
4. 开始训练

> ⏱ 预计耗时：**5～8 分钟**（RTX 3060 级别）

---

## 📤 五、训练完拷回笔记本

**只需要一个文件：**

```
台式机:  runs/detect/cone_detect/weights/best.pt  (约 22MB)
                 ↓  拷贝到
笔记本:  August_task/results/best.pt
```

---

## 🎯 六、笔记本上推理检测

```powershell
cd August_task/results
python bag_yolo_detect.py ../fifth_week_tasks/src/plumbing_pub_sub/bag/test.bag --model best.pt
```

| 参数 | 说明 |
|------|------|
| `--model best.pt` | 训练好的锥桶检测模型 |
| `--conf 0.35` | 置信度阈值（可选） |
| `--output result.mp4` | 输出视频路径（可选） |

---

## 📋 速查卡片

| 步骤 | 在哪里 | 命令 |
|------|:--:|------|
| 装环境 | 🖥️ 台式 | `pip install -r requirements.txt` |
| 改路径 | 🖥️ 台式 | 编辑 `train_cone.py` 第 27 行 |
| 训练 | 🖥️ 台式 | `python train_cone.py --model yolov8s.pt --epochs 200 --batch 16` |
| 拷回 | 📤 → 💻 | 只拿 `best.pt`（22MB） |
| 推理 | 💻 笔记本 | `python bag_yolo_detect.py <bag> --model best.pt` |

---

## 🌙 可选：过夜训练大模型

如果想追求最高精度，可以换大模型多跑几轮：

```powershell
# 大模型训练（更久但更准）
python train_cone.py --model yolov8m.pt --epochs 500 --batch 8

# 小模型快速验证
python train_cone.py --model yolov8n.pt --epochs 100 --batch 32
```
