import rospy
import cv2
from sensor_msgs.msg import Image
from pypylon import pylon


def main():
    rospy.init_node("pylon_image_publisher", anonymous=False)

    tl = pylon.TlFactory.GetInstance()
    devices = tl.EnumerateDevices()
    if not devices:
        rospy.logerr("未检测到 Basler 相机！请检查 USB3.0 连接")
        return
    rospy.loginfo(f"打开相机: {devices[0].GetModelName()} SN={devices[0].GetSerialNumber()}")

    camera = pylon.InstantCamera(tl.CreateDevice(devices[0]))
    camera.Open()

    nm = camera.NodeMap
    try:
        nm.GetNode("ExposureAuto").SetValue("Continuous")
        nm.GetNode("GainAuto").SetValue("Continuous")
        nm.GetNode("AutoTargetBrightness").SetValue(0.5)
        nm.GetNode("AutoExposureTimeUpperLimit").SetValue(80000)
        nm.GetNode("AutoGainUpperLimit").SetValue(15)
        rospy.loginfo("自动曝光已启用")
    except Exception as e:
        rospy.logwarn(f"自动曝光设置失败: {e}")

    camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
    converter = pylon.ImageFormatConverter()
    converter.OutputPixelFormat = pylon.PixelType_BGR8packed

    pub = rospy.Publisher("/pylon_camera_node/image_raw", Image, queue_size=5)
    rate = rospy.Rate(30)

    rospy.loginfo("开始发布图像到 /pylon_camera_node/image_raw ...")
    while not rospy.is_shutdown():
        grab = camera.RetrieveResult(3000, pylon.TimeoutHandling_ThrowException)
        if grab.GrabSucceeded():
            img = converter.Convert(grab).GetArray()
            if img.shape[2] == 4:
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            # 手动构造Image消息，绕过cv_bridge兼容问题
            msg = Image()
            msg.header.stamp = rospy.Time.now()
            msg.header.frame_id = "camera_frame"
            msg.height = img.shape[0]
            msg.width = img.shape[1]
            msg.encoding = "bgr8"
            msg.is_bigendian = False
            msg.step = img.shape[1] * 3
            msg.data = img.tobytes()
            pub.publish(msg)
        grab.Release()
        rate.sleep()

    camera.StopGrabbing()
    camera.Close()


if __name__ == "__main__":
    main()
