#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>


#define IR_RECEIVE_PIN 45

// 定义 Trig 和 Echo 引脚
const int trigPin = 2;
const int echoPin = 3;

// 红外按键：防抖参数
unsigned long lastCode = 0;
const unsigned long DEBOUNCE_DELAY = 250; // 毫秒，防止重复触发


// 0 RF_UP
// 1 RF_MID
// 2 RF_DOWN

// 3 LF_UP
// 4 LF_MID
// 5 LF_DOWN

// 6 LB_UP
// 7 LB_MID
// 8 LB_DOWN

// 9 RB_UP
// 10 RB_MID
// 11 RB_DOWN

const int RF_UP = 0;
const int RF_DOWN = 2;
const int RF_MID  = 1;
const int LF_MID = 4;
const int LF_UP = 3;
const int LF_DOWN = 5;

const int LB_MID = 7;
const int LB_DOWN = 8;
const int LB_UP = 6;

const int RB_MID = 10;
const int RB_UP = 9;
const int RB_DOWN = 11;

const int STEP_DELAY = 300;

// 蓝牙心跳
unsigned long lastPing = 0;
const long PING_INTERVAL = 3000; // 3秒心跳


// 创建 PCA9685 对象（默认地址 0x40）
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// === 舵机参数（针对 SPT5425LV，6V 供电）===
// 实测建议值（需根据你的舵机微调）
#define SERVOMIN  102  // ≈ 500μs
#define SERVOMAX  512  // ≈ 2500μs
// 注：SG90 通常为 100~500，金属舵机范围更大

// 舵机通道分配（示例：四足狗，3DoF×4腿=12舵机）
const byte LEG_CHANNELS[12] = {
  0, 1, 2,   // 左前腿：髋、膝、踝
  3, 4, 5,   // 右前腿
  6, 7, 8,   // 左后腿
  9,10,11    // 右后腿
};


Adafruit_MPU6050 mpu;

void setup() {

  Serial.begin(115200);
  Serial.println("PCA9685 初始化...");

  Serial1.begin(115200); 

  if (!mpu.begin()) {
    Serial.println("MPU6050 未找到！");
    while (1) delay(10);
  }

  Serial.println("MPU6050 初始化成功！");

  // 可选：设置量程（默认即可）
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);


  pwm.begin();
  pwm.setPWMFreq(50);  // 舵机标准频率：50Hz

  // 初始化所有舵机到 90°
  for (int i = 0; i < 12; i++) {
    setServoAngle(i, 90);
  }

  // 超声波
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);

  delay(10);

}

// 将角度（0~180）转换为 PCA9685 的 PWM 值
uint16_t angleToPWM(int angle) {
  angle = constrain(angle, 0, 180);
  return map(angle, 0, 180, SERVOMIN, SERVOMAX);
}

// 设置指定舵机角度
void setServoAngle(byte channel, int angle) {
  uint16_t pulse = angleToPWM(angle);
  pwm.setPWM(channel, 0, pulse);
}


// 坐下
void sitDown() {
 setServoAngle(RF_UP, 90);
 setServoAngle(RF_DOWN, 90);
 setServoAngle(RF_MID, 90);
 setServoAngle(LF_MID, 90);
 setServoAngle(LF_UP, 90);
 setServoAngle(LF_DOWN, 90);
 setServoAngle(LB_MID, 90);
 setServoAngle(LB_DOWN, 90);
 setServoAngle(LB_UP, 90);
 setServoAngle(RB_MID, 90);
 setServoAngle(RB_UP, 90);
 setServoAngle(RB_DOWN, 90);

 delay(3000);
}

void Stand() {
    
    setServoAngle(LB_UP, 90);
    setServoAngle(LB_DOWN, 60);
    setServoAngle(RB_UP, 90);
    setServoAngle(RB_DOWN, 120);
    delay(1000);


    setServoAngle(LF_UP, 90);
    setServoAngle(LF_DOWN, 60);
    setServoAngle(RF_UP, 90);
    setServoAngle(RF_DOWN, 120);

    delay(2000);

}

