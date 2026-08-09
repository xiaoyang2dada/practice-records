#include "ros/ros.h"
#include "main_pkg/ConeArray.h"
#include <cmath>

// 全局变量
ros::Publisher g_cone_pub;

// 相机内参（标定后的默认值）
double g_fx = 1379.0, g_fy = 1378.0;
double g_cx = 984.0,  g_cy = 611.0;

// 外参（相机在车体坐标系的安装位置）
double g_tx = 0.3, g_ty = 0.0, g_tz = 0.5;

// 函数声明
void doMsg(const main_pkg::ConeArray::ConstPtr &msg);
bool loadParams(ros::NodeHandle &nh);

// 主函数
int main(int argc, char *argv[])
{
    setlocale(LC_ALL, "");
    ros::init(argc, argv, "camera");
    ros::NodeHandle nh("~");

    if (!loadParams(nh)) { ROS_ERROR("参数加载失败!"); return 1; }

    ros::NodeHandle nh_global;
    g_cone_pub = nh_global.advertise<main_pkg::ConeArray>("/yolov7/yolov7/all_cones", 10);
    ros::Subscriber sub = nh_global.subscribe<main_pkg::ConeArray>(
        "/test/camera_cones", 10, doMsg);

    ROS_INFO("坐标转换节点已启动 (对齐学长 detect_ros.py)");
    ROS_INFO("  内参: fx=%.1f fy=%.1f cx=%.1f cy=%.1f", g_fx, g_fy, g_cx, g_cy);
    ROS_INFO("  安装: (%.2f, %.2f, %.2f)m", g_tx, g_ty, g_tz);
    ros::spin();
    return 0;
}

// 加载参数
bool loadParams(ros::NodeHandle &nh)
{
    nh.param("fx", g_fx, 1379.0);
    nh.param("fy", g_fy, 1378.0);
    nh.param("cx", g_cx, 984.0);
    nh.param("cy", g_cy, 611.0);
    nh.param("camera_x", g_tx, 0.3);
    nh.param("camera_y", g_ty, 0.0);
    nh.param("camera_z", g_tz, 0.5);
    return true;
}

void doMsg(const main_pkg::ConeArray::ConstPtr &msg)
{
    ROS_INFO("=== 接收锥桶: %zu 个 ===", msg->cones.size());

    main_pkg::ConeArray car_cones;
    car_cones.header.frame_id = "base_link";
    car_cones.header.stamp = ros::Time::now();

    if (msg->cones.empty()) { g_cone_pub.publish(car_cones); return; }

    for (size_t i = 0; i < msg->cones.size(); ++i)
    {
        double u     = msg->cones[i].position.x;
        double v     = msg->cones[i].position.y;
        double depth = msg->cones[i].position.z;

        if (depth <= 0.0) continue;

        // 1. back-project → 相机坐标系 (X右 Y上 Z前)
        double Xc = (u - g_cx) * depth / g_fx;
        double Yc = (g_cy - v) * depth / g_fy;   // cy-v, 非 v-cy!
        double Zc = depth;

        // 2. 相机→车体: R=[[0,0,1],[-1,0,0],[0,1,0]]
        double car_x =  Zc + g_tx;    // 0*Xc + 0*Yc + 1*Zc + tx
        double car_y = -Xc + g_ty;    // -1*Xc + 0*Yc + 0*Zc + ty
        double car_z =  Yc + g_tz;    // 0*Xc + 1*Yc + 0*Zc + tz

        ROS_INFO("  锥桶[%zu]: px(%.0f,%.0f) d=%.2f → car(%.2f,%.2f,%.2f)m %s",
                 i+1, u, v, depth, car_x, car_y, car_z, msg->cones[i].color.c_str());

        main_pkg::ConeInfo cone;
        cone.header.stamp = msg->cones[i].header.stamp;
        cone.header.frame_id = "base_link";
        cone.position.x = car_x; cone.position.y = car_y; cone.position.z = car_z;
        cone.color = msg->cones[i].color;
        cone.confidence = msg->cones[i].confidence;
        car_cones.cones.push_back(cone);
    }

    g_cone_pub.publish(car_cones);
    ROS_INFO("已发布 %zu 个 → /yolov7/yolov7/all_cones", car_cones.cones.size());
}