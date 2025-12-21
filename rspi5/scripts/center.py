# servo_12_to_90.py
import time
from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo

# 初始化 I2C 总线
i2c = busio.I2C(SCL, SDA)

# 创建 PCA9685 实例（默认地址 0x40）
pca = PCA9685(i2c)
pca.frequency = 50  # 舵机标准频率：50Hz

# 创建 12 个舵机对象（连接到通道 0~11）
servos = []
for channel in range(12):
    servos.append(servo.Servo(pca.channels[channel]))

# 设置所有舵机到 90 度
print("正在将 12 路舵机转动到 90 度...")
for i, s in enumerate(servos):
    s.angle = 90
    print(f"通道 {i}: 90°")
    time.sleep(0.05)  # 微小延迟，避免电流突变

print("完成！")

# 可选：保持 5 秒后释放（设为 None 可断开 PWM）
# time.sleep(5)
# for s in servos:
#     s.angle = None  # 停止输出 PWM
