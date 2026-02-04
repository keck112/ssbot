# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Interaction Preferences

- **Language**: Always respond in English only

## Build Commands

```bash
# Build the entire workspace (run from ssbot_ws directory)
cd ~/ssbot_ws && colcon build

# Build a specific package
colcon build --packages-select ssbot_description

# Source the workspace after building
source ~/ssbot_ws/install/setup.bash
```

## Launch Commands

```bash
# View robot model in RViz with joint GUI
ros2 launch ssbot_description view_robot.launch.py

# Launch Gazebo simulation with the robot (default: slam_test world)
ros2 launch ssbot_bringup gazebo.launch.py

# Launch Gazebo with nav2 warehouse world
ros2 launch ssbot_bringup gazebo.launch.py world:=/opt/ros/jazzy/share/nav2_minimal_tb4_sim/worlds/warehouse.sdf

# Launch Cartographer SLAM (mapping)
ros2 launch ssbot_cartographer cartographer.launch.py

# Launch Cartographer localization (with existing map)
ros2 launch ssbot_cartographer localization.launch.py

# Launch Nav2 navigation
ros2 launch ssbot_bringup navigation.launch.py map:=/home/ss/maps/my_map.yaml

# Teleop keyboard control
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

## Map Management

```bash
# Save map from Cartographer
ros2 service call /finish_trajectory cartographer_ros_msgs/srv/FinishTrajectory "{trajectory_id: 0}"
ros2 service call /write_state cartographer_ros_msgs/srv/WriteState "{filename: '/home/ss/maps/warehouse.pbstream'}"

# Convert pbstream to nav2 format (yaml + pgm)
ros2 run cartographer_ros cartographer_pbstream_to_ros_map \
  -pbstream_filename=/home/ss/maps/warehouse.pbstream \
  -map_filestem=/home/ss/maps/warehouse \
  -resolution=0.05
```

## Architecture

This is a ROS 2 differential-drive robot (SSBot) workspace with Gazebo Harmonic simulation support.

### Package Structure

- **ssbot_description**: Robot model (URDF/Xacro), meshes, RViz configs
- **ssbot_bringup**: Launch files for simulation, navigation, and robot bringup
- **ssbot_cartographer**: Cartographer SLAM and localization configurations
- **ssbot_msgs**: Custom ROS 2 message/service definitions (template ready, no messages defined yet)
- **dual_laser_merger**: Merges front/rear LiDAR scans into single 360-degree scan

### Robot Model (ssbot_description/urdf/)

- `ssbot.urdf.xacro`: Main robot description - differential drive base (60x40cm), two drive wheels, four casters, dual 2D LiDAR (SICK NanoScan3), IMU
- `gazebo.xacro`: Gazebo-specific plugins and sensors
  - Differential drive controller (publishes to `cmd_vel`, `odom` at 33Hz)
  - Dual GPU LiDAR sensors (publishes to `scan_front`, `scan_rear`)
  - IMU sensor (publishes to `imu`)

### Navigation Stack

- **SLAM**: Cartographer (ssbot_cartographer) with merged dual LiDAR
- **Localization**: Cartographer localization mode with pbstream
- **Navigation**: Nav2 with MPPI controller, NavfnPlanner, waypoint_follower
- **Costmap**: Static layer (map), obstacle layer (scan), inflation layer
- **Collision Monitor**: Footprint approach with scan source

### ROS Topics (Gazebo Simulation)

- `/cmd_vel` (Twist): Robot velocity commands
- `/odom` (Odometry): Odometry from diff-drive plugin
- `/scan_front` (LaserScan): Front LiDAR data (NanoScan3, 275deg FOV)
- `/scan_rear` (LaserScan): Rear LiDAR data (NanoScan3, 275deg FOV)
- `/scan` (LaserScan): Merged 360-degree LiDAR data
- `/imu` (Imu): IMU sensor data
- `/clock` (Clock): Simulation time
- `/map` (OccupancyGrid): Map from map_server or Cartographer

### Known Issues

- Gazebo `gz_frame_id` warnings on startup are benign (SDF parser warning for Gazebo-specific extension)
- Nav2 warehouse world uses `max_step_size: 0.003`, odom frequency must be compatible (currently 33Hz)
- RViz RobotModel requires Durability Policy set to `Transient Local` to receive `/robot_description`

### Adding Custom Messages

Edit `ssbot_msgs/CMakeLists.txt` and uncomment the `rosidl_generate_interfaces` block:
```cmake
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/YourMsg.msg"
  "srv/YourSrv.srv"
  DEPENDENCIES std_msgs geometry_msgs
)
```
