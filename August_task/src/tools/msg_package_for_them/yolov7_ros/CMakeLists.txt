cmake_minimum_required(VERSION 3.0.2)
project(yolov7_ros)

# 消息依赖
find_package(catkin REQUIRED COMPONENTS
  message_generation
  std_msgs
  geometry_msgs
)

# 声明 ROS 自定义消息
add_message_files(
  FILES
  ConeArray.msg   # 锥桶数组消息
  ConeInfo.msg    # 单个锥桶信息（ID、位置、颜色、置信度）
)

# 生成消息
generate_messages(
  DEPENDENCIES
  geometry_msgs
  std_msgs
)

catkin_package(
  CATKIN_DEPENDS message_runtime std_msgs geometry_msgs
)
