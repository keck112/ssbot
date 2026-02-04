#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from cartographer_ros_msgs.srv import ReadMetrics
from std_msgs.msg import Float32, String
import json


class LocalizationMonitor(Node):
    def __init__(self):
        super().__init__('localization_monitor')

        self.declare_parameter('check_interval', 2.0)
        self.check_interval = self.get_parameter('check_interval').value

        self.client = self.create_client(ReadMetrics, '/read_metrics')
        self.quality_pub = self.create_publisher(Float32, '/localization_quality', 10)
        self.status_pub = self.create_publisher(String, '/localization_status', 10)

        self.timer = self.create_timer(self.check_interval, self.check_metrics)
        self.get_logger().info('Localization monitor started')

    def check_metrics(self):
        if not self.client.service_is_ready():
            return

        request = ReadMetrics.Request()
        future = self.client.call_async(request)
        future.add_done_callback(self.process_metrics)

    def process_metrics(self, future):
        try:
            response = future.result()
            if response.status.code != 0:
                return

            local_searched = 0
            local_found = 0
            real_time_ratio = 0.0

            for family in response.metric_families:
                if family.name == 'mapping_constraints_constraint_builder_2d_constraints':
                    for m in family.metrics:
                        labels = {l.key: l.value for l in m.labels}
                        if labels.get('search_region') == 'local':
                            if labels.get('matcher') == 'searched':
                                local_searched = m.value
                            elif labels.get('matcher') == 'found':
                                local_found = m.value

                elif family.name == 'mapping_2d_local_trajectory_builder_real_time_ratio':
                    if family.metrics:
                        real_time_ratio = family.metrics[0].value

            if local_searched > 0:
                quality = local_found / local_searched
            else:
                quality = 1.0

            quality_msg = Float32()
            quality_msg.data = float(quality)
            self.quality_pub.publish(quality_msg)

            if quality >= 0.9:
                status = "GOOD"
            elif quality >= 0.7:
                status = "MODERATE"
            else:
                status = "POOR"

            status_msg = String()
            status_msg.data = json.dumps({
                'status': status,
                'quality': round(quality, 3),
                'local_found': int(local_found),
                'local_searched': int(local_searched),
                'real_time_ratio': round(real_time_ratio, 3),
            })
            self.status_pub.publish(status_msg)

            self.get_logger().info(f'Localization: {status} (quality={quality:.2f}, matched={int(local_found)}/{int(local_searched)}, rt={real_time_ratio:.2f})')

        except Exception as e:
            self.get_logger().warn(f'Failed to process metrics: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = LocalizationMonitor()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
