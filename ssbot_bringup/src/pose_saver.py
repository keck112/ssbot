#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from tf2_ros import Buffer, TransformListener
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
import json
import os


class PoseSaver(Node):
    def __init__(self):
        super().__init__('pose_saver')

        self.declare_parameter('save_path', '')
        self.declare_parameter('save_interval', 1.0)

        self.save_path = self.get_parameter('save_path').value
        self.save_interval = self.get_parameter('save_interval').value

        self.enabled = False

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # trajectory_starter의 신호를 받을 때까지 저장 비활성화
        latched_qos = QoSProfile(
            depth=1,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE,
        )
        self.create_subscription(Bool, '/trajectory_started', self._on_trajectory_started, latched_qos)

        self.timer = self.create_timer(self.save_interval, self.save_pose)
        self.get_logger().info(f'Pose saver started (waiting for /trajectory_started). Save path: {self.save_path}')

    def _on_trajectory_started(self, msg: Bool):
        if msg.data and not self.enabled:
            self.enabled = True
            self.get_logger().info('Trajectory started signal received → pose saving enabled')

    def save_pose(self):
        if not self.enabled:
            return
        try:
            transform = self.tf_buffer.lookup_transform('map', 'base_link', rclpy.time.Time())
            pose_data = {
                'x': transform.transform.translation.x,
                'y': transform.transform.translation.y,
                'z': transform.transform.translation.z,
                'qx': transform.transform.rotation.x,
                'qy': transform.transform.rotation.y,
                'qz': transform.transform.rotation.z,
                'qw': transform.transform.rotation.w
            }
            os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
            with open(self.save_path, 'w') as f:
                json.dump(pose_data, f)
        except Exception:
            pass


def main(args=None):
    rclpy.init(args=args)
    node = PoseSaver()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
