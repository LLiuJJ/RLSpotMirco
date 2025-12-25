from ultralytics import YOLO
from picamera2 import Picamera2
import time
import serial

# ----------------------------
# 配置串口（语音模块）
# ----------------------------
try:
    ser = serial.Serial("/dev/ttyAMA0", 115200, timeout=1)
    print("Speech Serial Opened! Baudrate=115200")
except Exception as e:
    print(f"Speech Serial Open Failed: {e}")
    ser = None

# 语音播报指令定义（按你的协议）
CMD_INIT = 0x67
CMD_ORANGE_DETECTED = 0x0C  # 你提到的 0x0C

def send_voice_cmd(cmd_byte):
    """发送语音播报指令"""
    if ser is None or not ser.is_open:
        print("Serial not available, skip sending command.")
        return
    # 构造帧：[0xAA, 0x55, 0x00, CMD, 0xFB]
    cmd = bytearray([0xAA, 0x55, 0x00, cmd_byte & 0xFF, 0xFB])
    ser.write(cmd)
    ser.flush()
    time.sleep(0.01)  # 短暂延时确保发送完成

# ----------------------------
# 加载 YOLO 模型
# ----------------------------
print("Loading YOLO model...")
model = YOLO("/home/pi/ultralytics/ultralytics/yolo11n.pt")  # 可替换为 .onnx 或 ncnn

# ----------------------------
# 初始化并拍照
# ----------------------------
print("Initializing camera...")
picam2 = Picamera2()
config = picam2.create_still_configuration(main={"size": (1920, 1080)})
picam2.configure(config)
picam2.start()
time.sleep(2)  # 等待自动曝光/对焦

print("Capturing image...")
image_path = "/home/pi/current.jpg"
picam2.capture_file(image_path)
picam2.stop()
print(f"Image saved to {image_path}")

# ----------------------------
# 运行推理
# ----------------------------
print("Running inference...")
results = model(image_path)

# ----------------------------
# 解析结果：检查是否包含 'orange'
# ----------------------------
orange_detected = False
for result in results:
    if result.boxes is not None and len(result.boxes) > 0:
        # 获取所有检测到的类别名称
        class_names = result.names  # dict: {0: 'person', 1: 'bicycle', ...}
        cls_indices = result.boxes.cls.cpu().numpy().astype(int)  # 类别索引数组

        for cls_idx in cls_indices:
            class_name = class_names[cls_idx]
            print(f"Detected: {class_name}")
            if class_name == "orange":
                orange_detected = True
                break
        if orange_detected:
            break

# ----------------------------
# 触发语音播报
# ----------------------------
if orange_detected:
    print("🍊 Orange detected! Sending voice command...")
    send_voice_cmd(CMD_ORANGE_DETECTED)
else:
    print("No orange detected.")

# 可选：发送初始化指令（根据你的需求）
# send_voice_cmd(CMD_INIT)

# 关闭串口（可选）
if ser and ser.is_open:
    ser.close()
