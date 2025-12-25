#!/usr/bin/python3

import io
import logging
import socketserver
from http import server
from threading import Condition, Thread, Event
import subprocess
import os
import time
import serial
import queue
import numpy as np
from PIL import Image
from picamera2 import Picamera2

# --- 日志配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ----------------------------
# 全局：YOLO 和串口初始化
# ----------------------------
model = None
try:
    from ultralytics import YOLO
    model = YOLO("yolov8n.pt")
    print("✅ YOLO model loaded.")
except Exception as e:
    logging.error(f"❌ Failed to load YOLO model: {e}")

ser = None
try:
    ser = serial.Serial("/dev/ttyAMA0", 115200, timeout=1)
    print("✅ Speech Serial Opened! Baudrate=115200")
except Exception as e:
    print(f"⚠️ Speech Serial Open Failed: {e}")

CMD_ORANGE_DETECTED = 0x0C

def send_voice_cmd(cmd_byte):
    if ser is None or not ser.is_open:
        return
    cmd = bytearray([0xAA, 0x55, 0x00, cmd_byte & 0xFF, 0xFB])
    ser.write(cmd)
    ser.flush()
    time.sleep(0.01)


# === 脚本映射 ===
SCRIPTS = {
    'up': '/home/pi/scripts/up.py',
    'down': '/home/pi/scripts/down.py',
    'left': '/home/pi/scripts/left.py',
    'right': '/home/pi/scripts/right.py',
    'center': '/home/pi/scripts/center.py',
    'f1': '/home/pi/scripts/f1.py',
    'f2': None,
    'f3': '/home/pi/scripts/f3.py',
    'f4': '/home/pi/scripts/f4.py',
    'f5': '/home/pi/scripts/f5.py',
    'f6': '/home/pi/scripts/f6.py',
    'f7': '/home/pi/scripts/f7.py',
    'f8': '/home/pi/scripts/f8.py',
    'f9': '/home/pi/scripts/f9.py',
    'f10': '/home/pi/scripts/f10.py',
}

for name, path in SCRIPTS.items():
    if path and not os.path.isfile(path):
        logging.warning(f"Script for '{name}' not found: {path}")


def get_cpu_temperature():
    try:
        result = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True, text=True, timeout=2)
        temp_str = result.stdout.strip()
        return float(temp_str.replace("temp=", "").replace("'C", ""))
    except Exception as e1:
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                return int(f.read().strip()) / 1000.0
        except Exception as e2:
            logging.error(f"Failed to read CPU temperature: vcgencmd={e1}, sysfs={e2}")
            return None


# ========================
# 输出缓冲区（线程安全）
# ========================
class StreamingOutput:
    def __init__(self):
        self.annotated_frame = None
        self.raw_frame = None
        self.condition = Condition()

    def update_frames(self, raw_frame, annotated_frame):
        with self.condition:
            self.raw_frame = raw_frame
            self.annotated_frame = annotated_frame
            self.condition.notify_all()


# ========================
# YOLO 推理线程
# ========================
def yolo_inference_thread(raw_queue, output_obj, model, stop_event):
    while not stop_event.is_set():
        raw_frame = None
        try:
            while not raw_queue.empty():
                raw_frame = raw_queue.get_nowait()
        except queue.Empty:
            pass

        if raw_frame is None:
            time.sleep(0.01)
            continue

        try:
            # raw_frame 是 bytes (JPEG)
            image = Image.open(io.BytesIO(raw_frame)).convert('RGB')
            img_array = np.array(image)
            results = model(img_array, verbose=False, imgsz=640)
            annotated_bgr = results[0].plot()
            annotated_rgb = annotated_bgr[:, :, ::-1]
            pil_img = Image.fromarray(annotated_rgb)
            with io.BytesIO() as buf:
                pil_img.save(buf, format="JPEG", quality=70)
                annotated_jpeg = buf.getvalue()
        except Exception as e:
            logging.error(f"YOLO inference error: {e}")
            annotated_jpeg = raw_frame

        output_obj.update_frames(raw_frame, annotated_jpeg)


