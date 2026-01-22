import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
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
    default_world = os.path.join(pkg_bringup, 'worlds', 'empty_with_sensors.sdf')

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

    # Static transforms to map Gazebo sensor frames to URDF frames
    static_tf_front_lidar = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=['0', '0', '0', '0', '0', '0', 'front_laser_frame', 'ssbot/base_footprint/front_lidar'],
        output='screen'
    )

    static_tf_rear_lidar = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=['0', '0', '0', '0', '0', '0', 'rear_laser_frame', 'ssbot/base_footprint/rear_lidar'],
        output='screen'
    )

    static_tf_imu = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=['0', '0', '0', '0', '0', '0', 'imu_link', 'ssbot/base_footprint/imu'],
        output='screen'
    )

    return LaunchDescription([
        declare_world,
        robot_state_publisher,
        gazebo,
        spawn_robot,
        bridge,
        static_tf_front_lidar,
        static_tf_rear_lidar,
        static_tf_imu,
    ])
