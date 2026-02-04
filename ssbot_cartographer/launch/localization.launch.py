import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg_dir = get_package_share_directory('ssbot_cartographer')
    config_dir = os.path.join(pkg_dir, 'config')

    use_sim_time = LaunchConfiguration('use_sim_time')
    map_file = LaunchConfiguration('map_file')

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('map_file', default_value='/home/ss/maps/my_map.pbstream'),

        Node(
            package='cartographer_ros',
            executable='cartographer_node',
            name='cartographer_node',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time}],
            arguments=[
                '-configuration_directory', config_dir,
                '-configuration_basename', 'ssbot_2d_localization.lua',
                '-load_state_filename', map_file,
                '-start_trajectory_with_default_topics=false',
                '-collect_metrics',
            ],
            remappings=[
                ('scan', '/scan'),
                ('odom', '/odom'),
                ('imu', '/imu'),
            ],
        ),

        Node(
            package='cartographer_ros',
            executable='cartographer_occupancy_grid_node',
            name='cartographer_occupancy_grid_node',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time}],
            arguments=['-resolution', '0.05', '-publish_period_sec', '1.0'],
        ),

        TimerAction(
            period=3.0,
            actions=[
                Node(
                    package='ssbot_cartographer',
                    executable='trajectory_starter.py',
                    name='trajectory_starter',
                    output='screen',
                    parameters=[
                        {'use_sim_time': use_sim_time},
                        {'pose_file': '/home/ss/maps/last_pose.json'},
                        {'config_dir': config_dir},
                        {'config_basename': 'ssbot_2d_localization.lua'},
                    ],
                ),
            ],
        ),

        TimerAction(
            period=5.0,
            actions=[
                Node(
                    package='ssbot_cartographer',
                    executable='pose_saver.py',
                    name='pose_saver',
                    output='screen',
                    parameters=[
                        {'use_sim_time': use_sim_time},
                        {'save_path': '/home/ss/maps/last_pose.json'},
                        {'save_interval': 1.0},
                    ],
                ),
                Node(
                    package='ssbot_cartographer',
                    executable='localization_monitor.py',
                    name='localization_monitor',
                    output='screen',
                    parameters=[
                        {'use_sim_time': use_sim_time},
                        {'check_interval': 2.0},
                    ],
                ),
            ],
        ),
    ])