# ========================
# 摄像头采集线程（替代 FileOutput）
# ========================
def camera_capture_thread(picam2, raw_queue, stop_event):
    """持续捕获摄像头帧并编码为 JPEG，送入队列"""
    while not stop_event.is_set():
        try:
            frame_array = picam2.capture_array("main")

            # 确保数据类型正确
            if frame_array.dtype != np.uint8:
                frame_array = frame_array.astype(np.uint8)

            # 处理通道数：RGBA → RGB
            if frame_array.ndim == 3 and frame_array.shape[2] == 4:
                # RGBA
                pil_img = Image.fromarray(frame_array, mode='RGBA').convert('RGB')
            elif frame_array.ndim == 3 and frame_array.shape[2] == 3:
                # RGB
                pil_img = Image.fromarray(frame_array, mode='RGB')
            else:
                # 灰度图等（理论上不会出现）
                pil_img = Image.fromarray(frame_array).convert('RGB')

            with io.BytesIO() as buf:
                pil_img.save(buf, format="JPEG", quality=70)
                jpeg_bytes = buf.getvalue()

            # 入队（只保留最新帧）
            try:
                while not raw_queue.empty():
                    raw_queue.get_nowait()
                raw_queue.put_nowait(jpeg_bytes)
            except queue.Full:
                pass

        except Exception as e:
            logging.error(f"Camera capture error: {e}")
            time.sleep(0.1)


# ========================
# Web 页面（保持不变）
# ========================
PAGE = """\
<html>
<head>
<meta charset="UTF-8">
<title>YOLO Camera Control</title>
<style>
  body {
    margin: 0;
    padding: 20px;
    padding-top: 100px;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background-color: #f5f5f5;
    display: flex;
    flex-direction: row;
    align-items: flex-start;
    justify-content: flex-start;
    min-height: 100vh;
    gap: 30px;
  }

  .video-container {
    flex-shrink: 0;
  }

  .panel {
    background: white;
    padding: 20px;
    border-radius: 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .btn {
    width: 70px;
    height: 70px;
    margin: 8px;
    border: none;
    border-radius: 12px;
    background: #4CAF50;
    color: white;
    font-size: 18px;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 6px rgba(0,0,0,0.2);
  }

  .btn:hover {
    background: #45a049;
    transform: scale(1.05);
  }

  .btn:active {
    transform: scale(0.98);
  }

  .direction-btn {
    width: 80px;
    height: 80px;
    border-radius: 50%;
  }

  .center-btn {
    background: #2196F3;
  }
  .center-btn:hover {
    background: #1E88E5;
  }

  .function-row {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 8px;
    width: 100%;
    max-width: 300px;
  }

  .func-btn {
    background: #FF9800;
    width: 60px;
    height: 60px;
    border-radius: 10px;
    font-size: 14px;
  }
  .func-btn:hover {
    background: #F57C00;
  }

  h2 {
    margin: 10px 0;
    color: #333;
    font-size: 18px;
  }

  .temp-display {
    margin-bottom: 10px;
    font-size: 18px;
    color: #e74c3c;
    font-weight: bold;
  }
</style>
<script>
function sendCmd(direction) {
    fetch('/cmd/' + direction, {method: 'POST'})
        .then(response => {
            if (!response.ok) alert('命令执行失败: ' + direction);
        })
        .catch(err => {
            console.error('请求出错:', err);
            alert('网络错误');
        });
}

function updateTemperature() {
    fetch('/temperature')
        .then(response => {
            if (!response.ok) throw new Error('获取失败');
            return response.text();
        })
        .then(temp => {
            document.getElementById('cpu-temp').textContent = temp + '°C';
        })
        .catch(err => {
            console.error('温度获取失败:', err);
            document.getElementById('cpu-temp').textContent = 'N/A';
        });
}

document.addEventListener('DOMContentLoaded', () => {
    updateTemperature();
    setInterval(updateTemperature, 2000);
});
</script>
</head>
<body>
  <div class="video-container">
    <img src="stream.mjpg" width="640" height="480" style="border: 1px solid #ddd; border-radius: 8px;" />
    <div class="temp-display">CPU 温度: <span id="cpu-temp">--</span></div>
    <h1>YOLO 实时检测画面</h1>
  </div>

  <div class="panel">
    <h2>方向控制</h2>
    <button class="btn direction-btn" onclick="sendCmd('up')">↑</button>
    <div style="display:flex; gap:10px; margin:10px 0;">
      <button class="btn direction-btn" onclick="sendCmd('left')">←</button>
      <button class="btn direction-btn center-btn" onclick="sendCmd('center')">●</button>
      <button class="btn direction-btn" onclick="sendCmd('right')">→</button>
    </div>
    <button class="btn direction-btn" onclick="sendCmd('down')">↓</button>
  </div>

  <div class="panel">
    <h2>功能按钮</h2>
    <div class="function-row">
      <button class="btn func-btn" onclick="sendCmd('f1')">抬头握手</button>
      <button class="btn func-btn" onclick="sendCmd('f2')">检测橙子</button>
      <button class="btn func-btn" onclick="sendCmd('f3')">F3</button>
      <button class="btn func-btn" onclick="sendCmd('f4')">F4</button>
      <button class="btn func-btn" onclick="sendCmd('f5')">F5</button>
      <button class="btn func-btn" onclick="sendCmd('f6')">F6</button>
      <button class="btn func-btn" onclick="sendCmd('f7')">F7</button>
      <button class="btn func-btn" onclick="sendCmd('f8')">F8</button>
      <button class="btn func-btn" onclick="sendCmd('f9')">F9</button>
      <button class="btn func-btn" onclick="sendCmd('f10')">F10</button>
    </div>
  </div>
</body>
</html>
"""


