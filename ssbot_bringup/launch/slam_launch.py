import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetParameter


def generate_launch_description():
    bringup_dir = get_package_share_directory('ssbot_bringup')

    use_sim_time = LaunchConfiguration('use_sim_time')
    use_respawn = LaunchConfiguration('use_respawn')
    log_level = LaunchConfiguration('log_level')

    stdout_linebuf_envvar = SetEnvironmentVariable('RCUTILS_LOGGING_BUFFERED_STREAM', '1')

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation (Gazebo) clock if true',
    )

    declare_use_respawn_cmd = DeclareLaunchArgument(
        'use_respawn',
        default_value='False',
        description='Respawn nodes on crash',
    )

    declare_log_level_cmd = DeclareLaunchArgument(
        'log_level',
        default_value='info',
        description='Log level',
    )

    load_nodes = GroupAction([
        SetParameter('use_sim_time', use_sim_time),
        Node(
            package='cartographer_ros',
            executable='cartographer_node',
            name='cartographer_node',
            output='screen',
            respawn=use_respawn,
            respawn_delay=2.0,
            arguments=[
                '-configuration_directory', os.path.join(bringup_dir, 'params'),
                '-configuration_basename', 'backpack_2d.lua',
                '--minloglevel=1',
                '-start_trajectory_with_default_topics=true',
            ],
            remappings=[
                ('scan_1', 'scan_front'),
                ('scan_2', 'scan_rear'),
                ('odom', '/odom'),
                ('imu', '/imu'),
            ],
        ),
        Node(
            package='cartographer_ros',
            executable='cartographer_occupancy_grid_node',
            name='cartographer_occupancy_grid_node',
            output='screen',
            respawn=use_respawn,
            respawn_delay=2.0,
            arguments=['-resolution', '0.05', '-publish_period_sec', '1.0'],
        ),
    ])

    ld = LaunchDescription()
    ld.add_action(stdout_linebuf_envvar)
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_use_respawn_cmd)
    ld.add_action(declare_log_level_cmd)
    ld.add_action(load_nodes)

    return ld
