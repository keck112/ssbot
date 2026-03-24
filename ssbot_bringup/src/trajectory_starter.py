#!/usr/bin/env python3
import time
import json
import os

import rclpy
from cartographer_ros_msgs.srv import StartTrajectory, FinishTrajectory
from geometry_msgs.msg import Pose
from std_msgs.msg import Bool
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy


def main(args=None):
    rclpy.init(args=args)
    node = rclpy.create_node('trajectory_starter')

    node.declare_parameter('pose_file', '')
    node.declare_parameter('config_dir', '')
    node.declare_parameter('config_basename', '')

    pose_file = node.get_parameter('pose_file').value
    config_dir = node.get_parameter('config_dir').value
    config_basename = node.get_parameter('config_basename').value

    start_client = node.create_client(StartTrajectory, '/start_trajectory')
    finish_client = node.create_client(FinishTrajectory, '/finish_trajectory')

    # pose_saver에게 시작 신호를 보낼 퍼블리셔 (latched — 나중에 구독해도 수신됨)
    latched_qos = QoSProfile(
        depth=1,
        durability=DurabilityPolicy.TRANSIENT_LOCAL,
        reliability=ReliabilityPolicy.RELIABLE,
    )
    ready_pub = node.create_publisher(Bool, '/trajectory_started', latched_qos)

    # pose 파일을 가장 먼저 읽음 — pose_saver가 덮어쓰기 전에 메모리에 보존
    pose = Pose()
    pose.orientation.w = 1.0
    if os.path.exists(pose_file):
        try:
            with open(pose_file, 'r') as f:
                data = json.load(f)
            pose.position.x = data.get('x', 0.0)
            pose.position.y = data.get('y', 0.0)
            pose.position.z = data.get('z', 0.0)
            pose.orientation.x = data.get('qx', 0.0)
            pose.orientation.y = data.get('qy', 0.0)
            pose.orientation.z = data.get('qz', 0.0)
            pose.orientation.w = data.get('qw', 1.0)
            node.get_logger().info(
                f'Loaded pose: x={pose.position.x:.2f}, y={pose.position.y:.2f}')
        except Exception as e:
            node.get_logger().warn(f'Failed to load pose: {e}')
    else:
        node.get_logger().info('No saved pose found, using origin')

    # 실제 시간(wall time) 기준으로 5초 대기 — use_sim_time 영향 없음
    node.get_logger().info('Waiting 5s for Cartographer to initialize...')
    time.sleep(5.0)

    # start_trajectory 서비스 대기
    if not start_client.wait_for_service(timeout_sec=5.0):
        node.get_logger().error('start_trajectory service not available')
        node.destroy_node()
        rclpy.shutdown()
        return

    # pbstream 로드 시 복원된 active trajectory 정리
    if finish_client.wait_for_service(timeout_sec=3.0):
        for traj_id in range(1, 10):
            req = FinishTrajectory.Request()
            req.trajectory_id = traj_id
            future = finish_client.call_async(req)
            rclpy.spin_until_future_complete(node, future, timeout_sec=3.0)
            if future.done() and future.result().status.code == 0:
                node.get_logger().info(f'Finished existing trajectory {traj_id}')
            else:
                break
    else:
        node.get_logger().warn('finish_trajectory service not available, skipping cleanup')

    # 새 trajectory 시작 (저장된 pose 기준)
    request = StartTrajectory.Request()
    request.configuration_directory = config_dir
    request.configuration_basename = config_basename
    request.use_initial_pose = True
    request.initial_pose = pose
    request.relative_to_trajectory_id = 0

    future = start_client.call_async(request)
    rclpy.spin_until_future_complete(node, future, timeout_sec=10.0)

    if future.done():
        response = future.result()
        if response.status.code == 0:
            node.get_logger().info(f'Trajectory started: ID={response.trajectory_id}')
            ready_pub.publish(Bool(data=True))
            node.get_logger().info('Published /trajectory_started → pose_saver enabled')
        else:
            node.get_logger().error(
                f'start_trajectory failed: {response.status.message}')
    else:
        node.get_logger().error('Timeout waiting for start_trajectory response')

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
