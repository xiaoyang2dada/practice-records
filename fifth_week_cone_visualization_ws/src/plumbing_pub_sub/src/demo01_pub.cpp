#include "ros/ros.h"
#include "std_msgs/String.h"
#include "plumbing_pub_sub/ConeArray.h"
#include "visualization_msgs/Marker.h"
#include "visualization_msgs/MarkerArray.h"


int main(int argc, char *argv[])
{
    setlocale(LC_ALL,"");
    ros::init(argc,argv,"car_position");
    ros::NodeHandle nh;
    ros::Publisher pub = nh.advertise<plumbing_pub_sub::ConeArray>("/car/cones",10);

    ros::Rate rate(2);

    //编写循环，循环中发布消息
    while(ros::ok)
    {
        plumbing_pub_sub::ConeArray msg;
        msg.header.stamp = ros::Time::now();
        msg.header.frame_id = "base_link";
        pub.publish(msg);
        rate.sleep();
        ros::spinOnce();
    }


    return 0;
}