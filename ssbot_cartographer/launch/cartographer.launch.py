import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg_dir = get_package_share_directory('ssbot_cartographer')
    config_dir = os.path.join(pkg_dir, 'config')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation (Gazebo) clock if true'
        ),

        # Cartographer node with dual LiDAR
        Node(
            package='cartographer_ros',
            executable='cartographer_node',
            name='cartographer_node',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time}],
            arguments=[
                '-configuration_directory', config_dir,
                '-configuration_basename', 'ssbot_2d.lua'
            ],
            remappings=[
                # Dual LiDAR: scan -> scan_1, scan_2 for Cartographer
                ('scan_1', '/scan_front'),
                ('scan_2', '/scan_rear'),
                ('odom', '/odom'),
                ('imu', '/imu'),
            ],
        ),

        # Occupancy grid node
        Node(
            package='cartographer_ros',
            executable='cartographer_occupancy_grid_node',
            name='cartographer_occupancy_grid_node',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time}],
            arguments=[
                '-resolution', '0.05',
                '-publish_period_sec', '1.0'
            ],
        ),
    ])