void Sleep() {
    setServoAngle(LB_UP, 20);
    setServoAngle(LB_DOWN, 150);
    setServoAngle(RB_UP, 160);
    setServoAngle(RB_DOWN, 30);


    setServoAngle(LF_UP, 20);
    setServoAngle(LF_DOWN, 150);
    setServoAngle(RF_UP, 160);
    setServoAngle(RF_DOWN, 30);
    delay(1000);

}

// 站立起来
void SlowStandUp() {
  sitDown();

  for(int i = 0; i < 50; i++) {
    setServoAngle(LF_UP, 90 - i);
    setServoAngle(LB_UP, 90 - i);

    setServoAngle(RF_UP, 90 + i);
    setServoAngle(RB_UP, 90 + i);

    delay(100);
  }            

  // for(int i = 0; i < 20; i++) {
  //   setServoAngle(LF_DOWN, 90 - i);
  //   setServoAngle(LB_DOWN, 90 - i);

  //   setServoAngle(RF_DOWN, 90 + i);
  //   setServoAngle(RB_DOWN, 90 + i);

  //   delay(100);
  // }            

  delay(2000);
}

void LookUp() {
    sitDown();
    
    setServoAngle(RF_DOWN, 130);
    setServoAngle(LF_DOWN, 70);

    delay(1000);
}

// 步态参数
const int NUM_SWING = 20;   // 摆动相点数
const int NUM_SUPPORT = 20; // 支撑相点数
const int TOTAL_FRAMES = NUM_SWING + NUM_SUPPORT;
const int FRAME_DELAY = 20; // 每帧间隔 ms

//
// cal_angle.py 生成
// 模型参数（与 MATLAB 和之前的示例一致）
// L1 = 12.0  # 大腿长度 (cm)
// L2 = 12.0  # 小腿长度 (cm)
// R = 3    # 半圆半径 (cm)
// center_y = -13.0  # 相对于髋关节(0,0)的Y坐标
// num_swing = 20   # 摆动相点数
// num_support = 20 # 支撑相点数
//
// python cal_angle.py  [注意！这里计算结果要倒转一下，先抬腿画半圆，再向后画直线]
// PROGMEM const uint8_t hipAngles[40] = {
// 47, 46, 44, 42, 40, 38, 35, 32, 29, 26, 23, 21, 19, 17, 17, 16, 17, 18, 19, 21, 
// 21, 22, 23, 24, 26, 27, 28, 29, 31, 32, 33, 35, 36, 38, 39, 41, 42, 44, 45, 47
// };

// PROGMEM const uint8_t kneeAngles[40] = {
// 68, 65, 62, 59, 57, 54, 53, 51, 50, 49, 49, 50, 51, 53, 54, 57, 59, 62, 65, 68, 
// 68, 67, 67, 67, 66, 66, 66, 66, 66, 66, 66, 66, 66, 66, 66, 66, 67, 67, 67, 68
// };

PROGMEM const uint8_t hipAnglesBak[TOTAL_FRAMES] =  {
21, 19, 18, 17, 16, 17, 17, 19, 21, 23, 26, 29, 32, 35, 38, 40, 42, 44, 46, 47,
47, 45, 44, 42, 41, 39, 38, 36, 35, 33, 32, 31, 29, 28, 27, 26, 24, 23, 22, 21
};

PROGMEM const uint8_t kneeAnglesBak[TOTAL_FRAMES] = {
68, 65, 62, 59, 57, 54, 53, 51, 50, 49, 49, 50, 51, 53, 54, 57, 59, 62, 65, 68, 
68, 67, 67, 67, 66, 66, 66, 66, 66, 66, 66, 66, 66, 66, 66, 66, 67, 67, 67, 68
};


