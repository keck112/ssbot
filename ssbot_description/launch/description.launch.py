import os
from launch import LaunchDescription
from launch.substitutions import Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    # Get package directory
    pkg_dir = get_package_share_directory('ssbot_description')

    # URDF file path
    urdf_file = os.path.join(pkg_dir, 'urdf', 'ssbot.urdf.xacro')

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

    # Joint State Publisher GUI (for testing)
#    joint_state_publisher_gui = Node(
#        package='joint_state_publisher_gui',
#        executable='joint_state_publisher_gui',
#        output='screen'
#   )

    return LaunchDescription([
        robot_state_publisher,
#        joint_state_publisher_gui,
    ])
