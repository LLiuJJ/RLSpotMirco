# 原地右转
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
R = 3.5          # 减小半径，避免迈太大导致失衡
center_y = -12.0 # 略微抬高（比前进时高）
num_swing = 20
num_support = 20

# Y 抬高（尤其后腿）
y_lift_rear = +1.5

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
# 生成原地转向轨迹
# ========================
theta_swing = linspace(0, math.pi, num_swing)  # 注意：从 0 到 π

# ---------- 左前腿 (LF)：向后划 ----------
x_swing_LF = [-R * math.cos(t) for t in theta_swing]  # 负 X（向后）
y_swing_LF = [center_y + R * math.sin(t) for t in theta_swing]
x_support_LF = [0.0] * num_support  # 支撑相停在 x=0
y_support_LF = [min(y_swing_LF)] * num_support
x_LF = x_swing_LF + x_support_LF
y_LF = y_swing_LF + y_support_LF
hip_LF, knee_LF = compute_servo_angles(x_LF, y_LF)

# ---------- 右前腿 (RF)：向前划 ----------
x_swing_RF = [+R * math.cos(t) for t in theta_swing]  # 正 X（向前）
y_swing_RF = [center_y + R * math.sin(t) for t in theta_swing]
x_support_RF = [0.0] * num_support
y_support_RF = [min(y_swing_RF)] * num_support
x_RF = x_swing_RF + x_support_RF
y_RF = y_swing_RF + y_support_RF
hip_RF, knee_RF = compute_servo_angles(x_RF, y_RF)

# ---------- 左后腿 (LB)：向后划 + 抬高 ----------
x_swing_LB = [-R * math.cos(t) for t in theta_swing]
y_swing_LB = [center_y + y_lift_rear + R * math.sin(t) for t in theta_swing]
x_support_LB = [0.0] * num_support
y_support_LB = [min(y_swing_LB)] * num_support
x_LB = x_swing_LB + x_support_LB
y_LB = y_swing_LB + y_support_LB
hip_LB, knee_LB = compute_servo_angles(x_LB, y_LB)

# ---------- 右后腿 (RB)：向前划 + 抬高 ----------
x_swing_RB = [+R * math.cos(t) for t in theta_swing]
y_swing_RB = [center_y + y_lift_rear + R * math.sin(t) for t in theta_swing]
x_support_RB = [0.0] * num_support
y_support_RB = [min(y_swing_RB)] * num_support
x_RB = x_swing_RB + x_support_RB
y_RB = y_swing_RB + y_support_RB
hip_RB, knee_RB = compute_servo_angles(x_RB, y_RB)

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

# 中间舵机居中
for ch in [1, 4, 7, 10]:
    servo.Servo(pca.channels[ch]).angle = 90

print("✅ 原地左转轨迹生成完成。")

# ========================
# 初始站立（所有腿在 x=0 支撑）
# ========================
stand_idx = num_swing  # 支撑相起始索引（第20帧）

LF_UP.angle = hip_LF[stand_idx]
LF_DOWN.angle = 180 - knee_LF[stand_idx]

RF_UP.angle = 180 - hip_RF[stand_idx]
RF_DOWN.angle = knee_RF[stand_idx]

LB_UP.angle = hip_LB[stand_idx]
LB_DOWN.angle = 180 - knee_LB[stand_idx]

RB_UP.angle = 180 - hip_RB[stand_idx]
RB_DOWN.angle = knee_RB[stand_idx]

time.sleep(1.5)
print("🔄 开始原地左转...")

# ========================
# 原地左转步态循环
# ========================
steps = 6  # 每 step ≈ 30~45 度，6 steps ≈ 180~270 度
for step in range(steps):
    for i in range(len(hip_LF)):  # 总共 40 帧
        # Group A: LF + RB
        LF_UP.angle = hip_LF[i]
        LF_DOWN.angle = 180 - knee_LF[i]

        RB_UP.angle = 180 - hip_RB[i]   # 右侧镜像
        RB_DOWN.angle = knee_RB[i]

        # Group B: RF + LB（相位偏移 20 帧）
        j = (i + num_swing) % len(hip_LF)

        RF_UP.angle = 180 - hip_RF[j]
        RF_DOWN.angle = knee_RF[j]

        LB_UP.angle = hip_LB[j]
        LB_DOWN.angle = 180 - knee_LB[j]

        time.sleep(0.10)  # 慢速更稳

# ========================
# 回到站立姿势
# ========================
LF_UP.angle = hip_LF[stand_idx]
LF_DOWN.angle = 180 - knee_LF[stand_idx]

RF_UP.angle = 180 - hip_RF[stand_idx]
RF_DOWN.angle = knee_RF[stand_idx]

LB_UP.angle = hip_LB[stand_idx]
LB_DOWN.angle = 180 - knee_LB[stand_idx]

RB_UP.angle = 180 - hip_RB[stand_idx]
RB_DOWN.angle = knee_RB[stand_idx]

print("⏹️ 原地右转完成！")
