import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
import serial
import time

class HighPerformanceArmNode(Node):
    def __init__(self):
        super().__init__('arm_node')
        
        self.ser = None
        self.port_name = '/dev/ttyACM0'
        self.baud_rate = 1000000
        
        # 💡 노드 시작 시 최초 연결 시도
        self.connect_serial()

        # 비전 트래커로부터 명령을 받는 구독자
        self.sub = self.create_subscription(JointState, 'joint_commands', self.listener_callback, 10)

    def connect_serial(self):
        """시리얼 포트를 (재)연결하는 안전 함수"""
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.ser = serial.Serial(self.port_name, self.baud_rate, timeout=0.1)
            self.get_logger().info('🚀 부드러운 구동 모드: 시리얼 통신 연결 완료 (1Mbps)')
        except Exception as e:
            self.get_logger().error(f'❌ 포트 연결 실패 (다음 명령 수신 시 재시도): {e}')

    def listener_callback(self, msg):
        # 💡 연결이 끊겨있다면 재연결 시도
        if self.ser is None or not self.ser.is_open:
            self.get_logger().warning('⚠️ 시리얼 포트 단절 감지! 재연결을 시도합니다...')
            self.connect_serial()
            if not self.ser.is_open:
                return # 여전히 안 열리면 이번 명령은 스킵

        try:
            for i, pos in enumerate(msg.position):
                if i >= 6: break
                
                motor_id = i + 1
                p = int(round(pos))
                p = max(0, min(4095, p)) # 하드웨어 파손 방지 가드
                
                # 💡 안정화 업데이트: 하드웨어 모터의 속도와 가속도를 대폭 낮춤
                # 가속도: 40 (0x28, 0x00), 최대 속도: 150 (0x96, 0x00) -> 묵직하고 우아하게 움직임
                packet = [0xFF, 0xFF, motor_id, 0x09, 0x03, 0x2A, 
                          p & 0xFF, (p >> 8) & 0xFF, 0x28, 0x00, 0x96, 0x00]
                
                chk = ~(sum(packet[2:]) & 0xFF) & 0xFF
                packet.append(chk)
                
                self.ser.write(bytearray(packet))
                time.sleep(0.001) 
                
        except serial.SerialException as e:
            # 💡 통신 중 케이블 흔들림 등으로 에러 발생 시 노드가 죽지 않도록 방어
            self.get_logger().error(f'🔥 시리얼 통신 에러 발생! 케이블 상태를 확인하세요: {e}')
            if self.ser:
                self.ser.close() # 안전하게 닫아두어 다음 callback에서 connect_serial()이 호출되게 유도
        except Exception as e:
            self.get_logger().error(f'❌ 모터 제어 중 알 수 없는 에러: {e}')

def main(args=None):
    rclpy.init(args=args)
    node = HighPerformanceArmNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node.ser and node.ser.is_open:
            node.ser.close()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()