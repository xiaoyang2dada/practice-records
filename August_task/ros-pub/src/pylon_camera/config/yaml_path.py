import yaml

# 读取YAML文件
with open('/home/petr0/a_24_ws/biaoding/20240519_0102_autoware_camera_calibration.yaml', 'r') as file:
    try:
        # 尝试解析YAML文件
        data = yaml.safe_load(file)
        print("YAML文件解析成功！")
        print(data)  # 打印解析后的数据
    except yaml.YAMLError as exc:
        print("YAML文件解析错误：", exc)
