import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg_bringup = get_package_share_directory('ssbot_bringup')
    params_dir = os.path.join(pkg_bringup, 'params')

    use_sim_time = LaunchConfiguration('use_sim_time', default='false')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation time'
        ),

        Node(
            package='sick_safetyscanners2',
            executable='sick_safetyscanners2_node',
            name='nanoscan3_front',
            output='screen',
            parameters=[
                os.path.join(params_dir, 'nanoscan3_front.yaml'),
                {'use_sim_time': use_sim_time}
            ],
            remappings=[('scan', '/scan_front')],
        ),

        Node(
            package='sick_safetyscanners2',
            executable='sick_safetyscanners2_node',
            name='nanoscan3_rear',
            output='screen',
            parameters=[
                os.path.join(params_dir, 'nanoscan3_rear.yaml'),
                {'use_sim_time': use_sim_time}
            ],
            remappings=[('scan', '/scan_rear')],
        ),
    ])
