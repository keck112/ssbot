#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from cartographer_ros_msgs.srv import StartTrajectory
from geometry_msgs.msg import Pose
import json
import os


class TrajectoryStarter(Node):
    def __init__(self):
        super().__init__('trajectory_starter')

        self.declare_parameter('pose_file', '/home/ss/maps/last_pose.json')
        self.declare_parameter('config_dir', '/home/ss/ssbot_ws/install/ssbot_cartographer/share/ssbot_cartographer/config')
        self.declare_parameter('config_basename', 'ssbot_2d_localization.lua')

        self.pose_file = self.get_parameter('pose_file').value
        self.config_dir = self.get_parameter('config_dir').value
        self.config_basename = self.get_parameter('config_basename').value

        self.client = self.create_client(StartTrajectory, '/start_trajectory')
        self.timer = self.create_timer(2.0, self.start_trajectory)

    def start_trajectory(self):
        self.timer.cancel()

        if not self.client.wait_for_service(timeout_sec=5.0):
            self.get_logger().error('start_trajectory service not available')
            return

        pose = self.load_pose()
        request = StartTrajectory.Request()
        request.configuration_directory = self.config_dir
        request.configuration_basename = self.config_basename
        request.use_initial_pose = True
        request.initial_pose = pose
        request.relative_to_trajectory_id = 0

        future = self.client.call_async(request)
        future.add_done_callback(self.callback)

    def load_pose(self):
        pose = Pose()
        pose.position.x = 0.0
        pose.position.y = 0.0
        pose.position.z = 0.0
        pose.orientation.x = 0.0
        pose.orientation.y = 0.0
        pose.orientation.z = 0.0
        pose.orientation.w = 1.0

        if os.path.exists(self.pose_file):
            try:
                with open(self.pose_file, 'r') as f:
                    data = json.load(f)
                pose.position.x = data.get('x', 0.0)
                pose.position.y = data.get('y', 0.0)
                pose.position.z = data.get('z', 0.0)
                pose.orientation.x = data.get('qx', 0.0)
                pose.orientation.y = data.get('qy', 0.0)
                pose.orientation.z = data.get('qz', 0.0)
                pose.orientation.w = data.get('qw', 1.0)
                self.get_logger().info(f'Loaded pose: x={pose.position.x:.2f}, y={pose.position.y:.2f}')
            except Exception as e:
                self.get_logger().warn(f'Failed to load pose: {e}')
        else:
            self.get_logger().info('No saved pose found, using origin')

        return pose

    def callback(self, future):
        try:
            response = future.result()
            self.get_logger().info(f'Trajectory started with ID: {response.trajectory_id}')
        except Exception as e:
            self.get_logger().error(f'Failed to start trajectory: {e}')
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = TrajectoryStarter()
    rclpy.spin(node)
    node.destroy_node()


if __name__ == '__main__':
    main()
