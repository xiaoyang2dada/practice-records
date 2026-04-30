# Cone Visualization ROS Workspace
- 本工作空间用于回放 `rosbag` 数据包，订阅解析 `/test/camera_cones` 锥桶话题，完成相机坐标系到车体坐标系转换，并在 `rviz` 中可视化展示。

## 📡 话题与节点说明

- rosbag 原始数据源话题：`/test/camera_cones`
- 数据解析订阅节点：`/demo01_sub`
- 中转发布话题：`/car/cones`
- rviz 可视化订阅节点：`/visualization_rviz`
- rviz 可视化发布话题：`/visual/cones`
 
## 🚀 运行步骤
- 1.进入工作空间(`fifth_week_cone_visualization_ws`文件夹)，然后在工作空间主目录下打开终端
- 2. 在终端内编译并刷新环境
 ```
catkin_make
source devel/setup.bash
 ```
- 3. 一键启动所有节点
 ```
roslaunch plumbing_pub_sub task.launch 
 ```

## 🖥️ 预期结果 
![result_visualization](./screenshot/cones_viusalization_done.png)
