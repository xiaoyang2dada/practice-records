import os
import sys

# 环境兼容 (realpath 解析软链接到真实源码位置, relay 执行时也能正确定位)
_VENV_SITE = os.path.abspath(os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    '..', '..', '..',
    '.venv-yolov7', 'lib', 'python3.8', 'site-packages'))
if os.path.isdir(_VENV_SITE) and _VENV_SITE not in sys.path:
    sys.path.insert(0, _VENV_SITE)

# YOLOv7 官方库 (相对脚本位置: src/lib/yolov7)
_YOLOV7_LIB = os.path.normpath(os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    '..', '..', '..', 'src', 'lib', 'yolov7'))
if os.path.isdir(_YOLOV7_LIB) and _YOLOV7_LIB not in sys.path:
    sys.path.insert(0, _YOLOV7_LIB)

import cv2
import numpy as np
import torch
import torch.nn as nn
from models.common import Conv
from utils.general import non_max_suppression, scale_coords

import rospy
import cv_bridge
from sensor_msgs.msg import Image, CompressedImage
from main_pkg.msg import ConeInfo, ConeArray, ConeDetection2D, ConeDetection2DArray


# 锥桶颜色映射
CLASS_ID_TO_COLOR = {
    0: "red_cone",
    1: "blue_cone",
    2: "yellow_cone",
}

