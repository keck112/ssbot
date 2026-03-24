#!/usr/bin/env python3
"""
action_client.py
BasicNavigator 없이 navigate_to_pose Action을 직접 다루는 예제

Action 3단계 구조:
  1) send_goal_async()          → goal_future    : 서버가 goal 수락/거부
  2) goal_handle.get_result_async() → result_future : 주행 완료/실패
  3) feedback_callback()            : 주행 중 현재 위치를 계속 받음
"""

import rclpy
import tf2_ros
import tf2_geometry_msgs
from rclpy.node import Node
from rclpy.action import ActionClient

from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped


# ─────────────────────────────────────────────
# 유틸: PoseStamped 메시지 생성
# ─────────────────────────────────────────────
def make_pose(node, x, y, yaw_z=0.0, yaw_w=1.0):
    pose = PoseStamped()
    pose.header.frame_id = 'world'
    pose.header.stamp = node.get_clock().now().to_msg()
    pose.pose.position.x = x
    pose.pose.position.y = y
    pose.pose.position.z = 0.0
    pose.pose.orientation.z = yaw_z
    pose.pose.orientation.w = yaw_w
    return pose


# ─────────────────────────────────────────────
# Action Client 노드
# ─────────────────────────────────────────────
class NavActionClient(Node):

    def __init__(self):
        super().__init__('nav_action_client')

        # ActionClient 생성
        # - 인자1: 노드 자신 (self)
        # - 인자2: Action 타입 (NavigateToPose)
        # - 인자3: Action 서버 이름 ('/navigate_to_pose')
        self._action_client = ActionClient(self, NavigateToPose, '/navigate_to_pose')
        self._tf_buffer = tf2_ros.Buffer()
        self._tf_listener = tf2_ros.TransformListener(self._tf_buffer, self)
        

    # ── 1단계: Goal 전송 ──────────────────────────
    def send_goal(self, x, y):
        # Action 서버가 뜰 때까지 대기
        self.get_logger().info('Action 서버 대기 중...')
        self._action_client.wait_for_server()
        self.get_logger().info('Action 서버 연결됨!')

        # Goal 메시지 구성
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = make_pose(self, x, y)

        self.get_logger().info(f'Goal 전송: x={x}, y={y}')

        # send_goal_async(): Goal을 보내고 즉시 goal_future 반환 (논블로킹)
        # feedback_callback: 주행 중 주기적으로 호출될 콜백 등록
        goal_future = self._action_client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback   # 3단계 콜백 등록
        )

        # goal_future 완료 시 → goal_response_callback 호출
        goal_future.add_done_callback(self.goal_response_callback)

    # ── 1단계 완료 콜백: 서버가 goal 수락/거부 응답 ──
    def goal_response_callback(self, future):
        goal_handle = future.result()
        
        if not goal_handle.accepted:
            # 서버가 goal을 거부한 경우 (경로 없음 등)
            self.get_logger().error('Goal 거부됨!')
            return

        self.get_logger().info('Goal 수락됨! 주행 시작...')

        # ── 2단계: Result 요청 ──────────────────────
        # get_result_async(): 주행 완료까지 기다리는 result_future 반환
        result_future = goal_handle.get_result_async()

        # result_future 완료 시 → result_callback 호출
        result_future.add_done_callback(self.result_callback)

    # ── 2단계 완료 콜백: 주행 최종 결과 ─────────────
    def result_callback(self, future):
        result = future.result()

        # status 값: 4 = SUCCEEDED, 5 = CANCELED, 6 = ABORTED
        status = result.status

        if status == 4:
            self.get_logger().info('주행 성공!')
        elif status == 5:
            self.get_logger().warn('주행 취소됨')
        else:
            self.get_logger().error(f'주행 실패 (status={status})')

        # 완료 후 spin 종료
        rclpy.shutdown()

    # ── 3단계 콜백: 주행 중 피드백 (반복 호출) ───────
    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback
        
        try:
            pose_in_map = self._tf_buffer.transform(
                feedback.current_pose,
                'world'
            )
            
            # 현재 위치 출력
            pos = pose_in_map.pose
            dist = feedback.distance_remaining

            self.get_logger().info(
                f'현재 위치: ({pos.position.x:.2f}, {pos.position.y:.2f}, {pos.orientation.z:.2f}) | 남은 거리: {dist:.2f}m'
            )
        except Exception as e:
            self.get_logger().error(f'TF 변환 실패: {e}')


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────
def main():
    rclpy.init()

    node = NavActionClient()

    # Goal 전송 (좌표는 환경에 맞게 수정)
    node.send_goal(x=25.0, y=19.0)

    # spin(): executor가 이벤트 루프를 돌며 콜백들을 처리
    # result_callback에서 rclpy.shutdown()이 호출되면 자동 종료
    rclpy.spin(node)


if __name__ == '__main__':
    main()
