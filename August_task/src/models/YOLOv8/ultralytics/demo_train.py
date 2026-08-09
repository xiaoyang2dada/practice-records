from ultralytics import YOLO

model = YOLO("yolov8n.pt")

model.train(data="yolo-bvn.yaml", worker=0, epochs=50, batch=16)