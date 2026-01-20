import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    # Get package directories
    bringup_dir = get_package_share_directory('ssbot_bringup')
    description_dir = get_package_share_directory('ssbot_description')

    # Include robot description launch
    robot_description_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(description_dir, 'launch', 'description.launch.py')
        )
    )

    return LaunchDescription([
        robot_description_launch,
    ])
