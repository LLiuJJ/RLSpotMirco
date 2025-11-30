#include <Servo.h>  // 包含舵机库
#include <IRremote.h>

#define IR_RECEIVE_PIN 45

// 超声波：HC-SR04 接在 Trig=D30, Echo=D28
const int TRIG_PIN = 30;
const int ECHO_PIN = 28;

// 红外按键：防抖参数
unsigned long lastCode = 0;
unsigned long lastTime = 0;
const unsigned long DEBOUNCE_DELAY = 250; // 毫秒，防止重复触发

 
// 定义连接舵机的 Arduino Mega 引脚
// 使用 Mega 上的 PWM 引脚 (2~13 或 44~46)
// 这里选择引脚 6~13 (共8个连续引脚，方便管理) , 13会被干扰
//
//
// 0: 2 -> R 前上  1: 3 -> R 前下 2: 4 -> R 前中
// 3: 5 -> L 前中  4: 6 -> L 前上 5: 7 -> L 前下
// 6: 8 -> L 后中  7: 9 -> L 后下 8: 10 -> L 后上   
// 9: 11 -> R 后中 10: 12 -> R 后上 11: 46 -> R 后下
//
Servo RF_UP;
Servo RF_DOWN;
Servo RF_MID;
Servo LF_MID;
Servo LF_UP;
Servo LF_DOWN;

Servo LB_MID;
Servo LB_DOWN;
Servo LB_UP;
Servo RB_MID;
Servo RB_UP;
Servo RB_DOWN;


const int STEP_DELAY = 300;

// 蓝牙心跳
unsigned long lastPing = 0;
const long PING_INTERVAL = 3000; // 3秒心跳

// 坐下
void sitDown() {
 RF_UP.write(90);
 RF_DOWN.write(90);
 RF_MID.write(90);
 LF_MID.write(90);
 LF_UP.write(90);
 LF_DOWN.write(90);

 LB_MID.write(90);
 LB_DOWN.write(90);
 LB_UP.write(90);
 RB_MID.write(90);
 RB_UP.write(90);
 RB_DOWN.write(90);

 delay(3000);
}

// 抬头握手
//
void lookUp() {
 RF_UP.write(90);
 RF_DOWN.write(20);
 RF_MID.write(90);
 LF_MID.write(90);
 LF_UP.write(90);
 LF_DOWN.write(160);

 LB_MID.write(90);
 LB_DOWN.write(90);
 LB_UP.write(90);
 RB_MID.write(90);
 RB_UP.write(90);
 RB_DOWN.write(90);
 delay(1000);

  // 上下摆握手
  for (int i = 20; i < 120; i++) {
    RF_DOWN.write(i);
    delay(10);
  }
}

// 站立起来
void SlowStandUp() {
  LF_UP.write(180);  
  LB_UP.write(180); 
  
  RF_UP.write(0); 
  RB_UP.write(0); 

  LF_DOWN.write(0);  
  LB_DOWN.write(0); 
  
  RF_DOWN.write(180); 
  RB_DOWN.write(180); 

  delay(100);

  LF_DOWN.write(50);  
  LB_DOWN.write(50); 
  
  RF_DOWN.write(130); 
  RB_DOWN.write(130); 
  delay(1000);

  LF_MID.write(105);
  RF_MID.write(75);
}


void setup() {
  // 初始化与电脑通信的串口，用于调试
  Serial.begin(115200);
  IrReceiver.begin(IR_RECEIVE_PIN, ENABLE_LED_FEEDBACK); // 启用板载 LED 反馈（如有）
  Serial.println("KEYES 红外接收（带防抖）");

  // 初始化与蓝牙模块通信的串口
  Serial1.begin(9600); // HC-05 默认波特率通常是 9600 或 38400

  // 超声波模块初始化
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  // 绑定舵机 PWM 信号口
  // 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 46
  RF_UP.attach(2);
  RF_DOWN.attach(3);
  RF_MID.attach(4);
  LF_MID.attach(5);
  LF_UP.attach(6);
  LF_DOWN.attach(7);
  LB_MID.attach(8);
  LB_DOWN.attach(9);
  LB_UP.attach(10);
  RB_MID.attach(11);
  RB_UP.attach(12);
  RB_DOWN.attach(46);

  // 初始化状态为坐下                                                                                                                                                                                                                                                                            
  sitDown();
}