// small
PROGMEM const uint8_t hipAnglesSmall[TOTAL_FRAMES] =  {
39, 37, 35, 33, 32, 32, 32, 33, 34, 36, 38, 41, 44, 47, 49, 52, 55, 57, 59, 61,
61, 59, 58, 57, 55, 54, 53, 52, 50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 40, 39
};

PROGMEM const uint8_t kneeAnglesSmall[TOTAL_FRAMES] = {
100, 95, 91, 88, 84, 81, 79, 77, 75, 74, 74, 75, 77, 79, 81, 84, 88, 91, 95, 100, 
100, 99, 99, 98, 98, 98, 98, 97, 97, 97, 97, 97, 97, 98, 98, 98, 98, 99, 99, 100
};



// L1 = 12.0  # 大腿长度 (cm)
// L2 = 12.0  # 小腿长度 (cm)
// R = 5    # 半圆半径 (cm)
// center_y = -13.0  # 相对于髋关节(0,0)的Y坐标
// num_swing = 20   # 摆动相点数
// num_support = 20 # 支撑相点数
// PROGMEM const uint8_t hipAngles[40] = {
// 57, 55, 53, 51, 48, 44, 40, 35, 29, 22, 17, 12, 8, 5, 4, 5, 6, 8, 11, 14, 14, 16, 18, 19, 21, 23, 25, 27, 29, 32, 34, 36, 39, 41, 44, 46, 49, 51, 54, 57
// };

// PROGMEM const uint8_t kneeAngles[40] = {
// 71, 66, 62, 57, 53, 49, 45, 42, 40, 39, 39, 40, 42, 45, 49, 53, 57, 62, 66, 71, 71, 70, 69, 68, 67, 67, 66, 66, 66, 66, 66, 66, 66, 66, 67, 67, 68, 69, 70, 71
// };

PROGMEM const uint8_t hipAnglesBig[TOTAL_FRAMES] =  {
27, 24, 21, 19, 17, 17, 17, 19, 22, 25, 29, 34, 39, 43, 48, 51, 55, 57, 60, 62,
62, 59, 57, 55, 53, 51, 49, 47, 45, 43, 41, 39, 37, 36, 34, 32, 31, 30, 28, 27
};

PROGMEM const uint8_t kneeAnglesBig[TOTAL_FRAMES] = {
89, 83, 78, 73, 69, 64, 61, 58, 56, 55, 55, 56, 58, 61, 64, 69, 73, 78, 83, 89,
89, 88, 87, 86, 85, 85, 84, 84, 84, 84, 84, 84, 84, 84, 85, 85, 86, 87, 88, 89
};


void slowBackWalk() {
 for (int i = 0; i < TOTAL_FRAMES; i++) {
    uint8_t h = pgm_read_byte(&hipAnglesBak[i]);
    uint8_t k = pgm_read_byte(&kneeAnglesBak[i]);

    setServoAngle(LF_UP, h);
    setServoAngle(LF_DOWN, 180 - k);

    setServoAngle(RB_UP, 180 - h);
    setServoAngle(RB_DOWN, k);

    delay(FRAME_DELAY);
  }

  delay(1000);

  for (int i = 0; i < TOTAL_FRAMES; i++) {
    uint8_t h = pgm_read_byte(&hipAnglesBak[i]);
    uint8_t k = pgm_read_byte(&kneeAnglesBak[i]);

    setServoAngle(LB_UP, h);
    setServoAngle(LB_DOWN, 180 - k);

    setServoAngle(RF_UP, 180 - h);
    setServoAngle(RF_DOWN, k);

    delay(FRAME_DELAY);
  }
}

