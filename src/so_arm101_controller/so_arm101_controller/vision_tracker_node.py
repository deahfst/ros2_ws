import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
import cv2
import threading
import time
from flask import Flask, Response
from ultralytics import YOLO

# Flask 웹 스트리밍 설정
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
        
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        if not self.cap.isOpened():
            self.get_logger().error("❌ 카메라를 열 수 없습니다.")
            return

        self.get_logger().info('🧠 맞춤형 학습 모델 로드 중...')
        # 살아남은 최고 성능 모델 경로!
        self.model = YOLO('/home/robot/runs/detect/train-5/weights/best.pt') 

        self.positions = [2048.0, 1500.0, 2500.0, 2048.0, 2048.0, 2048.0]
        self.target_positions = list(self.positions)
        
        self.Kp_x = 0.15 
        self.Kp_y = 0.15
        
        self.deadzone = 30  
        self.alpha = 0.4    
        self.startup_counter = 0 
        
        self.timer = self.create_timer(0.1, self.track_book)
        self.get_logger().info('🌐 AI 추적 가동 준비! (http://192.168.0.2:5000)')

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
            self.get_logger().info("👀 팔 펴기 완료! 본격적으로 책(Book) 탐색을 시작합니다.")
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
            
            error_x = 320 - cx
            error_y = 240 - cy
            
            if abs(error_x) > self.deadzone:
                self.target_positions[0] -= (error_x * self.Kp_x) 
            if abs(error_y) > self.deadzone:
                self.target_positions[2] -= (error_y * self.Kp_y) 
            
            self.target_positions = [max(0.0, min(4095.0, float(p))) for p in self.target_positions]
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), 3)
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
            cv2.putText(frame, f"TRACKING (X:{error_x}, Y:{error_y})", (x1, y1-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)

        for i in range(6):
            self.positions[i] = (self.alpha * self.target_positions[i]) + ((1 - self.alpha) * self.positions[i])

        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg() 
        msg.name = ['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'joint6']
        msg.position = self.positions
        self.pub.publish(msg)

        cv2.rectangle(frame, (320 - self.deadzone, 240 - self.deadzone), 
                             (320 + self.deadzone, 240 + self.deadzone), (255, 0, 0), 2)
        cv2.line(frame, (310, 240), (330, 240), (255, 0, 0), 2)
        cv2.line(frame, (320, 230), (320, 250), (255, 0, 0), 2)
        
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