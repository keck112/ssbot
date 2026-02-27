# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Interaction Preferences

- **Language**: Always respond in Korean

## Build Commands

```bash
# Build the entire workspace (run from ssbot_ws directory)
cd ~/ssbot_ws && colcon build

# Build a specific package
colcon build --packages-select ssbot_bringup

# Build with symlink install (Python/YAML 수정 시 재빌드 불필요)
colcon build --symlink-install

# Source the workspace after building
source ~/ssbot_ws/install/setup.bash
```

## Launch Commands

```bash
# View robot model in RViz with joint GUI
ros2 launch ssbot_description view_robot.launch.py

# Launch Gazebo simulation (default: slam_test world)
ros2 launch ssbot_bringup gazebo_launch.py

# Launch Gazebo with warehouse world
ros2 launch ssbot_bringup gazebo_launch.py world:=warehouse

# Cartographer SLAM + Nav2 (Gazebo 실행 후)
ros2 launch ssbot_bringup bringup_launch.py use_sim_time:=true slam:=true

# Cartographer Localization + Nav2 (Gazebo 실행 후)
ros2 launch ssbot_bringup bringup_launch.py use_sim_time:=true

# Localization only (Nav2 없이)
ros2 launch ssbot_bringup localization_launch.py use_sim_time:=true

# Launch RViz
ros2 launch ssbot_bringup rviz_launch.py

# Teleop keyboard control
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

> **주의**: Gazebo와 함께 실행할 때는 반드시 `use_sim_time:=true` 인자를 전달해야 합니다.
> 미전달 시 Cartographer(wall clock)와 Nav2(sim clock) 간 TF 시간 불일치 발생.

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
- **ssbot_bringup**: Launch files, params, maps, worlds, and Python scripts for full robot bringup
- **ssbot_msgs**: Custom ROS 2 message/service definitions (template ready, no messages defined yet)
- **dual_laser_merger**: Merges front/rear LiDAR scans into single 360-degree scan

### ssbot_bringup Layout

```
ssbot_bringup/
  launch/
    gazebo_launch.py        # Gazebo simulation + ros_gz_bridge
    bringup_launch.py       # Cartographer(SLAM or Localization) + Nav2
    slam_launch.py          # Cartographer SLAM (backpack_2d.lua)
    localization_launch.py  # Cartographer Localization (localization_2d.lua)
    rviz_launch.py          # RViz
    nanoscan3.launch.py     # Real NanoScan3 sensor launch
  params/
    nav2_params.yaml        # Nav2 전체 파라미터 (MPPI controller, costmap 등)
    backpack_2d.lua         # Cartographer SLAM 설정
    localization_2d.lua     # Cartographer Localization 설정
    ros_gz_bridge.yaml      # Gazebo ↔ ROS 2 토픽 브릿지 설정
    nanoscan3_front.yaml    # 실제 센서 파라미터
    nanoscan3_rear.yaml
  maps/
    my_map.pbstream         # Cartographer 맵 (localization용)
    my_map.yaml / .pgm      # Nav2 static layer용 맵
  worlds/
    slam_test.sdf           # 기본 Gazebo 월드
    warehouse.sdf           # 창고 월드
  graphs/
    route_graph.geojson     # Nav2 Route Server 경로 그래프
  src/
    trajectory_starter.py   # Cartographer trajectory 자동 시작 (저장된 pose 사용)
    pose_saver.py           # 현재 pose를 JSON으로 주기적 저장
    route_gui_commander.py  # VDA 5050 Route GUI (구현 중)
```

### Robot Model (ssbot_description/urdf/)

- `ssbot.urdf.xacro`: Main robot description - differential drive base (60x40cm), two drive wheels, four casters, dual 2D LiDAR (SICK NanoScan3), IMU
- `gazebo.xacro`: Gazebo-specific plugins and sensors
  - Differential drive controller (publishes to `cmd_vel`, `odom` at 33Hz)
  - Dual GPU LiDAR sensors (publishes to `scan_front`, `scan_rear`)
  - IMU sensor (publishes to `imu`)

### Navigation Stack

- **SLAM**: Cartographer (`backpack_2d.lua`, scan_front + scan_rear 직접 입력)
- **Localization**: Cartographer localization (`localization_2d.lua`, pbstream 맵 로드)
  - `trajectory_starter.py`: 이전 세션 저장 pose로 초기 trajectory 자동 시작
  - `pose_saver.py`: 1초마다 현재 pose를 `maps/last_pose.json`에 저장
- **Navigation**: Nav2 with MPPI controller, NavfnPlanner, waypoint_follower
- **Route Server**: Nav2 Route Server with GeoJSON graph support (VDA LIF Editor compatible)
- **Costmap**: Static layer (map), obstacle layer (scan_front + scan_rear), inflation layer
- **Collision Monitor**: Footprint approach with scan source

### ROS Topics (Gazebo Simulation)

- `/cmd_vel` (Twist): Robot velocity commands
- `/odom` (Odometry): Odometry from diff-drive plugin
- `/scan_front` (LaserScan): Front LiDAR (NanoScan3, 275deg FOV)
- `/scan_rear` (LaserScan): Rear LiDAR (NanoScan3, 275deg FOV)
- `/imu` (Imu): IMU sensor data
- `/clock` (Clock): Simulation time
- `/map` (OccupancyGrid): Map from Cartographer occupancy grid node

## Current Development Goal: VDA 5050 Route Navigation

### Overview
Nav2 Route Server를 VDA 5050 프로토콜 기반으로 제어하는 시스템 구현.
BT(Behavior Tree) 방식이 아닌 **직접 Action 호출 방식**으로 구현.

### Core Architecture
```
GeoJSON Graph → set_route_graph (service) → Route Server
                                                  ↓
