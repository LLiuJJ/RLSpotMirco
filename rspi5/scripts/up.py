# 大白稳定前进版本

import time
from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo
import math

# ========================
# 机械参数（单位：cm）
# ========================
L1 = 12.0  # 大腿长度
L2 = 12.0  # 小腿长度
R = 4.0    # 摆动相半圆半径
center_y = -14.0  # 轨迹圆心 Y 坐标（相对于髋关节）

num_swing = 20   # 摆动相点数
num_support = 20 # 支撑相点数

# 前腿 X 偏移（负值 = 向后）
x_offset_front = -1.0

# 后腿额外偏移（更靠后 + 抬高）
x_offset_rear = x_offset_front - 6.0  # 再向后 4cm
y_offset_rear = +3.0                  # 抬高 1.5cm（Y 更接近 0）

# ========================
# 工具函数
# ========================
def linspace(start, end, num):
    if num <= 1:
        return [start]
    step = (end - start) / (num - 1)
    return [start + i * step for i in range(num)]

def compute_servo_angles(x_list, y_list, L1=12.0, L2=12.0):
    hip_list = []
    knee_list = []
    for x, y in zip(x_list, y_list):
        # 逆运动学
        D = (x**2 + y**2 - L1**2 - L2**2) / (2 * L1 * L2)
        D = max(min(D, 1.0), -1.0)
        theta2 = math.pi - math.acos(D)

        k1 = L1 + L2 * math.cos(math.pi - theta2)
        k2 = L2 * math.sin(math.pi - theta2)
        theta1 = math.atan2(y, x) - math.atan2(k2, k1)

        # 转舵机角度（0~180）
        hip_deg = int(round(math.degrees(theta1))) + 180
        knee_deg = int(round(math.degrees(theta2)))

        hip_servo = max(0, min(180, hip_deg))
        knee_servo = max(0, min(180, knee_deg))

        hip_list.append(hip_servo)
        knee_list.append(knee_servo)
    return hip_list, knee_list

# ========================
# 生成前腿轨迹
# ========================
theta_swing = linspace(math.pi, 0, num_swing)
x_swing_front = [R * math.cos(t) + x_offset_front for t in theta_swing]
y_swing_front = [center_y + R * math.sin(t) for t in theta_swing]

x_support_front = linspace(x_swing_front[-1], x_swing_front[0], num_support)
y_support_front = [min(y_swing_front)] * num_support

x_front_full = x_swing_front + x_support_front
y_front_full = y_swing_front + y_support_front

hip_front, knee_front = compute_servo_angles(x_front_full, y_front_full)

# ========================
# 生成后腿轨迹（偏后 + 抬高）
# ========================
x_swing_rear = [R * math.cos(t) + x_offset_rear for t in theta_swing]
y_swing_rear = [center_y + y_offset_rear + R * math.sin(t) for t in theta_swing]

x_support_rear = linspace(x_swing_rear[-1], x_swing_rear[0], num_support)
y_support_rear = [min(y_swing_rear)] * num_support

x_rear_full = x_swing_rear + x_support_rear
y_rear_full = y_swing_rear + y_support_rear

hip_rear, knee_rear = compute_servo_angles(x_rear_full, y_rear_full)

# ========================
# 初始化 PCA9685 和舵机
# ========================
i2c = busio.I2C(SCL, SDA)
pca = PCA9685(i2c)
pca.frequency = 50  # 标准舵机频率

# 定义舵机（UP = 髋, DOWN = 膝）
LF_UP = servo.Servo(pca.channels[0])
LF_DOWN = servo.Servo(pca.channels[2])

RF_UP = servo.Servo(pca.channels[3])
RF_DOWN = servo.Servo(pca.channels[5])

LB_UP = servo.Servo(pca.channels[6])
LB_DOWN = servo.Servo(pca.channels[8])

RB_UP = servo.Servo(pca.channels[9])
RB_DOWN = servo.Servo(pca.channels[11])

# 中间舵机（如果不用可注释）
for ch in [1, 4, 7, 10]:
    mid = servo.Servo(pca.channels[ch])
    mid.angle = 90

print("✅ 轨迹生成完成。")
print(f"前腿轨迹长度: {len(hip_front)}")
print(f"后腿轨迹长度: {len(hip_rear)}")

# ========================
# 初始站立姿势（支撑相中点）
# ========================
stand_idx = 20  # 支撑相起始点（第20帧）

LF_UP.angle = hip_front[stand_idx]
LF_DOWN.angle = 180 - knee_front[stand_idx]

RF_UP.angle = 180 - hip_front[stand_idx]
RF_DOWN.angle = knee_front[stand_idx]

LB_UP.angle = hip_rear[stand_idx]
LB_DOWN.angle = 180 - knee_rear[stand_idx]

RB_UP.angle = 180 - hip_rear[stand_idx]
RB_DOWN.angle = knee_rear[stand_idx]

time.sleep(1.5)
print("🚶 开始 Walk 步态（慢速前进）...")

# ========================
# Walk 步态主循环
# ========================
steps = 6  # 执行 6 个完整步态周期（每个周期 40 帧）
for step in range(steps):
    for i in range(40):
        # Group A: LF（左前） + RB（右后）
        LF_UP.angle = hip_front[i]
        LF_DOWN.angle = 180 - knee_front[i]

        RB_UP.angle = 180 - hip_rear[i]   # 右侧镜像
        RB_DOWN.angle = knee_rear[i]

        # Group B: RF（右前） + LB（左后）—— 相位偏移 20 帧
        j = (i + 20) % 40

        RF_UP.angle = 180 - hip_front[j]
        RF_DOWN.angle = knee_front[j]

        LB_UP.angle = hip_rear[j]
        LB_DOWN.angle = 180 - knee_rear[j]

        # 慢速控制（可调：0.06 ~ 0.12）
        time.sleep(0.09)

# ========================
# 停止：回到站立姿势
# ========================
LF_UP.angle = hip_front[stand_idx]
LF_DOWN.angle = 180 - knee_front[stand_idx]

RF_UP.angle = 180 - hip_front[stand_idx]
RF_DOWN.angle = knee_front[stand_idx]

LB_UP.angle = hip_rear[stand_idx]
LB_DOWN.angle = 180 - knee_rear[stand_idx]

RB_UP.angle = 180 - hip_rear[stand_idx]
RB_DOWN.angle = knee_rear[stand_idx]

print("⏹️ Walk 步态完成，已回到站立姿势。")
