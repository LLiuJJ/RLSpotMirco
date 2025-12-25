import math


# 参数（与 MATLAB 和之前的示例一致）
L1 = 12.0  # 大腿长度 (cm)
L2 = 12.0  # 小腿长度 (cm)
R = 6.0    # 半圆半径 (cm)
center_y = -15.0  # 相对于髋关节(0,0)的Y坐标
num_swing = 20   # 摆动相点数
num_support = 20 # 支撑相点数

# 新增：X 方向整体偏移（负值表示向后）
x_offset = 4.0  # 相对于髋关节(0,0)的X坐标偏移

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
