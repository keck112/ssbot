#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from tf2_ros import Buffer, TransformListener
import json
import os


class PoseSaver(Node):
    def __init__(self):
        super().__init__('pose_saver')

        self.declare_parameter('save_path', '/home/ss/maps/last_pose.json')
        self.declare_parameter('save_interval', 1.0)

        self.save_path = self.get_parameter('save_path').value
        self.save_interval = self.get_parameter('save_interval').value

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.timer = self.create_timer(self.save_interval, self.save_pose)
        self.get_logger().info(f'Pose saver started. Saving to {self.save_path}')

    def save_pose(self):
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
        except Exception as e:
            pass


def main(args=None):
    rclpy.init(args=args)
    node = PoseSaver()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