// 步态参数
const int NUM_SWING = 20;   // 摆动相点数
const int NUM_SUPPORT = 20; // 支撑相点数
const int TOTAL_FRAMES = NUM_SWING + NUM_SUPPORT;
const int FRAME_DELAY = 30; // 每帧间隔 ms

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



void stepForward() {           
  // 抬起左前 & 右后腿
  LF_DOWN.write(40); 
  RB_DOWN.write(140);
  delay(200);
  LF_DOWN.write(50); 
  RB_DOWN.write(130);
  delay(200);
  // 抬起左后 & 右前腿
  LB_DOWN.write(40);  
  RF_DOWN.write(140);
  delay(200);
  LB_DOWN.write(50);  
  RF_DOWN.write(130);
  delay(200);
}

void slowBackWalk() {
 for (int i = 0; i < TOTAL_FRAMES; i++) {
    uint8_t h = pgm_read_byte(&hipAnglesBak[i]);
    uint8_t k = pgm_read_byte(&kneeAnglesBak[i]);

    LF_UP.write(180 - h);  
    LF_DOWN.write(k);  

    RB_UP.write(h);
    RB_DOWN.write(180 - k);

    delay(FRAME_DELAY);
  }

  delay(1000);

  for (int i = 0; i < TOTAL_FRAMES; i++) {
    uint8_t h = pgm_read_byte(&hipAnglesBak[i]);
    uint8_t k = pgm_read_byte(&kneeAnglesBak[i]);

    LB_UP.write(180 - h);  
    LB_DOWN.write(k);  

    RF_UP.write(h);
    RF_DOWN.write(180 - k);

    delay(FRAME_DELAY);
  }
}

// 键盘硬件参数
// KEYES 遥控器 NEC 协议按键码（32-bit）
const uint32_t KEY_0     = 0xAD52FF00;
const uint32_t KEY_1     = 0xE916FF00;
const uint32_t KEY_2     = 0xE619FF00;
const uint32_t KEY_3     = 0xF20DFF00;
const uint32_t KEY_4     = 0xF30CFF00;
const uint32_t KEY_5     = 0xE718FF00;
const uint32_t KEY_6     = 0xA15EFF00;
const uint32_t KEY_7     = 0xF708FF00;
const uint32_t KEY_8     = 0xE31CFF00;
const uint32_t KEY_9     = 0xA55AFF00;

const uint32_t KEY_STAR  = 0xFFB847;   // *
const uint32_t KEY_HASH  = 0xFF7A85;   // #

const uint32_t KEY_UP    = 0xB946FF00;
const uint32_t KEY_DOWN  = 0xEA15FF00;
const uint32_t KEY_LEFT  = 0xBB44FF00;
const uint32_t KEY_RIGHT = 0xBC43FF00;
const uint32_t KEY_OK    = 0xBF40FF00;

const uint32_t KEY_POWER = 0xFF6897;   // 电源键（部分套件有）
const uint32_t KEY_MODE  = 0xFF18E7;   // MODE 键（部分套件有）
const uint32_t KEY_MUTE  = 0xFF4AB5;   // 静音（较少见）
const uint32_t KEY_PLAY  = 0xFF58A7;   // ▶ 播放（部分版本）

int cnt = 0;

