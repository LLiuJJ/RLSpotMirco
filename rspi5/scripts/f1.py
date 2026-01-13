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


LF_UP = servo.Servo(pca.channels[0])
LF_MID = servo.Servo(pca.channels[1])
LF_DOWN = servo.Servo(pca.channels[2])

RF_UP = servo.Servo(pca.channels[3])
RF_MID = servo.Servo(pca.channels[4])
RF_DOWN = servo.Servo(pca.channels[5])

LB_UP = servo.Servo(pca.channels[6])
LB_MID = servo.Servo(pca.channels[7])
LB_DOWN = servo.Servo(pca.channels[8])

RB_UP = servo.Servo(pca.channels[9])
RB_MID = servo.Servo(pca.channels[10])
RB_DOWN = servo.Servo(pca.channels[11])


LF_UP.angle = 90
LF_MID.angle = 90
LF_DOWN.angle = 90

RF_UP.angle = 90
RF_MID.angle = 90
RF_DOWN.angle = 90

LB_UP.angle = 90
LB_MID.angle = 90
LB_DOWN.angle = 90

RB_UP.angle = 90
RB_MID.angle = 90
RB_DOWN.angle= 90


print("完成！")

time.sleep(1)

# ========== 右前腿（右手）招手 ==========
# 招手主要靠小腿（RF_MID）摆动，大腿（RF_UP）保持抬起姿态
wave_count = 3
for _ in range(wave_count):
    RF_DOWN.angle = 80  # 抬起“手”
    time.sleep(0.3)
    RF_DOWN.angle = 130   # 放下“手”
    time.sleep(0.3)

print("完成！")
