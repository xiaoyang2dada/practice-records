# Cone Visualization ROS Workspace
<br>

- 本工作空间用于回放 `rosbag` 数据包，订阅解析 `/test/camera_cones` 锥桶话题。
- 将 相机坐标系 下的锥桶数据（100像素/米）进行坐标转换：
    - 轴对齐粗变换
    - 车体Z轴左偏30°旋转变换
    - 叠加安装偏移（后 0.3m/左 0.1m/上 0.95m）
- 最终在 `rviz` 中可视化展示。
<br>

## 📡 话题与节点说明
<br>

- rosbag 原始数据源话题：`/test/camera_cones`
- 数据解析订阅节点：`/demo01_sub`
- 中转发布话题：`/car/cones`
- rviz 可视化订阅节点：`/visualization_rviz`
- rviz 可视化发布话题：`/visual/cones`
<br>

## 🚀 运行步骤
<br>

- 1.进入工作空间(`fifth_week_cone_visualization_ws`文件夹)，然后在工作空间主目录下打开终端
- 2. 在终端内编译并刷新环境
```bash
catkin_make
source devel/setup.bash
 ```
- 3. 一键启动所有节点
 ```bash
roslaunch plumbing_pub_sub task.launch 
 ```
<br>

## 🖥️ 预期结果
<br>

- 运行成功后，rviz将可视化锥桶，效果如下：
![result_visualization](./screenshot/cones_viusalization_done.png)