void runCycleRight() {

    int kc = 0;
    for (int i = 20; i < TOTAL_FRAMES; i++) {
      uint8_t h = pgm_read_byte(&hipAnglesSmall[i]);
      uint8_t k = pgm_read_byte(&kneeAnglesSmall[i]);

      uint8_t hr = pgm_read_byte(&hipAnglesSmall[39 - kc]);
      uint8_t kr = pgm_read_byte(&kneeAnglesSmall[39 - kc]);

      // 左前右后前划
      setServoAngle(LF_UP, h);
      setServoAngle(LF_DOWN, 180 - k);

      setServoAngle(RB_UP, 180 - hr);
      setServoAngle(RB_DOWN, kr);


      kc = kc + 1;
      delay(10);
    }

    delay(20);

    kc = 0;

    for (int i = 20; i < TOTAL_FRAMES; i++) {
      uint8_t h = pgm_read_byte(&hipAnglesSmall[i]);
      uint8_t k = pgm_read_byte(&kneeAnglesSmall[i]);

      uint8_t hr = pgm_read_byte(&hipAnglesSmall[39 - kc]);
      uint8_t kr = pgm_read_byte(&kneeAnglesSmall[39 - kc]);


      // 左后右前后划
      setServoAngle(LB_UP, h);
      setServoAngle(LB_DOWN, 180 - k);

      setServoAngle(RF_UP, 180 - hr);
      setServoAngle(RF_DOWN, kr);

      kc = kc + 1;

      delay(10);
    }

}


void runCycleLeft() {

    int kc = 0;
    for (int i = 20; i < TOTAL_FRAMES; i++) {
      uint8_t h = pgm_read_byte(&hipAnglesSmall[i]);
      uint8_t k = pgm_read_byte(&kneeAnglesSmall[i]);

      uint8_t hr = pgm_read_byte(&hipAnglesSmall[39 - kc]);
      uint8_t kr = pgm_read_byte(&kneeAnglesSmall[39 - kc]);

      // 左前右后前划
      setServoAngle(LF_UP, hr);
      setServoAngle(LF_DOWN, 180 - kr);

      setServoAngle(RB_UP, 180 - h);
      setServoAngle(RB_DOWN, k);


      kc = kc + 1;
      delay(10);
    }

    delay(20);

    kc = 0;

    for (int i = 20; i < TOTAL_FRAMES; i++) {
      uint8_t h = pgm_read_byte(&hipAnglesSmall[i]);
      uint8_t k = pgm_read_byte(&kneeAnglesSmall[i]);

      uint8_t hr = pgm_read_byte(&hipAnglesSmall[39 - kc]);
      uint8_t kr = pgm_read_byte(&kneeAnglesSmall[39 - kc]);


      // 左后右前后划
      setServoAngle(LB_UP, hr);
      setServoAngle(LB_DOWN, 180 - kr);

      setServoAngle(RF_UP, 180 - h);
      setServoAngle(RF_DOWN, k);

      kc = kc + 1;

      delay(10);
    }

}

void rightSlowBackWalk() {
    setServoAngle(RF_MID, 100);
    setServoAngle(RB_MID, 80);

    delay(100);

    for (int i = 0; i < TOTAL_FRAMES; i++) {
      uint8_t h = pgm_read_byte(&hipAnglesBak[i]);
      uint8_t k = pgm_read_byte(&kneeAnglesBak[i]);

      uint8_t hbig = pgm_read_byte(&hipAnglesBig[i]);
      uint8_t kbig = pgm_read_byte(&kneeAnglesBig[i]);


      setServoAngle(LF_UP, hbig);
      setServoAngle(LF_DOWN, 180 - kbig);

      setServoAngle(RB_UP, 180 - h);
      setServoAngle(RB_DOWN, k);

      delay(FRAME_DELAY);
    }

  delay(100);

  for (int i = 0; i < TOTAL_FRAMES; i++) {
    uint8_t h = pgm_read_byte(&hipAnglesBak[i]);
    uint8_t k = pgm_read_byte(&kneeAnglesBak[i]);

    uint8_t hbig = pgm_read_byte(&hipAnglesBig[i]);
    uint8_t kbig = pgm_read_byte(&kneeAnglesBig[i]);

    setServoAngle(LB_UP, hbig);
    setServoAngle(LB_DOWN, 180 - kbig);

    setServoAngle(RF_UP, 180 - h);
    setServoAngle(RF_DOWN, k);

    delay(FRAME_DELAY);
  }
}

