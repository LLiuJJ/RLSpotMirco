#!/usr/bin/python3

import io
import logging
import socketserver
from http import server
from threading import Condition
import subprocess
import os

from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput

# === 配置你的五个脚本路径（请确保这些脚本存在且可执行）===
SCRIPTS = {
    'up': '/home/pi/scripts/up.py',
    'down': '/home/pi/scripts/down.py',
    'left': '/home/pi/scripts/left.py',
    'right': '/home/pi/scripts/right.py',
    'center': '/home/pi/scripts/center.py',
    # 功能按钮 f1 ~ f10
    'f1': '/home/pi/scripts/f1.py',
    'f2': '/home/pi/scripts/f2.py',
    'f3': '/home/pi/scripts/f3.py',
    'f4': '/home/pi/scripts/f4.py',
    'f5': '/home/pi/scripts/f5.py',
    'f6': '/home/pi/scripts/f6.py',
    'f7': '/home/pi/scripts/f7.py',
    'f8': '/home/pi/scripts/f8.py',
    'f9': '/home/pi/scripts/f9.py',
    'f10': '/home/pi/scripts/f10.py',
}

# 安全检查：确保脚本存在
for name, path in SCRIPTS.items():
    if not os.path.isfile(path):
        logging.warning(f"Script for '{name}' not found: {path}")


def get_cpu_temperature():
    """返回 CPU 温度，单位为摄氏度（float），失败返回 None"""
    try:
        # 方法1：使用 vcgencmd（树莓派官方工具，最准确）
        result = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True, text=True, timeout=2)
        temp_str = result.stdout.strip()
        return float(temp_str.replace("temp=", "").replace("'C", ""))
    except Exception as e1:
        try:
            # 方法2：读取 sysfs（通用 Linux 方法）
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                return int(f.read().strip()) / 1000.0
        except Exception as e2:
            logging.error(f"Failed to read CPU temperature: vcgencmd={e1}, sysfs={e2}")
            return None


PAGE = """\
<html>
<head>
<meta charset="UTF-8">
<title>Camera Control</title>
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

// 自动更新 CPU 温度
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
    updateTemperature(); // 立即获取一次
    setInterval(updateTemperature, 2000); // 每2秒刷新
});
</script>
</head>
<body>
  <div class="video-container">
    <img src="stream.mjpg" width="640" height="480" style="border: 1px solid #ddd; border-radius: 8px;" />
    <div class="temp-display">CPU 温度: <span id="cpu-temp">--</span></div>
    <h1>摄像头实时画面</h1>
</div>

  <!-- 方向控制 -->
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

  <!-- 功能按钮 f1~f10 -->
  <div class="panel">
    <h2>功能按钮</h2>
    <div class="function-row">
      <button class="btn func-btn" onclick="sendCmd('f1')">抬头握手</button>
      <button class="btn func-btn" onclick="sendCmd('f2')">F2</button>
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


class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


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
                        frame = output.frame
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
                response_text = f"{temp:.1f}"
                response = response_text.encode('utf-8')
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
        if self.path.startswith('/cmd/'):
            cmd = self.path.split('/')[-1]
            if cmd in SCRIPTS:
                script_path = SCRIPTS[cmd]
                try:
                    result = subprocess.run(['python3', script_path], capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        self.send_response(200)
                        self.end_headers()
                        logging.info(f"Executed script: {cmd} -> {script_path}")
                    else:
                        logging.error(f"Script failed: {cmd}, stderr: {result.stderr}")
                        self.send_error(500)
                except subprocess.TimeoutExpired:
                    logging.error(f"Script timeout: {cmd}")
                    self.send_error(500)
                except Exception as e:
                    logging.error(f"Failed to run script {cmd}: {e}")
                    self.send_error(500)
            else:
                self.send_error(400, "Invalid command")
        else:
            self.send_error(404)


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
output = StreamingOutput()
picam2.start_recording(JpegEncoder(), FileOutput(output))

try:
    address = ('', 8000)
    server = StreamingServer(address, StreamingHandler)
    print("Starting server on port 8000...")
    print("Open http://<your-pi-ip>:8000 in your browser")
    server.serve_forever()
finally:
    picam2.stop_recording()