# 可视化颜色 (BGR)
CONE_BGR_COLORS = {
    0: (0, 0, 255),      # red
    1: (255, 0, 0),      # blue
    2: (0, 255, 255),    # yellow
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
    # 绕过 attempt_load 的 attempt_download (路径小写化导致含大写路径的文件找不到)
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


class ConeDetectorV7:
    def __init__(self):
        rospy.init_node("cone_detector_v7", anonymous=False)

        image_topic = rospy.get_param("~image_topic", "/pylon_camera_node/image_raw")
        model_path = rospy.get_param("~model_path", "src/weights/trained/YOLOv7/best.pt")

        # 相对路径转为基于项目根目录的绝对路径
        if not os.path.isabs(model_path):
            model_path = os.path.abspath(os.path.join(
                os.path.dirname(os.path.realpath(__file__)), '../../..', model_path))
        conf_threshold = rospy.get_param("~conf_threshold", 0.3)
        iou_threshold  = rospy.get_param("~iou_threshold", 0.45)
        imgsz = rospy.get_param("~imgsz", 640)
        self.infer_stride = rospy.get_param("~infer_stride", 1)  # 每N帧推理一次(>1跳帧省CPU), 1=不跳帧
        self.publish_2d = rospy.get_param("~publish_2d", False)
        self.show_gui = rospy.get_param("~show_gui", False)
        self.fy_est = rospy.get_param("~fy_depth", 1378.0)
        self.cone_h = rospy.get_param("~cone_height", 0.3)
        self._frame_count = 0   # 跳帧计数
        self._last_det = None   # 最近一次推理结果(供跳帧复用)

        rospy.loginfo(f"加载 YOLOv7 模型: {model_path}")
        if not os.path.exists(model_path):
            rospy.logerr(f"模型文件不存在: {model_path}")
            rospy.signal_shutdown("模型不存在")
            return
        self.model = load_model(model_path, device='cpu')
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.imgsz = imgsz
        self.names = list(self.model.names.values()) if isinstance(self.model.names, dict) else list(self.model.names)
        rospy.loginfo(f"模型类别: {self.names}, imgsz={imgsz}, conf={conf_threshold}, "
                      f"iou={iou_threshold}, infer_stride={self.infer_stride}")

        self.bridge = cv_bridge.CvBridge()

        self.cone_pub = rospy.Publisher("/test/camera_cones", ConeArray, queue_size=10)
        self.annotated_pub = rospy.Publisher("/test/camera_annotated", Image, queue_size=5)

        if self.publish_2d:
            self.cone_2d_pub = rospy.Publisher(
                "/test/camera_cones_2d", ConeDetection2DArray, queue_size=10
            )

        self.sub = self._subscribe_image_topic(image_topic)

        rospy.loginfo(f"YOLOv7 锥桶检测节点已启动，订阅: {image_topic}，发布: /test/camera_cones")

    def _subscribe_image_topic(self, topic_name):
        rospy.loginfo(f"等待图像话题: {topic_name} ...")

        msg_type_str = None
        for attempt in range(30):
            topic_types = dict(rospy.get_published_topics())
            if topic_name in topic_types:
                msg_type_str = topic_types[topic_name]
                break
            rospy.sleep(0.5)

        if msg_type_str is None:
            rospy.logwarn(f"话题 {topic_name} 在 15s 内未出现，使用默认 sensor_msgs/Image")
            return rospy.Subscriber(
                topic_name, Image, self._image_callback_raw,
                queue_size=5, buff_size=2**24
            )

        rospy.loginfo(f"检测到话题类型: {msg_type_str}")
        if "CompressedImage" in msg_type_str:
            return rospy.Subscriber(
                topic_name, CompressedImage, self._image_callback_compressed,
                queue_size=5, buff_size=2**24
            )
        else:
            return rospy.Subscriber(
                topic_name, Image, self._image_callback_raw,
                queue_size=5, buff_size=2**24
            )

    def _image_callback_raw(self, msg):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except cv_bridge.CvBridgeError as e:
            rospy.logerr(f"cv_bridge 转换失败 (raw): {e}")
            return
        self._process_frame(cv_image, msg.header)

    def _image_callback_compressed(self, msg):
        try:
            np_arr = np.frombuffer(msg.data, np.uint8)
            cv_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if cv_image is None:
                rospy.logerr("CompressedImage 解码失败")
                return
        except Exception as e:
            rospy.logerr(f"CompressedImage 解码失败: {e}")
            return
        self._process_frame(cv_image, msg.header)

    def _infer(self, img0):
        # 与官方 detect.py / v8 一致: letterbox 保比例 + 灰边, 避免拉伸变形导致框偏大
        stride = int(self.model.stride.max())
        img, _, _ = letterbox(img0, new_shape=self.imgsz, stride=stride)
        img = img.transpose((2, 0, 1))[::-1]
        img = np.ascontiguousarray(img)
        t = torch.from_numpy(img).float() / 255.0
        t = t.unsqueeze(0)

        with torch.no_grad():
            pred = self.model(t)[0]  # (1, N, 8) cxcywh, 直接传给 NMS (内部会转 xyxy)
        det = non_max_suppression(pred, self.conf_threshold, self.iou_threshold)[0]
        # 坐标映射回原图 (scale_coords 正确处理 letterbox 的缩放与灰边 pad)
        if det is not None and len(det) > 0:
            det[:, :4] = scale_coords(t.shape[2:], det[:, :4], img0.shape[:2]).round()
        return det

    def _process_frame(self, cv_image, header):
        # 跳帧推理: infer_stride>1 时每 N 帧推理一次, 中间帧复用最近结果 (省 CPU)
        if self.infer_stride > 1:
            if self._frame_count % self.infer_stride == 0:
                det = self._infer(cv_image)
                self._last_det = det
            else:
                det = self._last_det  # 复用最近一次推理结果, 不重新推理
            self._frame_count += 1
        else:
            det = self._infer(cv_image)

        self._process_detections(det, cv_image, header)

    def _process_detections(self, det, cv_image, header):
        cone_array = ConeArray()
        cone_array.header.stamp = header.stamp
        cone_array.header.frame_id = header.frame_id if header.frame_id else "camera_frame"

        if self.publish_2d:
            cone_2d_array = ConeDetection2DArray()
            cone_2d_array.header.stamp = header.stamp
            cone_2d_array.header.frame_id = header.frame_id if header.frame_id else "camera_frame"

        if det is not None and len(det) > 0:
            for *xyxy, conf, cls in det.tolist():
                cls_id = int(cls)

                if cls_id not in CLASS_ID_TO_COLOR:
                    continue

                x1, y1, x2, y2 = float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])

                cone_info = ConeInfo()
                cone_info.header.stamp = header.stamp
                cone_info.header.frame_id = header.frame_id if header.frame_id else "camera_frame"
                cone_info.position.x = (x1 + x2) / 2.0   # bbox水平中心 u
                cone_info.position.y = (y1 + y2) / 2.0   # bbox垂直中心 v
                bbox_h = max(y2 - y1, 10.0)
                cone_info.position.z = self.fy_est * self.cone_h / bbox_h  # 深度(m)
                cone_info.color = CLASS_ID_TO_COLOR[cls_id]
                cone_info.confidence = conf
                cone_array.cones.append(cone_info)

                if self.publish_2d:
                    det_2d = ConeDetection2D()
                    det_2d.x1 = x1
                    det_2d.y1 = y1
                    det_2d.x2 = x2
                    det_2d.y2 = y2
                    det_2d.confidence = conf
                    det_2d.color = CLASS_ID_TO_COLOR[cls_id]
                    cone_2d_array.cones.append(det_2d)

                color = CONE_BGR_COLORS.get(cls_id, (0, 255, 0))
                label = f"{CLASS_ID_TO_COLOR[cls_id]} {conf:.2f}"
                cv2.rectangle(cv_image, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                cv2.putText(cv_image, label, (int(x1), int(y1) - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # 发布锥桶坐标
        self.cone_pub.publish(cone_array)

        if self.publish_2d:
            self.cone_2d_pub.publish(cone_2d_array)

        # 发布标注图像（手动构造 Image，绕开 cv_bridge 与新版 OpenCV 的兼容问题）
        annotated = cv2.resize(cv_image, None, fx=0.5, fy=0.5)  # 缩小节省带宽
        ann_msg = Image()
        ann_msg.header.stamp = header.stamp if hasattr(header, 'stamp') else rospy.Time.now()
        ann_msg.header.frame_id = header.frame_id if header.frame_id else "camera_frame"
        ann_msg.height = annotated.shape[0]
        ann_msg.width = annotated.shape[1]
        ann_msg.encoding = "bgr8"
        ann_msg.is_bigendian = False
        ann_msg.step = annotated.shape[1] * 3
        ann_msg.data = annotated.tobytes()
        self.annotated_pub.publish(ann_msg)

        if self.show_gui:
            cv2.imshow("YOLOv7 Cone Detection", cv_image)
            cv2.waitKey(1)

        rospy.loginfo(f"已发布 {len(cone_array.cones)} 个锥桶 → /test/camera_cones")


if __name__ == "__main__":
    try:
        ConeDetectorV7()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
