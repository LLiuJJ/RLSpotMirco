import math

# 参数（与 MATLAB 和之前的示例一致）
L1 = 12.0  # 大腿长度 (cm)
L2 = 12.0  # 小腿长度 (cm)
R = 3.5    # 半圆半径 (cm)
center_y = -18.0  # 相对于髋关节(0,0)的Y坐标
num_swing = 20   # 摆动相点数
num_support = 20 # 支撑相点数

def linspace(start, end, num):
    if num == 1:
        return [start]
    step = (end - start) / (num - 1)
    return [start + i * step for i in range(num)]

# ========== 倒退步态：摆动相（前 → 后）==========
theta_swing = linspace(0, math.pi, num_swing)          # 0: 前方, π: 后方
x_swing = [R * math.cos(theta) for theta in theta_swing]  # cos(0)=1 → cos(π)=-1 ⇒ x: +R → -R
y_swing = [center_y + R * math.sin(theta) for theta in theta_swing]

# ========== 支撑相（后 → 前，脚拖地）==========
x_support = linspace(x_swing[-1], x_swing[0], num_support)  # 从 -R → +R
y_support = [min(y_swing)] * num_support  # 保持最低高度

# 合并完整周期：先摆动，再支撑
x_full = x_swing + x_support
y_full = y_swing + y_support

# ========== 逆运动学计算 ==========
hip_angles = []
knee_angles = []

for x, y in zip(x_full, y_full):
    # 计算膝关节角 theta2（内角）
    D = (x**2 + y**2 - L1**2 - L2**2) / (2 * L1 * L2)
    D = max(min(D, 1.0), -1.0)
    theta2 = math.pi - math.acos(D)

    # 计算髋关节角 theta1
    k1 = L1 + L2 * math.cos(math.pi - theta2)
    k2 = L2 * math.sin(math.pi - theta2)
    theta1 = math.atan2(y, x) - math.atan2(k2, k1)

    # 转换为舵机角度（0~180）
    hip_deg = int(round(math.degrees(theta1))) + 180   # ⚠️ 关键：这里应为 +90，不是 +180！
    knee_deg = int(round(math.degrees(theta2)))

    # 限制舵机范围
    hip_servo = max(0, min(180, hip_deg))
    knee_servo = max(0, min(180, knee_deg))

    hip_angles.append(hip_servo)
    knee_angles.append(knee_servo)

# ========== 输出 C 数组 ==========
print("PROGMEM const uint8_t hipAngles[{}] = {{".format(len(hip_angles)))
print(", ".join(map(str, hip_angles)))
print("};\n")

print("PROGMEM const uint8_t kneeAngles[{}] = {{".format(len(knee_angles)))
print(", ".join(map(str, knee_angles)))
print("};")
