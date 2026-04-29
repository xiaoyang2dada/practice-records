# Cone Visualization ROS Workspace
- 本工作空间用于回放 `rosbag` 数据包，订阅解析 `/test/camera_cones` 锥桶话题，完成相机坐标系到车体坐标系转换，并在 `rviz` 中可视化展示。

## 📡 话题与节点说明
- rosbag 原始数据源话题：`/test/camera_cones`
- 数据解析订阅节点：`/demo01_sub`
- 中转发布话题：`/car/cones`
- rviz 可视化订阅节点：`/visualization_rviz`
- rviz 可视化发布话题：`/visual/cones`
 
## 🚀 运行步骤
 
1. 进入工作空间，刷新环境
 ```
source devel/setup.bash
 ```
2. 一键启动所有节点
 ```
roslaunch plumbing_pub_sub task.launch 
 ```
