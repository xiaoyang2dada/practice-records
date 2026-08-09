import os
import sys

# 环境兼容
_VENV_SITE = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', '..', '..',
    '.venv', 'lib', 'python3.8', 'site-packages'))
if os.path.isdir(_VENV_SITE) and _VENV_SITE not in sys.path:
    sys.path.insert(0, _VENV_SITE)

import cv2
import numpy as np

import rospy
import cv_bridge
from sensor_msgs.msg import Image, CompressedImage
from main_pkg.msg import ConeInfo, ConeArray, ConeDetection2D, ConeDetection2DArray

from ultralytics import YOLO


# 锥桶颜色映射
# YOLO class_id → ROS color string
CLASS_ID_TO_COLOR = {
    0: "red_cone",
    1: "blue_cone",
    2: "yellow_cone",
}

# 可视化颜色 (BGR)
CONE_BGR_COLORS = {
    0: (0, 0, 255),      # red   → 红色框
    1: (255, 0, 0),      # blue  → 蓝色框
    2: (0, 255, 255),    # yellow → 青色框
}


class ConeDetector:
    def __init__(self):
        rospy.init_node("cone_detector", anonymous=False)

        # 读取参数
        image_topic = rospy.get_param("~image_topic", "/pylon_camera_node/image_raw")
        model_path = rospy.get_param("~model_path", "yolov8n.pt")
        conf_threshold = rospy.get_param("~conf_threshold", 0.5)
        iou_threshold  = rospy.get_param("~iou_threshold", 0.45)   # NMS IoU 阈值
        imgsz = rospy.get_param("~imgsz", 320)           # 推理尺寸，小值省内存
        self.publish_2d = rospy.get_param("~publish_2d", False)
        self.show_gui = rospy.get_param("~show_gui", False)
        self.fy_est = rospy.get_param("~fy_depth", 1000.0)  # 深度估算用 fy
        self.cone_h = rospy.get_param("~cone_height", 0.3)   # 锥桶真实高度(m)

        # 初始化 YOLO
        rospy.loginfo(f"加载 YOLO 模型: {model_path}")
        if not os.path.exists(model_path):
            rospy.logwarn(f"模型文件不存在: {model_path}，尝试从 ultralytics 下载...")
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.imgsz = imgsz
        rospy.loginfo(f"模型类别: {list(self.model.names.values())}, "
                      f"imgsz={imgsz}, conf={conf_threshold}, iou={iou_threshold}")

        # 初始化cv_bridge
        self.bridge = cv_bridge.CvBridge()

        # 发布方
        # 主话题：3D 锥桶位置
        self.cone_pub = rospy.Publisher("/test/camera_cones", ConeArray, queue_size=10)

        # 检测标注图像（RViz 中显示）
        self.annotated_pub = rospy.Publisher("/test/camera_annotated", Image, queue_size=5)

        # 可选：2D 检测结果（带检测框和置信度）
        if self.publish_2d:
            self.cone_2d_pub = rospy.Publisher(
                "/test/camera_cones_2d", ConeDetection2DArray, queue_size=10
            )

        # 订阅方
        # 自动检测话题类型并订阅
        self.sub = self._subscribe_image_topic(image_topic)

        rospy.loginfo(f"锥桶检测节点已启动，订阅: {image_topic}，发布: /test/camera_cones")
        if self.publish_2d:
            rospy.loginfo(f"同时发布 2D 检测结果到: /test/camera_cones_2d")

    def _subscribe_image_topic(self, topic_name):
        """等待图像话题出现，自动匹配消息类型后订阅"""
        rospy.loginfo(f"等待图像话题: {topic_name} ...")

        # 轮询等待话题在ROS master中注册（最多等 15 秒）
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
        """处理 sensor_msgs/Image 消息"""
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except cv_bridge.CvBridgeError as e:
            rospy.logerr(f"cv_bridge 转换失败 (raw): {e}")
            return
        self._process_frame(cv_image, msg.header)

    def _image_callback_compressed(self, msg):
        """处理 sensor_msgs/CompressedImage 消息"""
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

    def _process_frame(self, cv_image, header):
        # YOLOv8 推理
        results = self.model(cv_image, conf=self.conf_threshold,
                             iou=self.iou_threshold, imgsz=self.imgsz, verbose=False)

        # 构造 ConeArray 消息
        cone_array = ConeArray()
        cone_array.header.stamp = header.stamp  # 保留原始时间戳
        cone_array.header.frame_id = header.frame_id if header.frame_id else "camera_frame"

        # 可选：构造2D检测结果
        if self.publish_2d:
            cone_2d_array = ConeDetection2DArray()
            cone_2d_array.header.stamp = header.stamp
            cone_2d_array.header.frame_id = header.frame_id if header.frame_id else "camera_frame"

        if results and len(results) > 0:
            boxes = results[0].boxes
            if boxes is not None:
                for box in boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])

                    # 只识别锥桶类别（0=red, 1=blue, 2=yellow）
                    if cls_id not in CLASS_ID_TO_COLOR:
                        continue

                    # 边界框坐标
                    x1, y1, x2, y2 = map(float, box.xyxy[0].tolist())

                    # 构造ConeInfo
                    cone_info = ConeInfo()
                    cone_info.header.stamp = header.stamp
                    cone_info.header.frame_id = header.frame_id if header.frame_id else "camera_frame"
                    cone_info.position.x = (x1 + x2) / 2.0   # bbox水平中心 u
                    cone_info.position.y = (y1 + y2) / 2.0   # bbox垂直中心 v
                    bbox_h = max(y2 - y1, 10.0)              # bbox像素高度, 最小10防除零
                    cone_info.position.z = self.fy_est * self.cone_h / bbox_h  # 深度(m)
                    cone_info.color = CLASS_ID_TO_COLOR[cls_id]
                    cone_info.confidence = conf
                    cone_array.cones.append(cone_info)

                    # 构造 ConeDetection2D（含检测框完整信息）
                    if self.publish_2d:
                        det_2d = ConeDetection2D()
                        det_2d.x1 = x1
                        det_2d.y1 = y1
                        det_2d.x2 = x2
                        det_2d.y2 = y2
                        det_2d.confidence = conf
                        det_2d.color = CLASS_ID_TO_COLOR[cls_id]
                        cone_2d_array.cones.append(det_2d)

                    # 绘制检测框（始终绘制，用于发布标注图像）
                    color = CONE_BGR_COLORS.get(cls_id, (0, 255, 0))
                    label = f"{CLASS_ID_TO_COLOR[cls_id]} {conf:.2f}"
                    cv2.rectangle(cv_image, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                    cv2.putText(cv_image, label, (int(x1), int(y1) - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # 发布锥桶坐标
        self.cone_pub.publish(cone_array)

        if self.publish_2d:
            self.cone_2d_pub.publish(cone_2d_array)

        # 发布标注图像（RViz 可订阅 /test/camera_annotated）
        annotated = cv2.resize(cv_image, None, fx=0.5, fy=0.5)  # 缩小节省带宽
        img_msg = Image()
        img_msg.header.stamp = header.stamp if hasattr(header, 'stamp') else rospy.Time.now()
        img_msg.header.frame_id = header.frame_id if header.frame_id else "camera_frame"
        img_msg.height = annotated.shape[0]
        img_msg.width = annotated.shape[1]
        img_msg.encoding = "bgr8"
        img_msg.is_bigendian = False
        img_msg.step = annotated.shape[1] * 3
        img_msg.data = annotated.tobytes()
        self.annotated_pub.publish(img_msg)

        # 定时日志
        seq = header.seq if hasattr(header, 'seq') else 0
        if seq % 30 == 0:
            rospy.loginfo_throttle(3, f"检测到 {len(cone_array.cones)} 个锥桶")

        # GUI 显示
        if self.show_gui:
            cv2.putText(cv_image, f"cones: {len(cone_array.cones)}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.imshow("Cone Detector", cv_image)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                rospy.signal_shutdown("用户按 Q 退出")

    def shutdown(self):
        # 节点关闭时的清理
        if self.show_gui:
            cv2.destroyAllWindows()
        rospy.loginfo("锥桶检测节点已关闭")


if __name__ == "__main__":
    detector = ConeDetector()
    rospy.on_shutdown(detector.shutdown)
    try:
        rospy.spin()
    except KeyboardInterrupt:
        pass
    finally:
        detector.shutdown()
