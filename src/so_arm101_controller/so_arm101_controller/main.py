import os
import time
import math
import logging
import threading
from pathlib import Path

import cv2
import numpy as np
from flask import Flask, Response

# ROS 2 및 메시지 포맷 임포트
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 패키지 명을 포함한 올바른 임포트 경로
from so_arm101_controller.ocr_module import OCRModule

try:
    from so_arm101_controller.braille_module import text_to_braille_pins
except ImportError:
    logger.error("❌ braille_module을 찾을 수 없습니다. 파일 위치를 확인하세요.")
    raise

MODEL_PATH = os.environ.get('MODEL_PATH', '/home/robot/runs/detect/train-5/weights/best.pt')
OUTPUT_DIR = Path(os.environ.get('OCR_OUTPUT_DIR', 'ocr_captures_tracking'))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
current_frame = None 

def generate_frames():
    global current_frame
    while True:
        if current_frame is None:
            time.sleep(0.1)
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + current_frame + b'\r\n')
        time.sleep(0.05) 

@app.route('/')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)


class VisionTrackerNode(Node):
    def __init__(self):
        super().__init__('vision_tracker')
        
        self.pub = self.create_publisher(JointState, 'joint_commands', 10)
        self.timer = self.create_timer(0.1, self.track_book)
        
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        if not self.cap.isOpened():
            self.get_logger().error("❌ 카메라를 열 수 없습니다.")
            return

        self.get_logger().info('🧠 맞춤형 학습 모델 및 고도화 OCR 모듈 로드 중...')
        try:
            from ultralytics import YOLO
            self.model = YOLO(MODEL_PATH) 
        except Exception as e:
            self.get_logger().error(f"YOLO 모델 로드 실패: {e}")
            raise

        self.ocr = OCRModule()

        self.positions = [2048.0, 1500.0, 2500.0, 2048.0, 2048.0, 2048.0]
        self.target_positions = list(self.positions)
        
        # 💡 오버슈팅 방지를 위한 제어 파라미터 튜닝 (매우 부드러운 이동)
        self.Kp_x = 0.05    
        self.Kp_y = 0.05    
        
        self.deadzone = 40  # 정착하기 쉽도록 데드존 확장
        self.alpha = 0.15   # Low-pass Filter 강도를 높여 모터 부들거림 억제
        self.startup_counter = 0 
        
        self.prev_cx, self.prev_cy = None, None
        self.stationary_threshold = 4.0
        self.ocr_idx = 0

        self.get_logger().info('🌐 AI 추적 및 순수 점자 데이터 스트림 생성 준비 완료!')

    def track_book(self):
        global current_frame
        ret, frame = self.cap.read()
        if not ret: 
            return

        if self.startup_counter < 20:
            msg = JointState()
            msg.header.stamp = self.get_clock().now().to_msg() 
            msg.name = ['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'joint6']
            msg.position = self.positions
            self.pub.publish(msg)
            
            if self.startup_counter == 0:
                self.get_logger().info("🦾 즉시 로봇 팔을 시야 확보 자세로 뻗습니다!")
                
            self.startup_counter += 1
            
            cv2.putText(frame, "INITIALIZING ARM...", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret: current_frame = buffer.tobytes()
            return 

        if self.startup_counter == 20:
            self.get_logger().info("👀 팔 펴기 완료! 본격적으로 책(Book) 탐색 및 정지 기반 OCR을 시작합니다.")
            self.startup_counter += 1

        results = self.model.predict(source=frame, conf=0.45, verbose=False)

        best_box = None
        max_area = 0

        for box in results[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            area = (x2 - x1) * (y2 - y1)
            if area > max_area:
                max_area = area
                best_box = (x1, y1, x2, y2)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 1)

        if best_box:
            x1, y1, x2, y2 = best_box
            cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
            
            error_x = 640 - cx
            error_y = 360 - cy
            
            is_stationary = False
            if self.prev_cx is not None and self.prev_cy is not None:
                move_distance = math.sqrt((cx - self.prev_cx) ** 2 + (cy - self.prev_cy) ** 2)
                if move_distance < self.stationary_threshold and abs(error_x) <= self.deadzone + 10:
                    is_stationary = True
            
            self.prev_cx, self.prev_cy = cx, cy

            if abs(error_x) > self.deadzone:
                self.target_positions[0] -= (error_x * self.Kp_x) 
            if abs(error_y) > self.deadzone:
                self.target_positions[2] -= (error_y * self.Kp_y) 
            
            self.target_positions = [max(0.0, min(4095.0, float(p))) for p in self.target_positions]
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), 3)
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)

            if is_stationary:
                cv2.putText(frame, "STATUS: STATIONARY (OCR ACTIVE)", (10, 60), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                self.get_logger().info("✅ 정지 확정! OCR 스캔 실행 중...")
                
                # 오류 방지용 빈 리스트 변수 안전망
                texts = [] 
                
                try:
                    texts = self.ocr.ocr_from_image(frame, bbox=(x1, y1, x2, y2), pad=12)
                except Exception as e:
                    self.get_logger().error(f"OCR 추론 엔진 구동 실패: {e}")

                ts = time.strftime('%Y%m%d_%H%M%S')
                img_name = f'preprocess_track_{ts}_{self.ocr_idx}.jpg'
                txt_name = f'track_{ts}_{self.ocr_idx}_single.txt'
                braille_txt_name = f'track_{ts}_{self.ocr_idx}_braille.txt'

                combined_text = ""
                try:
                    h, w = frame.shape[:2]
                    px1, py1 = max(0, x1 - 12), max(0, y1 - 12)
                    px2, py2 = min(w - 1, x2 + 12), min(h - 1, y2 + 12)
                    roi = frame[py1:py2, px1:px2]
                    
                    # 로깅용으로 원본 크롭만 저장 (OCR 내부에서 자체 전처리함)
                    cv2.imwrite(str(OUTPUT_DIR / img_name), roi)
                    
                    combined_text = ' '.join([t['text'] for t in texts]) if texts else '[No OCR text detected]'
                    (OUTPUT_DIR / txt_name).write_text(combined_text, encoding='utf-8')
                except Exception as e:
                    self.get_logger().error(f"디버깅용 데이터 쓰기 에러: {e}")

                if combined_text and combined_text != '[No OCR text detected]':
                    try:
                        braille_data = text_to_braille_pins(combined_text)
                        braille_only_lines = [str(item['pins']) for item in braille_data]
                        braille_content = "\n".join(braille_only_lines)
                        
                        (OUTPUT_DIR / braille_txt_name).write_text(braille_content, encoding='utf-8')
                        self.get_logger().info(f"💾 순수 점자 핀 스트림 파일 저장 완료: {braille_txt_name}")
                    except Exception as e:
                        self.get_logger().error(f"점자 하드웨어 데이터 직렬화 실패: {e}")

                overlay = ' | '.join([t['text'] for t in texts])[:300]
                cv2.putText(frame, f"OCR: {overlay}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                self.ocr_idx += 1
            else:
                cv2.putText(frame, "STATUS: MOVING TO TARGET...", (10, 60), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        else:
            self.prev_cx, self.prev_cy = None, None
            cv2.putText(frame, "STATUS: SEARCHING BOOK...", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        for i in range(6):
            self.positions[i] = (self.alpha * self.target_positions[i]) + ((1 - self.alpha) * self.positions[i])

        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg() 
        msg.name = ['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'joint6']
        msg.position = self.positions
        self.pub.publish(msg)

        cv2.rectangle(frame, (640 - self.deadzone, 360 - self.deadzone), 
                             (640 + self.deadzone, 360 + self.deadzone), (255, 0, 0), 2)
        cv2.line(frame, (630, 360), (650, 360), (255, 0, 0), 2)
        cv2.line(frame, (640, 350), (640, 370), (255, 0, 0), 2)
        
        ret, buffer = cv2.imencode('.jpg', frame)
        if ret:
            current_frame = buffer.tobytes()


def main(args=None):
    rclpy.init(args=args)
    node = VisionTrackerNode()
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.cap.release()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()