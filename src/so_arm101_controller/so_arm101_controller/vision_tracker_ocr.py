import rclpy
from rclpy.node import Node

class VisionTrackerOCR(Node):
    def __init__(self):
        super().__init__('vision_tracker_ocr')
        self.get_logger().info('👁️ 책 인식 및 OCR(점자 변환) 비전 노드 가동 완료!')

def main(args=None):
    rclpy.init(args=args)
    node = VisionTrackerOCR()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