void loop() {
  // 发送 10μs 脉冲触发测距
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  // 读取回响时间（单位：微秒）
  long duration = pulseIn(ECHO_PIN, HIGH);

  // 计算距离（声速 340m/s = 0.034cm/μs → 距离 = 时间 / 2 * 0.034）
  float distance = duration * 0.034 / 2.0;

  Serial.print("Distance: ");
  Serial.print(distance);
  Serial.println(" cm");

  // 10 次 10 ～ 15cm 握手
  if (distance > 10 && distance < 15) {
    cnt++;
    if (cnt > 20) {
      lookUp();
      cnt = 0;
    }
  }

  delay(100); // 避免频繁测量（HC-SR04 最小周期约 60ms）

  if (IrReceiver.decode()) {
    // 获取解码后的数据
    uint32_t currentCode = IrReceiver.decodedIRData.decodedRawData;
    uint8_t protocol = IrReceiver.decodedIRData.protocol;

    // 忽略重复码（REPEAT）
    // if (protocol == UNKNOWN || protocol == UNUSED) {
    //   IrReceiver.resume();
    //   return;
    // }

    // 防抖逻辑：相同按键在 DEBOUNCE_DELAY 内只响应一次
    if (currentCode != lastCode || (millis() - lastTime) > DEBOUNCE_DELAY) {
      Serial.print("HEX: 0x");
      Serial.println(currentCode, HEX);
      // 这里做遥控器逻辑
      switch (currentCode) {
        case KEY_0:    { 
          Serial.println("按键: 0"); 
          sitDown();  
          break; 
        }
        case KEY_1:    { 
          Serial.println("按键: 1"); 
          SlowStandUp(); 
          break; 
        }
        case KEY_2:  {  
          Serial.println("按键: 2"); 
          lookUp();
          break;
        }
        case KEY_3:     Serial.println("按键: 3"); break;
        case KEY_4:     Serial.println("按键: 4"); break;
        case KEY_5:     Serial.println("按键: 5"); break;
        case KEY_6:     Serial.println("按键: 6"); break;
        case KEY_7:     Serial.println("按键: 7"); break;
        case KEY_8:     Serial.println("按键: 8"); break;
        case KEY_9:     Serial.println("按键: 9"); break;

        case KEY_STAR:  Serial.println("按键: *"); break;
        case KEY_HASH:  Serial.println("按键: #"); break;

        case KEY_UP:    {Serial.println("按键: ↑ (UP)"); slowBackWalk(); break;}
        case KEY_DOWN:  {Serial.println("按键: ↓ (DOWN)"); 
        // slowBackWalk(); 
        break;}
        case KEY_LEFT:  {Serial.println("按键: ← (LEFT)"); 
        // turnWalkLeft(); 
        break;}
        case KEY_RIGHT: {Serial.println("按键: → (RIGHT)"); 
        // turnWalkRight();
        break;}
        case KEY_OK:    Serial.println("按键: OK / SELECT"); break;

        case KEY_POWER: Serial.println("按键: 🔌 POWER"); break;
        case KEY_MODE:  Serial.println("按键: 🌀 MODE"); break;
        case KEY_MUTE:  Serial.println("按键: 🔇 MUTE"); break;
        case KEY_PLAY:  Serial.println("按键: ▶ PLAY"); break;

        default:
          Serial.print("未知按键 HEX: 0x");
          Serial.println(currentCode, HEX);
          break;
      }

      lastCode = currentCode;
      lastTime = millis();
    }

    IrReceiver.resume(); // 准备接收下一帧
  }

  // // 检查是否有来自蓝牙的数据
  // if (Serial1.available() > 0) {
  //   char receivedChar = Serial1.read(); // 读取一个字符
  //   Serial.print("收到蓝牙指令: ");
  //   Serial.println(receivedChar);

  //   // 根据收到的指令控制舵机角度
  //   switch (receivedChar) {
  //     case '1':
  //     {
  //       Serial1.println("sit down");
  //       sitDown();
  //       break;
  //     }
  //     case '0':
  //     {
  //       standUp();
  //       Serial1.println("stand up");
  //       break;
  //     }
  //     case '2':
  //     {
  //       slowWalk();
  //       Serial1.println("slow walk");
  //       break;
  //     }  
  //     case '3':
  //     {
  //       slowBackWalk();
  //       Serial1.println("slow back walk");
  //       break;
  //     }
  //     case '4':
  //     {
  //       turnWalkLeft();
  //       Serial1.println("turn walk left");
  //       break;
  //     }
  //     case '5':
  //     {
  //       turnWalkRight();
  //       Serial1.println("turn walk right");
  //       break;
  //     }
  //     default:
  //       Serial1.print("未知指令: ");
  //       Serial1.println(receivedChar);
  //       break;
  //   }
  // }

  // 心跳防断连
  if (millis() - lastPing > PING_INTERVAL) {
    Serial1.print("."); // 发一个点，不干扰解析
    lastPing = millis();
  }

  // // 将来自电脑的数据发送给蓝牙（可选，用于双向调试）
  // if (Serial.available() > 0) {
  //   char pcChar = Serial.read();
  //   Serial1.write(pcChar); // 将电脑输入的数据转发给蓝牙
  // }
}
