# 大白真正后退版本 —— 修复原地踏步问题

import time
from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo
import math

# ========================
# 机械参数
# ========================
L1 = 12.0
L2 = 12.0
R = 3.5                # 稍微减小，避免过大步幅失衡
center_y = -14.0
num_swing = 20
num_support = 20

# 后退时：所有腿的基准位置略靠前，以便向后迈
base_offset = +0.5     # 整体前移，留出向后空间
x_offset_front = base_offset
x_offset_rear = base_offset - 5.0  # 后腿更靠后
y_offset_rear = +2.5   # 抬高防拖地

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
        D = (x**2 + y**2 - L1**2 - L2**2) / (2 * L1 * L2)
        D = max(min(D, 1.0), -1.0)
        theta2 = math.pi - math.acos(D)

        k1 = L1 + L2 * math.cos(math.pi - theta2)
        k2 = L2 * math.sin(math.pi - theta2)
        theta1 = math.atan2(y, x) - math.atan2(k2, k1)

        hip_deg = int(round(math.degrees(theta1))) + 180
        knee_deg = int(round(math.degrees(theta2)))

        hip_servo = max(0, min(180, hip_deg))
        knee_servo = max(0, min(180, knee_deg))

        hip_list.append(hip_servo)
        knee_list.append(knee_servo)
    return hip_list, knee_list

# ========================
# 关键：使用统一的后退轨迹生成方式
# 摆动相：向后迈（X 减小）
# 支撑相：从后往前扫（X 增大）→ 推动身体后移
# ========================

theta_swing = linspace(math.pi, 0, num_swing)  # 保持与前进一致的方向

# ---------- 前腿：向后迈 ----------
x_swing_front = [ -R * math.cos(t) + x_offset_front for t in theta_swing ]
y_swing_front = [ center_y + R * math.sin(t) for t in theta_swing ]

# 支撑相：从最靠后点 → 最靠前点（即：腿向前推，身体后移）
x_support_front = linspace(x_swing_front[-1], x_swing_front[0], num_support)
y_support_front = [min(y_swing_front)] * num_support

x_front = x_swing_front + x_support_front
y_front = y_swing_front + y_support_front
hip_front, knee_front = compute_servo_angles(x_front, y_front)

# ---------- 后腿：也向后迈（但起点更靠后）----------
x_swing_rear = [ -R * math.cos(t) + x_offset_rear for t in theta_swing ]
y_swing_rear = [ center_y + y_offset_rear + R * math.sin(t) for t in theta_swing ]

x_support_rear = linspace(x_swing_rear[-1], x_swing_rear[0], num_support)
y_support_rear = [min(y_swing_rear)] * num_support

x_rear = x_swing_rear + x_support_rear
y_rear = y_swing_rear + y_support_rear
hip_rear, knee_rear = compute_servo_angles(x_rear, y_rear)

# ========================
# 初始化舵机
# ========================
i2c = busio.I2C(SCL, SDA)
pca = PCA9685(i2c)
pca.frequency = 50

LF_UP = servo.Servo(pca.channels[0])
LF_DOWN = servo.Servo(pca.channels[2])

RF_UP = servo.Servo(pca.channels[3])
RF_DOWN = servo.Servo(pca.channels[5])

LB_UP = servo.Servo(pca.channels[6])
LB_DOWN = servo.Servo(pca.channels[8])

RB_UP = servo.Servo(pca.channels[9])
RB_DOWN = servo.Servo(pca.channels[11])

for ch in [1, 4, 7, 10]:
    servo.Servo(pca.channels[ch]).angle = 90

print("✅ 真正后退轨迹生成完成。")

# ========================
# 初始站立（第20帧：支撑相开始）
# ========================
stand_idx = 20

LF_UP.angle = hip_front[stand_idx]
LF_DOWN.angle = 180 - knee_front[stand_idx]

RF_UP.angle = 180 - hip_front[stand_idx]
RF_DOWN.angle = knee_front[stand_idx]

LB_UP.angle = hip_rear[stand_idx]
LB_DOWN.angle = 180 - knee_rear[stand_idx]

RB_UP.angle = 180 - hip_rear[stand_idx]
RB_DOWN.angle = knee_rear[stand_idx]

time.sleep(1.5)
print("🚶 开始真正后退步态...")

# ========================
# 后退步态循环
# ========================
steps = 6
for step in range(steps):
    for i in range(40):
        # Group A: LF + RB
        LF_UP.angle = hip_front[i]
        LF_DOWN.angle = 180 - knee_front[i]

        RB_UP.angle = 180 - hip_rear[i]
        RB_DOWN.angle = knee_rear[i]

        # Group B: RF + LB（相位偏移20）
        j = (i + 20) % 40

        RF_UP.angle = 180 - hip_front[j]
        RF_DOWN.angle = knee_front[j]

        LB_UP.angle = hip_rear[j]
        LB_DOWN.angle = 180 - knee_rear[j]

        time.sleep(0.10)  # 稍慢更稳

# ========================
# 回到站立
# ========================
LF_UP.angle = hip_front[stand_idx]
LF_DOWN.angle = 180 - knee_front[stand_idx]

RF_UP.angle = 180 - hip_front[stand_idx]
RF_DOWN.angle = knee_front[stand_idx]

LB_UP.angle = hip_rear[stand_idx]
LB_DOWN.angle = 180 - knee_rear[stand_idx]

RB_UP.angle = 180 - hip_rear[stand_idx]
RB_DOWN.angle = knee_rear[stand_idx]

print("⏹️ 真正后退完成！")