void leftSlowBackWalk() {

    setServoAngle(LF_MID, 80);
    setServoAngle(LB_MID, 100);
    delay(100);

 for (int i = 0; i < TOTAL_FRAMES; i++) {
    uint8_t h = pgm_read_byte(&hipAnglesBak[i]);
    uint8_t k = pgm_read_byte(&kneeAnglesBak[i]);

    uint8_t hbig = pgm_read_byte(&hipAnglesBig[i]);
    uint8_t kbig = pgm_read_byte(&kneeAnglesBig[i]);


    setServoAngle(LF_UP, h);
    setServoAngle(LF_DOWN, 180 - k);

    setServoAngle(RB_UP, 180 - hbig);
    setServoAngle(RB_DOWN, kbig);

    delay(FRAME_DELAY);
  }

  delay(100);

  for (int i = 0; i < TOTAL_FRAMES; i++) {
    uint8_t h = pgm_read_byte(&hipAnglesBak[i]);
    uint8_t k = pgm_read_byte(&kneeAnglesBak[i]);

    uint8_t hbig = pgm_read_byte(&hipAnglesBig[i]);
    uint8_t kbig = pgm_read_byte(&kneeAnglesBig[i]);

    setServoAngle(LB_UP, h);
    setServoAngle(LB_DOWN, 180 - k);

    setServoAngle(RF_UP, 180 - hbig);
    setServoAngle(RF_DOWN, kbig);

    delay(FRAME_DELAY);
  }
}


// =============== 定义你的命令列表 ===============
struct Command {
  const byte* pattern;   // 指令字节序列
  int length;            // 指令长度
  const char* action;    // 对应的动作名称（可打印）
};

// 具体指令（按你提供的格式）
const byte CMD_RUN[]    = {0xAA, 0x55, 0x00, 0x04, 0xFB};
const byte CMD_DOWN[]  = {0xAA, 0x55, 0x00, 0x01, 0xFB};
const byte CMD_UP[]  = {0xAA, 0x55, 0x00, 0x02, 0xFB};
const byte CMD_LOOPUP[] = {0xAA, 0x55, 0x00, 0x2D, 0xFB};
const byte CMD_LEFT[] = {0xAA, 0x55, 0x00, 0x29, 0xFB};
const byte CMD_RIGHT[] = {0xAA, 0x55, 0x00, 0x2A, 0xFB}; 


const byte CMD_CYCLE_LEFT[] = {0xAA, 0x55, 0x00, 0x08, 0xFB};
const byte CMD_CYCLE_RIGHT[] = {0xAA, 0x55, 0x00, 0x09, 0xFB};



// 命令表（数组）
const Command commandList[] = {
  {CMD_RUN,    sizeof(CMD_RUN),    "run"},
  {CMD_DOWN,  sizeof(CMD_DOWN),  "down"},
  {CMD_UP,  sizeof(CMD_UP),  "up"},
  {CMD_LOOPUP, sizeof(CMD_LOOPUP), "lookup"},
  {CMD_LEFT, sizeof(CMD_LEFT), "left"},
  {CMD_RIGHT, sizeof(CMD_RIGHT), "right"},
  {CMD_CYCLE_LEFT, sizeof(CMD_CYCLE_LEFT), "cycleleft"},
  {CMD_CYCLE_RIGHT, sizeof(CMD_CYCLE_RIGHT), "cycleright"}
};

const int numCommands = sizeof(commandList) / sizeof(Command);

// =============== 缓冲区设置 ===============
// 找出最长指令的长度，作为缓冲区大小
const int MAX_CMD_LENGTH = 5; // 这里都是5字节，可手动设为5；也可用宏自动计算（略复杂）

byte buffer[MAX_CMD_LENGTH];
int index = 0;

