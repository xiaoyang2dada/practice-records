#include "ros/ros.h"
#include "plumbing_pub_sub/ConeArray.h"
#include "std_msgs/String.h"
#include "visualization_msgs/MarkerArray.h"

// 全局发布者
ros::Publisher g_cone_pub;

void doMsg(const plumbing_pub_sub::ConeArray::ConstPtr &msg);

int main(int argc, char *argv[])
{
    setlocale(LC_ALL,"");
    //2.初始化 ROS 节点
    ros::init(argc,argv,"camera");
    //3.创建节点句柄
    ros::NodeHandle nh;
    //4-1.初始化发布者
    g_cone_pub = nh.advertise<plumbing_pub_sub::ConeArray>("/car/cones",10);
    //4-2.创建订阅者对象
    ros::Subscriber sub = nh.subscribe<plumbing_pub_sub::ConeArray>("/test/camera_cones",10,doMsg);
    //5.处理订阅到的数据
    ros::spin();



    return 0;
}

void doMsg(const plumbing_pub_sub::ConeArray::ConstPtr &msg)
{
    ROS_INFO("=== 成功接收锥桶数组数据 ===");
    ROS_INFO("锥桶数量: %zu", msg->cones.size());
    
    // 初始化车体坐标系的锥桶数组消息
    plumbing_pub_sub::ConeArray base_cones;
    base_cones.header.frame_id = "base_link";
    base_cones.header.stamp = ros::Time::now();

    if(msg->cones.empty())
    {
        ROS_WARN("收到的消息为空");
    }
    // ROS_INFO("锥桶数量为：%zu",msg->cones.size());
    
    // 遍历所有锥桶
    for(size_t i = 0; i < msg->cones.size(); ++i)
    {
        // 取出像素坐标 u, v
        double u = msg->cones[i].position.x;
        double v = msg->cones[i].position.y;

        // 转换为米制坐标
        double x_m = u / 100;
        double y_m = 0.0;
        double z_m = v / 100;

        // 转换为车体坐标系
        // 旋转矩阵
        const double R11 = std::sqrt(3) / 2;
        const double R12 = 0.5;
        const double R21 = -0.5;
        const double R22 = std::sqrt(3) / 2;
        // 偏移量
        const double TX = -0.3;
        const double TY = 0.1;
        const double TZ = 0.95;
        // 坐标系对齐
        double base_x = z_m;
        double base_y = -x_m;
        double base_z = -y_m;

        // 转换
        double car_x = TX + R11 * base_x + R12 * base_y;
        double car_y = TY + R21 * base_x + R22 * base_y;
        double car_z = TZ;

        ROS_INFO("锥桶 [%zu]: camera_pos=(%.2fm, %.2fm, %.2fm), color='%s', car_pos=(%.2fm, %.2fm, %.2f)", 
                  i + 1,
                  x_m,
                  y_m,
                  z_m,
                  msg->cones[i].color.c_str(),
                  car_x,
                  car_y,
                  car_z
                  );

        // 将数据传入ConeInfo
        plumbing_pub_sub::ConeInfo base_cone;
        base_cone.position.x = car_x;
        base_cone.position.y = car_y;
        base_cone.position.z = car_z;
        base_cone.color = msg->cones[i].color;

        // 加入车体锥桶数组
        base_cones.cones.push_back(base_cone);
    }

    // 发布车体坐标系锥桶话题
    g_cone_pub.publish(base_cones);
    ROS_INFO("已发布 %zu 个车体坐标系锥桶到话题 /car/cones 中", base_cones.cones.size());
}