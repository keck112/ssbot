import os
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    # Use source directory directly for live editing
    rviz_config = os.path.expanduser(
        '~/ssbot_ws/src/ssbot/ssbot_description/rviz/gazebo_view.rviz'
    )

    return LaunchDescription([
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', rviz_config],
            parameters=[{'use_sim_time': True}],
            output='screen'
        ),
    ])
