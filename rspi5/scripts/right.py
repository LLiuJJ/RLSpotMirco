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

hipAnglesSmall = [39, 37, 35, 33, 32, 32, 32, 33, 34, 36, 38, 41, 44, 47, 49, 52, 55, 57, 59, 61, 61, 59, 58, 57, 55, 54, 53, 52, 50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 40, 39]
kneeAnglesSmall = [100, 95, 91, 88, 84, 81, 79, 77, 75, 74, 74, 75, 77, 79, 81, 84, 88, 91, 95, 100, 100, 99, 99, 98, 98, 98, 98, 97, 97, 97, 97, 97, 97, 98, 98, 98, 98, 99, 99, 100]

hipAngles = [21, 19, 18, 17, 16, 17, 17, 19, 21, 23, 26, 29, 32, 35, 38, 40, 42, 44, 46, 47, 47, 45, 44, 42, 41, 39, 38, 36, 35, 33, 32, 31, 29, 28, 27, 26, 24, 23, 22, 21]
kneeAngles = [68, 65, 62, 59, 57, 54, 53, 51, 50, 49, 49, 50, 51, 53, 54, 57, 59, 62, 65, 68, 68, 67, 67, 67, 66, 66, 66, 66, 66, 66, 66, 66, 66, 66, 66, 66, 67, 67, 67, 68]

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

LF_MID.angle = 90
RF_MID.angle = 90

LB_MID.angle = 90
RB_MID.angle = 90

time.sleep(1)

kc = 0
for i in range(20, 40):
    h = hipAngles[i]
    k = kneeAngles[i]

    hr = hipAngles[39 - kc]
    kr = kneeAngles[39 - kc]

    LF_UP.angle = h
    LF_DOWN.angle = 180 - k

    RB_UP.angle = 180 - hr
    RB_DOWN.angle = kr

    kc = kc + 1
    time.sleep(0.02)

time.sleep(0.02)

kc = 0

for i in range(20, 40):
    h = hipAngles[i]
    k = kneeAngles[i]

    hr = hipAngles[39 - kc]
    kr = kneeAngles[39 - kc]

    LB_UP.angle = h
    LB_DOWN.angle = 180 - k

    RF_UP.angle = 180 - hr
    RF_DOWN.angle = kr

    kc = kc + 1
    time.sleep(0.02)

time.sleep(0.02)

print("完成！")
