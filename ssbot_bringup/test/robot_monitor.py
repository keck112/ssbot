#!/usr/bin/env python3
"""
robot_monitor.py
ROS2 Node 직접 작성 학습용
- Topic 구독: 로봇 위치(/odom), 레이저(/scan_front) 읽기
- Topic 발행: 속도 명령(/cmd_vel) 보내기
- Timer: 주기적으로 상태 출력
"""

import rclpy
from rclpy.node import Node

# 사용할 메시지 타입 import
from nav_msgs.msg import Odometry        # 로봇 위치/속도
from sensor_msgs.msg import LaserScan    # 라이다 데이터
from geometry_msgs.msg import Twist      # 속도 명령 (선속도 + 각속도)

# ──────────────────────────────────────────
# Node 클래스 정의
# ──────────────────────────────────────────
class RobotMonitor(Node):
    """"
    Node를 상속받아 만드는 커스텀 노드.\n
    C#의 클래스 상속과 동일한 개념.
    """
    
    def __init__(self):
        # 부모 클래스(Node) 초기화 — 노드 이름 지정
        # 이 이름이 "ros2 node list" 에서 보이는 이름
        super().__init__('robot_monitor')
        
        # ── 내부 상태 변수 ──
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_vx = 0.0    # 선속도
        self.current_wz = 0.0    # 각속도
        self.front_min_dist = 0.0  # 전방 최소 거리

        # ── 구독자(Subscriber) 생성 ──
        # create_subscription(메시지타입, 토픽이름, 콜백함수, QoS)
        # QoS 10 = 최대 10개 메시지를 버퍼에 보관
        self.odom_sub = self.create_subscription(
            Odometry,           # 메시지 타입
            '/odom',            # 토픽 이름
            self.odom_callback, # 데이터 올 때마다 호출할 함수
            10                  # QoS depth
        )

        self.scan_sub = self.create_subscription(
            LaserScan,
            '/scan_front',
            self.scan_callback,
            10
        )

        # ── 발행자(Publisher) 생성 ──
        # create_publisher(메시지타입, 토픽이름, QoS)
        self.cmd_pub = self.create_publisher(
            Twist,      # 메시지 타입
            '/cmd_vel', # 토픽 이름
            10          # QoS depth
        )

        # ── 타이머 생성 ──
        # 1.0초마다 print_status() 자동 호출
        self.timer = self.create_timer(1.0, self.print_status)

        self.get_logger().info('RobotMonitor 노드 시작!')


    # ──────────────────────────────────────
    # 콜백 함수들 — 데이터가 올 때마다 자동 호출
    # ──────────────────────────────────────

    def odom_callback(self, msg: Odometry):
        """
        /odom 토픽에서 데이터가 올 때마다 호출됨.
        msg 안에 위치, 방향, 속도 정보가 들어있음.
        """
        # 위치 추출
        self.current_x = msg.pose.pose.position.x
        self.current_y = msg.pose.pose.position.y

        # 속도 추출
        self.current_vx = msg.twist.twist.linear.x   # 전진 속도 (m/s)
        self.current_wz = msg.twist.twist.angular.z  # 회전 속도 (rad/s)


    def scan_callback(self, msg: LaserScan):
        """
        /scan_front 토픽에서 데이터가 올 때마다 호출됨.
        msg.ranges = 각도별 거리 측정값 리스트
        """
        # 유효한 거리값만 필터링 (inf, nan 제거)
        valid_ranges = [
            r for r in msg.ranges
            if msg.range_min < r < msg.range_max
        ]

        if valid_ranges:
            self.front_min_dist = min(valid_ranges)  # 가장 가까운 장애물 거리


    # ──────────────────────────────────────
    # 타이머 콜백 — 1초마다 자동 호출
    # ──────────────────────────────────────

    def print_status(self):
        """1초마다 현재 로봇 상태를 출력."""
        self.get_logger().info(
            f'위치: ({self.current_x:.2f}, {self.current_y:.2f}) | '
            f'속도: {self.current_vx:.2f} m/s | '
            f'전방 최소거리: {self.front_min_dist:.2f} m'
        )


    # ──────────────────────────────────────
    # 속도 명령 발행
    # ──────────────────────────────────────

    def send_velocity(self, linear_x: float, angular_z: float):
        """
        로봇에게 속도 명령을 보내는 함수.
        linear_x  = 전진/후진 속도 (m/s), 양수=전진, 음수=후진
        angular_z = 회전 속도 (rad/s), 양수=좌회전, 음수=우회전
        """
        msg = Twist()
        msg.linear.x = linear_x
        msg.angular.z = angular_z
        self.cmd_pub.publish(msg)  # 발행!

    def stop(self):
        """로봇 정지."""
        self.send_velocity(0.0, 0.0)


# ──────────────────────────────────────────
# 메인 함수
# ──────────────────────────────────────────

def main(args=None):
    rclpy.init(args=args)

    node = RobotMonitor()

    # rclpy.spin(node)
    # = 노드를 계속 살아있게 유지하면서
    #   콜백(odom_callback, scan_callback, print_status)이
    #   호출될 수 있도록 대기하는 루프
    # = C#의 Application.Run() 과 동일한 역할
    rclpy.spin(node)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
