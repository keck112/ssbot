#!/usr/bin/env python3
"""
waypoint_navigator.py
A → B → C 순서로 웨이포인트를 순회하는 단순 주행 예제
"""

import rclpy
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from geometry_msgs.msg import PoseStamped
from rclpy.duration import Duration


# ─────────────────────────────────────────────
# 유틸: PoseStamped 메시지를 쉽게 만드는 함수
# ─────────────────────────────────────────────
def make_pose(navigator, x, y, yaw_z=0.0, yaw_w=1.0):
    """
    x, y 좌표와 방향(yaw)을 받아서 PoseStamped 메시지를 반환한다.

    yaw_z, yaw_w 는 쿼터니언(quaternion)의 z, w 성분.
    - 정면(0도): yaw_z=0.0, yaw_w=1.0
    - 90도(왼쪽): yaw_z=0.707, yaw_w=0.707
    - 180도(뒤): yaw_z=1.0, yaw_w=0.0
    """
    pose = PoseStamped()
    pose.header.frame_id = 'world'          # 좌표계: 맵 기준
    pose.header.stamp = navigator.get_clock().now().to_msg()  # 현재 시간 찍기

    pose.pose.position.x = x
    pose.pose.position.y = y
    pose.pose.position.z = 0.0            # 2D 주행이므로 항상 0

    pose.pose.orientation.z = yaw_z      # 방향 (쿼터니언)
    pose.pose.orientation.w = yaw_w

    return pose


# ─────────────────────────────────────────────
# 메인 함수
# ─────────────────────────────────────────────
def main():
    # 1. ROS2 초기화 — 반드시 가장 먼저 호출
    rclpy.init()

    # 2. BasicNavigator 생성 — Nav2와 통신하는 핵심 객체
    navigator = BasicNavigator()

    # 3. Nav2가 완전히 준비될 때까지 대기
    #    (Costmap, Planner, Controller 등이 모두 뜰 때까지)
    #navigator.waitUntilNav2Active()
    print('Nav2 준비 완료!')

    # 4. 웨이포인트 목록 정의 (A → B → C)
    #    좌표는 RViz에서 "Publish Point"로 확인 가능
    waypoints = [
        make_pose(navigator, x=20.0, y=14.0),   # A 지점
        make_pose(navigator, x=20.0, y=18.0),   # B 지점
        make_pose(navigator, x=25.0, y=18.0),   # C 지점
    ]

    # 5. 웨이포인트 순회 시작
    #    내부적으로 각 지점에 순서대로 navigate_to_pose 액션을 보냄
    print('웨이포인트 주행 시작: A → B → C')
    navigator.followWaypoints(waypoints)

    # 6. 주행 완료까지 대기 루프
    #    isTaskComplete()가 True가 될 때까지 반복
    while not navigator.isTaskComplete():

        # 현재 진행 상황 (몇 번째 웨이포인트인지)
        feedback = navigator.getFeedback()
        current_wp = feedback.current_waypoint
        total_wp = len(waypoints)
        print(f'진행 중: {current_wp + 1} / {total_wp} 번째 웨이포인트')

    # 7. 결과 확인
    result = navigator.getResult()

    if result == TaskResult.SUCCEEDED:
        print('✓ 주행 성공! 모든 웨이포인트 도달 완료')
    elif result == TaskResult.CANCELED:
        print('✗ 주행 취소됨')
    elif result == TaskResult.FAILED:
        print('✗ 주행 실패')
    else:
        print(f'? 알 수 없는 결과: {result}')

    # 8. 종료
    #navigator.lifecycleShutdown()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
