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

# Launch Gazebo simulation with the robot
ros2 launch ssbot_bringup gazebo.launch.py

# Launch Gazebo with a specific world file
ros2 launch ssbot_bringup gazebo.launch.py world:=my_world.sdf
```

## Architecture

This is a ROS 2 differential-drive robot (SSBot) workspace with Gazebo Harmonic simulation support.

### Package Structure

- **ssbot_description**: Robot model (URDF/Xacro), meshes, RViz configs
- **ssbot_bringup**: Launch files for simulation and robot bringup
- **ssbot_msgs**: Custom ROS 2 message/service definitions (template ready, no messages defined yet)

### Robot Model (ssbot_description/urdf/)

- `ssbot.urdf.xacro`: Main robot description - differential drive base (40x35cm), two drive wheels, front caster, 2D LiDAR, IMU
- `gazebo.xacro`: Gazebo-specific plugins and sensors
  - Differential drive controller (publishes to `cmd_vel`, `odom`)
  - GPU LiDAR sensor (publishes to `scan`)
  - IMU sensor (publishes to `imu`)

### ROS Topics (Gazebo Simulation)

- `/cmd_vel` (Twist): Robot velocity commands
- `/odom` (Odometry): Odometry from diff-drive plugin
- `/scan` (LaserScan): 2D LiDAR data
- `/imu` (Imu): IMU sensor data
- `/clock` (Clock): Simulation time

### Adding Custom Messages

Edit `ssbot_msgs/CMakeLists.txt` and uncomment the `rosidl_generate_interfaces` block:
```cmake
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/YourMsg.msg"
  "srv/YourSrv.srv"
  DEPENDENCIES std_msgs geometry_msgs
)
```
