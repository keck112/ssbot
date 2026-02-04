import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node, ComposableNodeContainer
from launch_ros.descriptions import ComposableNode
from launch_ros.parameter_descriptions import ParameterValue
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    # Get package directories
    pkg_description = get_package_share_directory('ssbot_description')
    pkg_bringup = get_package_share_directory('ssbot_bringup')

    # URDF file path
    urdf_file = os.path.join(pkg_description, 'urdf', 'ssbot.urdf.xacro')

    # Launch arguments
    world = LaunchConfiguration('world')

    # World file path
    default_world = os.path.join(pkg_bringup, 'worlds', 'slam_test.sdf')

    declare_world = DeclareLaunchArgument(
        'world',
        default_value=default_world,
        description='Gazebo world file'
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

    # Gazebo Sim
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
        ]),
        launch_arguments={'gz_args': ['-r ', world]}.items()
    )

    # Spawn robot
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'ssbot',
            '-topic', '/robot_description',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.1'
        ],
        output='screen'
    )

    # Bridge config file
    bridge_config = os.path.join(pkg_bringup, 'config', 'ros_gz_bridge.yaml')

    # Bridge for ROS2 <-> Gazebo communication
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['--ros-args', '-p', f'config_file:={bridge_config}'],
        output='screen'
    )

    # Dual Laser Merger - merge front and rear LiDAR scans
    laser_merger = ComposableNodeContainer(
        name='laser_merger_container',
        namespace='',
        package='rclcpp_components',
        executable='component_container',
        composable_node_descriptions=[
            ComposableNode(
                package='dual_laser_merger',
                plugin='merger_node::MergerNode',
                name='dual_laser_merger',
                parameters=[
                    {'use_sim_time': True},
                    {'laser_1_topic': '/scan_front'},
                    {'laser_2_topic': '/scan_rear'},
                    {'merged_scan_topic': '/scan'},
                    {'merged_cloud_topic': '/scan_cloud'},
                    {'target_frame': 'base_link'},
                    {'tolerance': 1.0},
                    {'queue_size': 10},
                    {'angle_increment': 0.00290888},  # ~1651 samples for 360deg
                    {'scan_time': 0.0294},  # 1/34 Hz
                    {'range_min': 0.05},
                    {'range_max': 40.0},
                    {'min_height': -0.1},
                    {'max_height': 0.5},
                    {'angle_min': -3.141592654},
                    {'angle_max': 3.141592654},
                    {'use_inf': True},
                    {'enable_shadow_filter': False},
                    {'enable_average_filter': False},
                ],
            )
        ],
        output='screen',
    )

    return LaunchDescription([
        declare_world,
        robot_state_publisher,
        gazebo,
        spawn_robot,
        bridge,
        laser_merger,
    ])