GUI (Start/Stop) → compute_and_track_route (action) → feedback loop
                                                  ↓
                   feedback(path) → follow_path (action) → Controller Server
```

### VDA 5050 ↔ nav2_route 매핑
- VDA 5050 **Action** = nav2_route **Operation** (플러그인)
  - action `name` → operation name
  - action `type` → operation type
  - `blockingType: HARD` → blocking RouteOperation (node에서 정지 후 실행)
  - `blockingType: SOFT` → non-blocking TriggerEvent
- VDA 5050 **Edge** `maxSpeed` → metadata `abs_speed_limit` → `AdjustSpeedLimit` operation
- VDA 5050 **Edge** `rotationAllowed: false` → node 도달 후 Spin → 진행
- VDA 5050 **Node** `deviationXY/Theta` → goal tolerance (추후 구현)

### Key Interfaces
- `nav2_msgs/srv/SetRouteGraph` → `route_server/set_route_graph`
  - Request: `graph_filepath` (string)
  - Response: `success` (bool)
- `nav2_msgs/action/ComputeAndTrackRoute`
  - Goal: `start_id`, `goal_id`, `use_poses`, `start`, `goal`, `use_start`
  - Feedback: `last_node_id`, `next_node_id`, `current_edge_id`, `route`, `path`, `operations_triggered`, `rerouted`
- `nav2_msgs/action/FollowPath`
  - Goal: `path`, `controller_id`

### GeoJSON Graph Format (nav2_route)
```json
{
  "features": [
    { "geometry": {"type": "Point", "coordinates": [x, y]},
      "properties": {"id": 0, "frame": "map",
        "metadata": {"theta": 0.0},
        "operations": [{"type": "ActionName", "trigger": "ON_ENTER",
                        "metadata": {"action_type": "wait", "duration": 5.0}}]} },
    { "geometry": {"type": "MultiLineString"},
      "properties": {"id": 100, "startid": 0, "endid": 1,
        "metadata": {"abs_speed_limit": 0.5, "rotation_allowed": false}} }
  ]
}
```

### Route Server Operations (nav2_route plugins)
- `AdjustSpeedLimit` — edge `abs_speed_limit` 메타데이터로 속도 자동 제한
- `CollisionMonitor` — 장애물 감지 시 정지(`reroute_on_collision: false`) 또는 회피
- `ReroutingService` — 외부 서비스 요청으로 재경로
- (커스텀) `HardActionOperation` — `blockingType: HARD` action 처리 (node에서 blocking)
- (커스텀) `PreEdgeRotationOperation` — `rotation_allowed: false` edge 전 Spin

### Current Implementation Status
- [x] `bringup_launch.py` — Cartographer + Nav2 통합 bringup (slam/localization 선택)
- [x] `slam_launch.py` — Cartographer SLAM
- [x] `localization_launch.py` — Cartographer Localization + trajectory_starter + pose_saver
- [x] `trajectory_starter.py` — 저장된 pose로 Cartographer trajectory 자동 시작
- [x] `pose_saver.py` — 현재 pose 주기적 저장
- [ ] `route_gui_commander.py` — **현재 구현 중**
  - Graph 불러오기 (Browse + Load → set_route_graph service)
  - Start/Stop (compute_and_track_route action)
  - Feedback 표시 (last_node_id, next_node_id, current_edge_id 등)

### Launch for Full System Test
```bash
# Terminal 1: Gazebo
ros2 launch ssbot_bringup gazebo_launch.py

# Terminal 2: Cartographer Localization + Nav2
ros2 launch ssbot_bringup bringup_launch.py use_sim_time:=true

# Terminal 3: RViz
ros2 launch ssbot_bringup rviz_launch.py
```

### Known Issues

- Gazebo `gz_frame_id` warnings on startup are benign (SDF parser warning for Gazebo-specific extension)
- `use_sim_time:=true` 미전달 시 Cartographer(wall clock) vs Nav2(sim clock) TF 시간 불일치 발생
- Cartographer 재시작 시 "Topic already used" 에러: 이전 trajectory 잔존 (동작에는 무관)
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
