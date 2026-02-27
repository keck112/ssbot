import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, TimerAction
from launch.actions import SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.substitutions import EqualsSubstitution, NotSubstitution
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch.substitutions import NotEqualsSubstitution
from launch_ros.actions import LoadComposableNodes, SetParameter
from launch_ros.actions import Node
from launch_ros.descriptions import ComposableNode, ParameterFile
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    # Get the launch directory
    bringup_dir = get_package_share_directory('ssbot_bringup')

    namespace = LaunchConfiguration('namespace')
    map_file = LaunchConfiguration('map')
    use_sim_time = LaunchConfiguration('use_sim_time')
    autostart = LaunchConfiguration('autostart')
    config_file = LaunchConfiguration('config_file')
    container_name = LaunchConfiguration('container_name')
    container_name_full = (namespace, '/', container_name)
    use_respawn = LaunchConfiguration('use_respawn')
    log_level = LaunchConfiguration('log_level')
    use_pose_save = LaunchConfiguration('use_pose_save')
    # world_x = LaunchConfiguration('world_x')
    # world_y = LaunchConfiguration('world_y')
    # world_z = LaunchConfiguration('world_z')
    # world_yaw = LaunchConfiguration('world_yaw')
    
    lifecycle_nodes = ['cartographer']
    
    # Map fully qualified names to relative ones so the node's namespace can be prepended.
    remappings = [('/tf', 'tf'), ('/tf_static', 'tf_static')]
    
    # configured_params = ParameterFile(
    #     RewrittenYaml(
    #         source_file=params_file,
    #         root_key=namespace,
    #         param_rewrites={},
    #         convert_types=True,
    #     ),
    #     allow_substs=True,
    # )

    stdout_linebuf_envvar = SetEnvironmentVariable(
        'RCUTILS_LOGGING_BUFFERED_STREAM', '1'
    )

    declare_namespace_cmd = DeclareLaunchArgument(
        'namespace', default_value='', description='Top-level namespace'
    )

    declare_map_cmd = DeclareLaunchArgument(
        'map', 
        default_value=os.path.join(bringup_dir, 'maps', 'my_map.pbstream'),
        description='Full path to map pbstream file to load'
    )

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation (Gazebo) clock if true',
    )

    declare_config_file_cmd = DeclareLaunchArgument(
        'config_file',
        default_value='localization_2d.lua',
        description='Cartographer configuration file name',
    )

    declare_autostart_cmd = DeclareLaunchArgument(
        'autostart',
        default_value='true',
        description='Automatically startup the nav2 stack',
    )

    declare_use_composition_cmd = DeclareLaunchArgument(
        'use_composition',
        default_value='False',
        description='Use composed bringup if True',
    )

    declare_use_intra_process_comms_cmd = DeclareLaunchArgument(
        'use_intra_process_comms',
        default_value='False',
        description='Use intra process communications if True',
    )

    declare_container_name_cmd = DeclareLaunchArgument(
        'container_name',
        default_value='nav2_container',
        description='the name of container that nodes will load in if use composition',
    )

    declare_use_respawn_cmd = DeclareLaunchArgument(
        'use_respawn',
        default_value='False',
        description='Whether to respawn if a node crashes. Applied when composition is disabled.',
    )

    declare_log_level_cmd = DeclareLaunchArgument(
        'log_level', default_value='info', description='log level'
    )
    
    declare_use_pose_save_cmd = DeclareLaunchArgument(
        'use_pose_save',
        default_value='true',
        description='Whether to save the last pose to a file for use in next localization run',
    )
    
    load_nodes = GroupAction(
        actions=[
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
                    '-configuration_basename', config_file,
                    '-load_state_filename', map_file,
                    '--minloglevel=1',
                    '-start_trajectory_with_default_topics', NotSubstitution(use_pose_save),
                    # '-collect_metrics',
                ],
                remappings=[
                    ('scan_1', 'scan_front'),
                    ('scan_2', 'scan_rear'),
                    ('odom', '/odom'),
                    ('imu', '/imu'),
                ]
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
            Node(
                condition=IfCondition(use_pose_save),
                package='ssbot_bringup',
                executable='trajectory_starter.py',
                name='trajectory_starter',
                output='screen',
                respawn=use_respawn,
                respawn_delay=2.0,
                parameters=[
                    {'pose_file': os.path.join(bringup_dir, 'maps', 'last_pose.json')},
                    {'config_dir': os.path.join(bringup_dir, 'params')},
                    {'config_basename': config_file},
                ],
            ),
            Node(
                condition=IfCondition(use_pose_save),
                package='ssbot_bringup',
                executable='pose_saver.py',
                name='pose_saver',
                output='screen',
                respawn=use_respawn,
                respawn_delay=2.0,
                parameters=[
                    {'save_path': os.path.join(bringup_dir, 'maps', 'last_pose.json')},
                    {'save_interval': 1.0},
                ],
            ),
        ],
    )

    # Create the launch description and populate
    ld = LaunchDescription()

    # Set environment variables
    ld.add_action(stdout_linebuf_envvar)

    # Declare the launch options
    ld.add_action(declare_namespace_cmd)
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_config_file_cmd)
    ld.add_action(declare_autostart_cmd)
    ld.add_action(declare_use_composition_cmd)
    ld.add_action(declare_container_name_cmd)
    ld.add_action(declare_use_respawn_cmd)
    ld.add_action(declare_log_level_cmd)
    ld.add_action(declare_use_pose_save_cmd)
    ld.add_action(declare_map_cmd)

    # Add the actions to launch all of the localiztion nodes
    ld.add_action(load_nodes)

    return ld

    # return LaunchDescription([
    #     DeclareLaunchArgument('use_sim_time', default_value='true'),
    #     DeclareLaunchArgument('map_file', default_value='/home/ss/maps/my_map.pbstream'),
    #     DeclareLaunchArgument('world_x', default_value='20.7',
    #                           description='VDA5050 world frame X offset from map'),
    #     DeclareLaunchArgument('world_y', default_value='17.1',
    #                           description='VDA5050 world frame Y offset from map'),
    #     DeclareLaunchArgument('world_z', default_value='0.0',
    #                           description='VDA5050 world frame Z offset from map'),
    #     DeclareLaunchArgument('world_yaw', default_value='-1.6',
    #                           description='VDA5050 world frame yaw offset from map (radians)'),

    #     # VDA5050 world -> map static transform
    #     Node(
    #         package='tf2_ros',
    #         executable='static_transform_publisher',
    #         name='world_to_map_publisher',
    #         output='screen',
    #         arguments=[
    #             '--x', world_x,
    #             '--y', world_y,
    #             '--z', world_z,
    #             '--yaw', world_yaw,
    #             '--pitch', '0.0',
    #             '--roll', '0.0',
    #             '--frame-id', 'world',
    #             '--child-frame-id', 'map',
    #         ],
    #     ),