# ========================
# HTTP Handler
# ========================
class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.annotated_frame
                    if frame:
                        self.wfile.write(b'--FRAME\r\n')
                        self.send_header('Content-Type', 'image/jpeg')
                        self.send_header('Content-Length', len(frame))
                        self.end_headers()
                        self.wfile.write(frame)
                        self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning('Removed streaming client %s: %s', self.client_address, str(e))
        elif self.path == '/temperature':
            temp = get_cpu_temperature()
            if temp is not None:
                response = f"{temp:.1f}".encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.send_header('Content-Length', len(response))
                self.end_headers()
                self.wfile.write(response)
            else:
                self.send_error(500, "Failed to read CPU temperature")
        else:
            self.send_error(404)

    def do_POST(self):
        logging.info(f"Received POST to: {self.path}")
        if self.path.startswith('/cmd/'):
            cmd = self.path.split('/')[-1]
            if cmd == 'f2':
                with output.condition:
                    frame_bytes = output.raw_frame
                if frame_bytes is None:
                    self.send_error(500, "No frame available")
                    return

                orange_found = False
                if model is not None:
                    try:
                        image = Image.open(io.BytesIO(frame_bytes)).convert('RGB')
                        img_array = np.array(image)
                        results = model(img_array, verbose=False)
                        for result in results:
                            if result.boxes is not None:
                                cls_indices = result.boxes.cls.cpu().numpy().astype(int)
                                for idx in cls_indices:
                                    if result.names.get(idx) == "orange":
                                        orange_found = True
                                        break
                    except Exception as e:
                        logging.error(f"f2 detection error: {e}")

                if orange_found:
                    send_voice_cmd(CMD_ORANGE_DETECTED)
                    logging.info("🍊 Orange detected! Voice command sent.")
                else:
                    logging.info("No orange detected.")

                self.send_response(200)
                self.end_headers()

            elif cmd in SCRIPTS:
                script_path = SCRIPTS[cmd]
                if script_path is None:
                    self.send_error(400, "Command not implemented")
                    return
                try:
                    result = subprocess.run(['python3', script_path], capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        self.send_response(200)
                        self.end_headers()
                        logging.info(f"Executed: {cmd}")
                    else:
                        logging.error(f"Script failed: {result.stderr}")
                        self.send_error(500)
                except Exception as e:
                    logging.error(f"Run script error: {e}")
                    self.send_error(500)
            else:
                self.send_error(400, "Invalid command")
        else:
            self.send_error(404)


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


# ========================
# 主程序启动
# ========================
if __name__ == '__main__':
    output = StreamingOutput()
    raw_frame_queue = queue.Queue(maxsize=1)

    # 启动 YOLO 推理线程
    stop_inference = Event()
    inference_thread = None
    if model is not None:
        inference_thread = Thread(
            target=yolo_inference_thread,
            args=(raw_frame_queue, output, model, stop_inference),
            daemon=True
        )
        inference_thread.start()
        print("🧵 YOLO inference thread started.")

    # 启动摄像头（不使用 FileOutput）
    picam2 = Picamera2()
    video_config = picam2.create_video_configuration(
        main={"size": (640, 480)},
        controls={"FrameRate": 10.0}
    )
    picam2.configure(video_config)
    picam2.start()

    # 启动采集线程
    stop_capture = Event()
    capture_thread = Thread(
        target=camera_capture_thread,
        args=(picam2, raw_frame_queue, stop_capture),
        daemon=True
    )
    capture_thread.start()
    print("📸 Camera capture thread started.")

    try:
        address = ('', 8000)
        server = StreamingServer(address, StreamingHandler)
        print("🚀 Starting stable YOLO streaming server on port 8000...")
        print("🌐 Open http://<your-pi-ip>:8000")
        server.serve_forever()
    finally:
        stop_capture.set()
        stop_inference.set()
        if inference_thread:
            inference_thread.join(timeout=2)
        if capture_thread:
            capture_thread.join(timeout=2)
        picam2.stop()
        if ser and ser.is_open:
            ser.close()
        print("🛑 Server stopped cleanly.")
