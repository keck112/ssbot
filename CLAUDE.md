# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Interaction Preferences

- **Language**: Always respond in Korean
- **코드 수정 금지**: 사용자가 명시적으로 수정을 확인/요청하기 전까지 어떠한 코드/파일도 수정하지 않는다. 분석과 설명만 제공한다.

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
- **ssbot_behavior_tree**: Nav2 커스텀 BT 노드 플러그인 + BT XML 파일 (Groot2 compatible)
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
    empty_with_sensors.sdf  # 빈 공간 월드 (센서 테스트용)
  graphs/
    route_graph.geojson     # Nav2 Route Server 경로 그래프
  src/
    trajectory_starter.py   # Cartographer trajectory 자동 시작 (저장된 pose 사용)
    pose_saver.py           # 현재 pose를 JSON으로 주기적 저장
    route_gui_commander.py  # Route Server GUI (GeoJSON 로드, 노드 선택, 주행 시작/정지)
  test/                     # 학습용 / 테스트용 독립 스크립트 (패키지 외부)
    robot_monitor.py        # ROS2 Node 학습용 (topic sub/pub)
    action_client.py        # NavigateToPose Action 직접 제어 학습용
    service_client.py       # Service 동기/비동기 호출 학습용
    waypoint_navigator.py   # Waypoint 순회 예제 (BasicNavigator)
```

### ssbot_behavior_tree Layout

```
ssbot_behavior_tree/
  include/ssbot_behavior_tree/bt_nodes/
    wait_action.hpp         # SsbotWait BT 노드 헤더
  src/bt_nodes/
    wait_action.cpp         # SsbotWait 구현 (nav2_msgs::action::Wait 래핑)
  behavior_trees/
    user_navigate_to_pose.xml                            # 사용자 정의 NavigateToPose BT
    navigate_through_poses_w_replanning_and_recovery.xml # NavigateThroughPoses + 복구 BT
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
  - `pose_saver.py`: `/trajectory_started` 토픽 수신 후 1초마다 pose 저장
  - `world→map` TF: VDA5050 world 좌표계를 위한 static_transform_publisher 내장
    - 기본값: `world_x=20.7 world_y=17.1 world_yaw=-1.6` (warehouse 기준, 인자로 변경 가능)
- **Navigation**: Nav2 with MPPI controller, NavfnPlanner, waypoint_follower
- **커스텀 BT 노드**: `ssbot_behavior_tree` 패키지 (`ssbot_bt_nodes.so` 플러그인)
  - `SsbotWait`: nav2_msgs::action::Wait 래핑, `wait_duration` 포트 입력
- **커스텀 BT XML**: `nav2_params.yaml`에 custom BT 경로 등록
  - `default_nav_through_poses_bt_xml`: `navigate_through_poses_w_replanning_and_recovery.xml`
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

## Current Development Goal: VDA 5050 기반 자율주행 시스템

### 목표
로봇의 모든 주행 방식을 **VDA 5050 프로토콜 사양에 맞춰 구현**하는 것.
- VDA 5050을 기본 설계 기준으로 삼고, 프로토콜이 요구하는 모든 사양(노드 액션, 엣지 속도 제한, deviation, orientation 등)을 만족해야 함
- 추후 TCP/IP, UDP 등 다른 통신 방식 추가를 고려한 확장 가능한 구조
- FMS(Fleet Management System) / ACS와의 연동을 최종 목표로 하되, 현재는 프로토콜 사양에 맞는 동작 구현이 우선
- FMS가 없는 개발/테스트 환경을 위한 **디버그용 GUI 주행 명령 도구** 필요

### 시스템 레이어 구조
```
[FMS / ACS]  ← 최종 목표: VDA 5050 (MQTT 등)
      ↕
[VDA 5050 Order Client]  ← 프로토콜 레이어 (Order 관리, State 보고, Instant Action)
      ↕ ROS 2 actions/services
[Nav2 Navigation Stack]  ← 주행 레이어 (경로 계획, 추종, 복구)
  - 주행 백엔드: FollowPath / Route Server / 커스텀 BT 중 최적 방식 선택
      ↕
[Robot Hardware / Gazebo]
```

### VDA 5050 구현 필수 사양
- **Order**: 노드-엣지 그래프 기반 주행 명령 수신 및 실행
- **Node Action**: `blockingType: HARD` (노드 정지 후 실행) / `SOFT` (주행 중 트리거)
- **Edge**: `maxSpeed` 속도 제한, `rotationAllowed` 회전 허용 여부
- **Node Deviation**: `deviationXY` / `deviationTheta` — 노드별 허용 오차
- **Orientation**: 노드 도착 후 지정 방향 정렬
- **State 보고**: 현재 위치, 동작 상태, 에러 등 주기적 보고
- **Instant Action**: 즉각 실행 명령 (정지, 취소 등) 비동기 처리

### 개발 방향 결정 사항
- **주행 레이어**: Nav2 기존 BT 노드(ComputePathToPose, FollowPath, Spin 등) 조합 + VDA 5050 전용 커스텀 BT 노드 최소화
- **프로토콜 레이어**: VDA 5050 Order Client ROS 2 노드로 분리 구현
- **테스트 도구**: FMS 없이 주행 명령을 보낼 수 있는 디버그 GUI

### Current Implementation Status
- [x] `bringup_launch.py` — Cartographer + Nav2 통합 bringup (slam/localization 선택)
- [x] `slam_launch.py` — Cartographer SLAM
- [x] `localization_launch.py` — Cartographer Localization + trajectory_starter + pose_saver + world TF
- [x] `trajectory_starter.py` — 저장된 pose로 Cartographer trajectory 자동 시작, `/trajectory_started` 신호 발행
- [x] `pose_saver.py` — `/trajectory_started` 수신 후 pose 주기적 저장
- [x] `ssbot_behavior_tree` — `SsbotWait` 커스텀 BT 노드 + BT XML 파일 2개
- [x] `route_gui_commander.py` — PyQt5 Route GUI 기본 구현 (개발 중, 일부 미완성)
- [ ] VDA 5050 Order Client — **구현 예정** (프로토콜 레이어)
  - nodes/edges → Nav2 명령 변환, State 보고, Instant Action 처리

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
