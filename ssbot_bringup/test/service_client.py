#!/usr/bin/env python3
"""
service_client.py
ROS2 Service 클라이언트 학습용
- 동기 호출: 응답 올 때까지 기다리기
- 비동기 호출: 응답 기다리지 않고 콜백으로 처리하기
"""

import rclpy
from rclpy.node import Node

# 사용할 서비스 타입 import
# 메시지와 동일한 규칙: 패키지명.srv 로 import
from std_srvs.srv import Empty           # 요청/응답 둘 다 비어있는 서비스


class ServiceClientNode(Node):

    def __init__(self):
        super().__init__('service_client_node')

        # ── 서비스 클라이언트 생성 ──
        # create_client(서비스타입, 서비스이름)
        self.clear_client = self.create_client(
            Empty,
            '/global_costmap/clear_entirely_global_costmap'
        )

        self.get_logger().info('ServiceClientNode 시작!')


    # ──────────────────────────────────────
    # 방법 1: 동기 호출 (응답 올 때까지 대기)
    # ──────────────────────────────────────

    def call_clear_costmap_sync(self):
        """
        코스트맵 초기화 서비스를 동기 방식으로 호출.
        응답이 올 때까지 블로킹(대기)함.
        C#의 일반 함수 호출과 동일한 느낌.
        """
        # 서비스 서버가 준비될 때까지 대기
        # timeout_sec 안에 서버가 안 뜨면 False 반환
        self.get_logger().info('서비스 서버 대기 중...')
        if not self.clear_client.wait_for_service(timeout_sec=3.0):
            self.get_logger().error('서비스 서버가 없습니다! Nav2 실행 중인지 확인하세요.')
            return False

        # 요청 메시지 생성
        # Empty 서비스는 요청/응답에 데이터가 없음
        request = Empty.Request()

        # 비동기로 요청 전송 → Future 객체 반환
        # Future = "나중에 결과가 담길 그릇"
        # C#의 Task<T> 와 동일한 개념
        self.get_logger().info('코스트맵 초기화 요청 전송...')
        future = self.clear_client.call_async(request)

        # Future가 완료될 때까지 spin으로 대기
        # (내부적으로 콜백을 처리하면서 응답을 기다림)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)

        # 결과 확인
        if future.done():
            self.get_logger().info('코스트맵 초기화 완료!')
            return True
        else:
            self.get_logger().error('서비스 응답 타임아웃')
            return False


    # ──────────────────────────────────────
    # 방법 2: 비동기 호출 (콜백으로 처리)
    # ──────────────────────────────────────

    def call_clear_costmap_async(self):
        """
        코스트맵 초기화 서비스를 비동기 방식으로 호출.
        응답을 기다리지 않고 즉시 반환.
        응답이 오면 콜백 함수가 자동으로 호출됨.
        C#의 async/await 와 동일한 개념.
        """
        if not self.clear_client.wait_for_service(timeout_sec=3.0):
            self.get_logger().error('서비스 서버가 없습니다!')
            return

        request = Empty.Request()
        future = self.clear_client.call_async(request)

        # 완료 시 호출할 콜백 등록
        # C#의 task.ContinueWith(callback) 과 동일
        future.add_done_callback(self._clear_done_callback)

        self.get_logger().info('코스트맵 초기화 요청 전송 (비동기)...')
        # 여기서 바로 반환 — 응답을 기다리지 않음


    def _clear_done_callback(self, future):
        """비동기 응답이 왔을 때 자동 호출되는 콜백."""
        try:
            response = future.result()
            self.get_logger().info('코스트맵 초기화 완료! (비동기 응답)')
        except Exception as e:
            self.get_logger().error(f'서비스 호출 실패: {e}')


# ──────────────────────────────────────────
# 메인 함수
# ──────────────────────────────────────────

def main(args=None):
    rclpy.init(args=args)
    node = ServiceClientNode()

    # ── 동기 방식 테스트 ──
    print('\n=== 동기 방식 호출 ===')
    node.call_clear_costmap_sync()

    # ── 비동기 방식 테스트 ──
    print('\n=== 비동기 방식 호출 ===')
    node.call_clear_costmap_async()

    # 비동기 콜백이 처리될 시간을 주기 위해 잠깐 spin
    import time
    time.sleep(1.0)
    rclpy.spin_once(node, timeout_sec=1.0)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
