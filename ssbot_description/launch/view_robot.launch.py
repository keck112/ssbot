import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    # Get package directory
    pkg_dir = get_package_share_directory('ssbot_description')

    # URDF file path
    urdf_file = os.path.join(pkg_dir, 'urdf', 'ssbot.urdf.xacro')
    rviz_config = os.path.join(pkg_dir, 'config', 'rviz.config.rviz')

    # Launch arguments
    use_gui = LaunchConfiguration('use_gui')

    declare_use_gui = DeclareLaunchArgument(
        'use_gui',
        default_value='true',
        description='Use joint_state_publisher_gui'
    )

    # Robot description
    robot_description = ParameterValue(
        Command(['xacro ', urdf_file]),
        value_type=str
    )

    # Robot State Publisher
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description}],
        output='screen'
    )

    # Joint State Publisher GUI
    joint_state_publisher_gui = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        output='screen'
    )

    # RViz
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', rviz_config],
        output='screen'
    )

    return LaunchDescription([
        declare_use_gui,
        robot_state_publisher,
        joint_state_publisher_gui,
        rviz,
    ])
