import time
from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo
import math


# 参数（与 MATLAB 和之前的示例一致）
L1 = 12.0  # 大腿长度 (cm)
L2 = 12.0  # 小腿长度 (cm)
R = 4.0    # 半圆半径 (cm)
center_y = -15  # 相对于髋关节(0,0)的Y坐标
num_swing = 20   # 摆动相点数
num_support = 20 # 支撑相点数

# 新增：X 方向整体偏移（负值表示向后）
x_offset = -1.0  # 相对于髋关节(0,0)的X坐标偏移

# 1. 生成轨迹
def linspace(start, end, num):
    step = (end - start) / (num - 1)
    return [start + i * step for i in range(num)]

theta_swing = linspace(math.pi, 0, num_swing)
x_swing = [R * math.cos(theta) for theta in theta_swing]
y_swing = [center_y + R * math.sin(theta) for theta in theta_swing]

x_support = linspace(x_swing[-1], x_swing[0], num_support)
y_support = [min(y_swing)] * num_support

# 合并原始轨迹
x_full_raw = x_swing + x_support
y_full = y_swing + y_support

# 应用 X 偏移：整体向后移动 3 cm
x_full = [x + x_offset for x in x_full_raw]  # x_offset = -3.0

# 2. 逆运动学计算角度（弧度 → 度）
hip_angles = []
knee_angles = []

for x, y in zip(x_full, y_full):
    D = (x**2 + y**2 - L1**2 - L2**2) / (2 * L1 * L2)
    D = max(min(D, 1), -1)
    theta2 = math.pi - math.acos(D)

    k1 = L1 + L2 * math.cos(math.pi - theta2)
    k2 = L2 * math.sin(math.pi - theta2)
    theta1 = math.atan2(y, x) - math.atan2(k2, k1)

    # 注意：偏移后 x 可能为负且绝对值较大，需确保 atan2 和舵机映射合理
    hip_deg = int(round(math.degrees(theta1))) + 180   # 建议使用 +90 而非 +180（见说明）
    knee_deg = int(round(math.degrees(theta2)))

    hip_servo = max(0, min(180, hip_deg))
    knee_servo = max(0, min(180, knee_deg))

    hip_angles.append(hip_servo)
    knee_angles.append(knee_servo)

# 3. 输出C数组
print("PROGMEM const uint8_t hipAngles[{}] = {{".format(len(hip_angles)))
print(", ".join(map(str, hip_angles)))
print("};\n")

print("PROGMEM const uint8_t kneeAngles[{}] = {{".format(len(knee_angles)))
print(", ".join(map(str, knee_angles)))
print("};")

# 初始化 I2C 总线
i2c = busio.I2C(SCL, SDA)

# 创建 PCA9685 实例（默认地址 0x40）
pca = PCA9685(i2c)
pca.frequency = 50  # 舵机标准频率：50Hz

hipAnglesSmall = [39, 37, 35, 33, 32, 32, 32, 33, 34, 36, 38, 41, 44, 47, 49, 52, 55, 57, 59, 61, 61, 59, 58, 57, 55, 54, 53, 52, 50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 40, 39]
kneeAnglesSmall = [100, 95, 91, 88, 84, 81, 79, 77, 75, 74, 74, 75, 77, 79, 81, 84, 88, 91, 95, 100, 100, 99, 99, 98, 98, 98, 98, 97, 97, 97, 97, 97, 97, 98, 98, 98, 98, 99, 99, 100]

# hipAngles = [31, 28, 26, 25, 24, 26, 29, 33, 39, 45, 51, 57, 63, 67, 71, 74, 77, 79, 81, 82, 82, 79, 77, 74, 71, 68, 65, 62, 59, 57, 54, 51, 48, 46, 43, 41, 38, 36, 34, 31]
# kneeAngles = [78, 72, 66, 61, 56, 52, 49, 47, 47, 48, 50, 53, 57, 62, 67, 73, 79, 85, 91, 97, 97, 95, 93, 91, 89, 87, 85, 84, 82, 81, 80, 79, 79, 78, 78, 77, 77, 77, 78, 78]

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

# LF
for i in range(20):
    h = hip_angles[i]
    k = knee_angles[i]

    LF_UP.angle = h
    LF_DOWN.angle = 180 - k

    time.sleep(0.02)

time.sleep(1)

#  RF
for i in range(20):
    h = hip_angles[i]
    k = knee_angles[i]

    RF_UP.angle = 180 - h
    RF_DOWN.angle = k
    time.sleep(0.02)

# LF_UP.angle = 64, LF_DOWN.angle = 95, RF_UP.angle = 116, RF_DOWN.angle = 85
# ' LF_UP.angle = 21, LF_DOWN.angle = 95, RF_UP.angle = 159, RF_DOWN.angle = 85


LF_UP.angle = hip_angles[0]
RF_UP.angle = 180 - hip_angles[0]


time.sleep(1)

# RB
for i in range(10):
    h = hip_angles[i]
    k = knee_angles[i]

    RB_UP.angle = 180 - h
    RB_DOWN.angle = k
    time.sleep(0.01)

time.sleep(1)

# LB
for i in range(20):
    h = hip_angles[i]
    k = knee_angles[i]

    LB_UP.angle = h
    LB_DOWN.angle = 180 - k

    time.sleep(0.01)

# RB_UP.angle = 116, RB_DOWN.angle = 85, LB_UP.angle = 64, LB_DOWN.angle = 95
# ' RB_UP.angle = 159, RB_DOWN.angle = 85, LB_UP.angle = 21, LB_DOWN.angle = 95

# for i in range(int(RB_UP.angle), 180 - hipAngles[0]):
#     RB_UP.angle = i
#     time.sleep(0.05)

# for i in range(int(LB_UP.angle), hipAngles[0], -1):
#     LB_UP.angle = i
#     time.sleep(0.05)


RB_UP.angle = 180 - hip_angles[0]
LB_UP.angle = hip_angles[0]

time.sleep(1)

print("完成！")