// MPU
float angleRoll = 0, anglePitch = 0, realAngleRoll = 0;
unsigned long lastTime = 0;

void loop() {

// slowBackWalk();
// runCycle();
// runCycleLeft();

  {
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  float dt = (millis() - lastTime) / 1000.0;
  lastTime = millis();

  // 1. 陀螺仪积分（单位：度/秒 → 度）
  float gyroRoll = g.gyro.x * 180 / PI;
  float gyroPitch = g.gyro.y * 180 / PI;

  angleRoll += gyroRoll * dt;
  anglePitch += gyroPitch * dt;

  // 2. 加速度计计算静态角度（无 Z 轴旋转时有效）
  float accRoll = atan2(a.acceleration.y, a.acceleration.z) * 180 / PI;
  float accPitch = atan2(-a.acceleration.x, 
                         sqrt(a.acceleration.y * a.acceleration.y + a.acceleration.z * a.acceleration.z)) * 180 / PI;

  // 3. 互补滤波（α ≈ 0.96 表示更信任陀螺仪）
  const float alpha = 0.96;
  angleRoll = alpha * (angleRoll) + (1 - alpha) * accRoll;
  anglePitch = alpha * (anglePitch) + (1 - alpha) * accPitch;
  realAngleRoll = angleRoll + 180;


  Serial.print("Roll: ");
  Serial.print(realAngleRoll);
  Serial.print("°, Pitch: ");
  Serial.print(anglePitch);
  Serial.println("°");
  delay(10);

}

{
// 清空触发引脚
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  
  // 发送 10μs 高电平触发信号
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  // 读取 Echo 高电平持续时间（单位：微秒）
  long duration = pulseIn(echoPin, HIGH);
  
  // 计算距离（声速 ≈ 340 m/s = 0.034 cm/μs）
  // 距离 = (时间 × 声速) / 2（往返）
  float distance = duration * 0.034 / 2.0; // 单位：厘米
  
  Serial.print("Distance: ");
  Serial.print(distance);
  Serial.println(" cm");
}

  while (Serial1.available()) {
    byte b = Serial1.read();

    // 存入循环缓冲区
    buffer[index] = b;
    index = (index + 1) % MAX_CMD_LENGTH;

    // 尝试匹配每一条命令
    for (int i = 0; i < numCommands; i++) {
      const Command& cmd = commandList[i];
      
      // 只有当缓冲区已满（至少收到 cmd.length 字节）才匹配
      // 我们假设所有命令长度相同（如5字节），简化处理
      if (cmd.length == MAX_CMD_LENGTH) {
        // 构造一个临时视图：从 (index) 开始往前推 length 个字节
        bool match = true;
        for (int j = 0; j < cmd.length; j++) {
          if (buffer[(index + j) % MAX_CMD_LENGTH] != cmd.pattern[j]) {
            match = false;
            break;
          }
        }
        if (match) {
          Serial.println(cmd.action); // 打印 "up", "down" 等
          
          // 🔔 可在此处添加实际控制逻辑
          if (strcmp(cmd.action, "up") == 0) {
            SlowStandUp();
          } else if (strcmp(cmd.action, "down") == 0) {
            sitDown();
          } else if (strcmp(cmd.action, "run") == 0) { 
            slowBackWalk();
          } else if (strcmp(cmd.action, "lookup") == 0) {
            LookUp();
          } else if (strcmp(cmd.action, "left") == 0) {
            leftSlowBackWalk();
          } else if (strcmp(cmd.action, "right") == 0) {
            rightSlowBackWalk();
          } else if (strcmp(cmd.action, "cycleright") == 0) {
            for (int i = 0; i < 5; i ++) {
              runCycleRight();
            }
          } else if (strcmp(cmd.action, "cycleleft") == 0) {
            for (int i = 0; i < 5; i ++) {
              runCycleLeft();
            }
          }
          
          break; // 匹配成功，跳出 for 循环（避免重复匹配）
        }
      }
    }
  }
}