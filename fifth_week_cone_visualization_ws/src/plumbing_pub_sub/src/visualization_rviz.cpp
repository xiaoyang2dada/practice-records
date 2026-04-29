#include "ros/ros.h"
#include "std_msgs/String.h"
#include "plumbing_pub_sub/ConeArray.h"
#include "visualization_msgs/Marker.h"
#include "visualization_msgs/MarkerArray.h"

ros::Publisher g_marker_pub;

void doConeMsg(const plumbing_pub_sub::ConeArray::ConstPtr& msg);

int main(int argc, char *argv[])
{
    setlocale(LC_ALL,"");
    ros::init(argc,argv,"cone_visual");
    ros::NodeHandle nh;

    ros::Subscriber sub = nh.subscribe("/car/cones",10,doConeMsg);
    g_marker_pub = nh.advertise<visualization_msgs::MarkerArray>("/visual/cones",10);

    ros::spin();
    return 0;
}

void doConeMsg(const plumbing_pub_sub::ConeArray::ConstPtr& msg)
{
    visualization_msgs::MarkerArray marker_array;
    int marker_id = 0;
    // ROS_INFO("回调函数被触发");
    for(int i=0;i<msg->cones.size();i++)
    {
        // 初始化visualization_msgs
        visualization_msgs::Marker marker;
        marker.header.frame_id = "base_link";
        marker.header.stamp = ros::Time::now();
        marker.ns = "car_cones";
        marker.id = marker_id++;
        marker.type = visualization_msgs::Marker::CYLINDER;
        marker.action = visualization_msgs::Marker::ADD;

        // 坐标导入
        marker.pose.position.x = msg->cones[i].position.x;
        marker.pose.position.y = msg->cones[i].position.y;
        marker.pose.position.z = msg->cones[i].position.z;
        marker.pose.orientation.w = 1.0;

        // 设置圆柱规模
        marker.scale.x = 0.2;
        marker.scale.y = 0.2;
        marker.scale.z = 0.6;

        // 只识别 red、blue 两种颜色
        if(msg->cones[i].color == "red_cone")
        {
            // 红色
            marker.color.r = 1.0;
            marker.color.g = 0.0;
            marker.color.b = 0.0;
        }
        else if(msg->cones[i].color == "blue_cone")
        {
            // 蓝色
            marker.color.r = 0.0;
            marker.color.g = 0.0;
            marker.color.b = 1.0;
        }
        else
        {
            // 其他默认白色
            marker.color.r = 1.0;
            marker.color.g = 1.0;
            marker.color.b = 1.0;
        }
        marker.color.a = 1.0;

        marker_array.markers.push_back(marker);
    }

    g_marker_pub.publish(marker_array);
}