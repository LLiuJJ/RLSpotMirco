#!/usr/bin/env python3
# coding: utf-8
# 大白语音控制主程序 —— 根据语音ID执行不同动作脚本

import time
import threading
import subprocess
import serial
import sys

# 串口配置
ser = serial.Serial("/dev/ttyAMA0", 115200, timeout=0.1)

# 语音指令 ID 定义（与模块一致）
SitDown = 0x01
Up = 0x04
Down = 0x05
Left = 0x06
Right = 0x07
LoopUp = 0x16


# 脚本映射表：Read_ID -> 要执行的脚本路径
SCRIPT_MAP = {
    SitDown:           "/home/pi/scripts/center.py",
    Up:                "/home/pi/scripts/up.py",
    Down:              "/home/pi/scripts/down.py",
    Left:              "/home/pi/scripts/left.py",
    Right:             "/home/pi/scripts/right.py",
    LoopUp:            "/home/pi/scripts/f1.py"
}

# 防止重复触发（可选）
last_triggered_id = None

def run_script(script_path):
    """在子线程中运行指定的 Python 脚本"""
    try:
        print(f"▶️ 执行脚本: {script_path}")
        # 使用 python3 显式调用（确保兼容）
        result = subprocess.run([sys.executable, script_path], 
                                cwd="/home/pi/scripts", 
                                capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"⚠️ 脚本执行出错:\n{result.stderr}")
        else:
            print("✅ 脚本执行完成")
    except subprocess.TimeoutExpired:
        print("❌ 脚本执行超时（>30秒），已终止")
    except Exception as e:
        print(f"💥 启动脚本失败: {e}")

def speech_read():
    global last_triggered_id
    count = ser.inWaiting()
    if count >= 4:
        data = ser.read(count)
        hex_str = data.hex()
        # 查找以 'aa55' 开头的有效帧
        for i in range(0, len(hex_str) - 7, 2):
            if hex_str[i:i+4] == 'aa55':
                try:
                    byte1 = hex_str[i+4:i+6]   # 通常为 0x00
                    byte2 = hex_str[i+6:i+8]   # Read_ID
                    value1 = int(byte1, 16)
                    value2 = int(byte2, 16)

                    print(f"🔊 收到语音指令: Read_ID = 0x{value2:02X} ({value2})")

                    # 防止重复触发（取消下一行注释即可启用）
                    # if value2 == last_triggered_id:
                    #     return

                    if value2 in SCRIPT_MAP:
                        script_path = SCRIPT_MAP[value2]
                        # 在新线程中运行，不阻塞主循环
                        thread = threading.Thread(target=run_script, args=(script_path,))
                        thread.daemon = True  # 主程序退出时自动结束
                        thread.start()
                        last_triggered_id = value2
                    else:
                        print(f"❓ 未知指令 ID: {value2}")

                    # 清空缓冲区（可选）
                    ser.flushInput()
                    break  # 只处理一帧
                except Exception as e:
                    print(f"解析错误: {e}")
                break

if ser.isOpen():
    print("🎤 语音串口已打开 (115200 baud)")
else:
    print("❌ 语音串口打开失败！")
    exit(1)

print("⏳ 等待语音指令...")

try:
    while True:
        speech_read()
        time.sleep(0.05)  # 避免 CPU 占用过高
except KeyboardInterrupt:
    print("\n🛑 程序被用户终止")
finally:
    ser.close()
