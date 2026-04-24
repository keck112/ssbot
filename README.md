# SSBot — ROS 2 자율주행 로봇 시스템

ROS 2 Jazzy 기반 차동구동 자율주행 로봇 시스템.
Gazebo Harmonic 시뮬레이션, Cartographer SLAM/Localization, Nav2 내비게이션 스택을 통합하며,
VDA 5050 프로토콜 기반 AGV 시스템 구현을 목표로 개발 중입니다.

---

## 패키지 구조

```
ssbot/
├── ssbot_description/      # 로봇 URDF 모델, 메쉬
├── ssbot_bringup/          # 런치 파일, 파라미터, 지도, 월드, 유틸리티 노드
└── ssbot_behavior_tree/    # Nav2 커스텀 BT XML 파일 및 플러그인
```

### ssbot_bringup 구성

```
ssbot_bringup/
├── launch/
│   ├── gazebo_launch.py        # Gazebo 시뮬레이션 + ROS-Gazebo 브릿지
│   ├── bringup_launch.py       # Cartographer(SLAM/Localization) + Nav2 통합
│   ├── slam_launch.py          # Cartographer SLAM 단독
│   ├── localization_launch.py  # Cartographer Localization + pose 자동 복원
│   ├── rviz_launch.py          # RViz 시각화
│   └── nanoscan3.launch.py     # 실제 NanoScan3 센서 런치
├── params/
│   ├── nav2_params.yaml        # Nav2 전체 파라미터 (MPPI, costmap 등)
│   ├── backpack_2d.lua         # Cartographer SLAM 설정
│   ├── localization_2d.lua     # Cartographer Localization 설정
│   └── ros_gz_bridge.yaml      # Gazebo ↔ ROS 2 토픽 브릿지 매핑
├── maps/                       # 저장된 지도 (pbstream, yaml, pgm)
├── worlds/                     # Gazebo 월드
└── src/
    ├── trajectory_starter.py   # 이전 세션 pose로 Cartographer 자동 초기화
    ├── pose_saver.py           # 현재 pose 주기적 저장 (JSON)
    └── map_saver.py            # 지도 저장 유틸리티 (대화형)
```

### ssbot_behavior_tree 구성

```
ssbot_behavior_tree/
└── behavior_trees/
    ├── navigate_path_through_poses.xml
    └── navigate_path_through_poses_w_replanning.xml
```

---

## 시스템 아키텍처

```
[FMS / ACS]
      ↕  VDA 5050
[VDA 5050 Order Client]     ← 프로토콜 레이어 (개발 중)
      ↕  ROS 2 actions/services
[Nav2 Navigation Stack]     ← 주행 레이어
  BT Navigator → Planner → Controller (MPPI)
  Collision Monitor → Waypoint Follower
      ↕
[Cartographer]              ← SLAM / Localization
      ↕
[Robot Hardware / Gazebo Harmonic]
```

### 데이터 흐름

```
Gazebo
  /scan_front, /scan_rear  ──→  Cartographer  ──→  /map, TF(map→odom)
  /odom, /imu              ──→  Cartographer
  /clock                   ──→  Nav2 (sim time)
                                    ↓
                               Nav2 Stack
                                    ↓
  /cmd_vel  ←────────────────────────
```

### TF 트리

```
world → map → odom → base_footprint → base_link
                                         ├─ front_lidar_link
                                         ├─ rear_lidar_link
                                         └─ imu_link
```

---

## 빌드 및 설치

```bash
# 워크스페이스 빌드
cd ~/ssbot_ws && colcon build

# 심볼릭 링크 설치 (Python/YAML 수정 시 재빌드 불필요)
colcon build --symlink-install

# 환경 소스
source ~/ssbot_ws/install/setup.bash
```

---

## 실행 방법

> `use_sim_time:=true` 없이 실행하면 Cartographer와 Nav2 간 TF 시간 불일치가 발생합니다.

### SLAM 모드 (지도 생성)

```bash
# Terminal 1
ros2 launch ssbot_bringup gazebo_launch.py

# Terminal 2
ros2 launch ssbot_bringup bringup_launch.py use_sim_time:=true slam:=true

# Terminal 3
ros2 launch ssbot_bringup rviz_launch.py

# Terminal 4 (수동 조작)
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

### Localization 모드 (저장된 지도 사용)

```bash
# Terminal 1
ros2 launch ssbot_bringup gazebo_launch.py

# Terminal 2
ros2 launch ssbot_bringup bringup_launch.py use_sim_time:=true

# Terminal 3
ros2 launch ssbot_bringup rviz_launch.py
```

### 런치 인자

| 인자 | 기본값 | 설명 |
|---|---|---|
| `world` | `warehouse` | Gazebo 월드 이름 (`warehouse` 등) |
| `slam` | `false` | `true`면 SLAM mapping, `false`면 Pure Localization |
| `map` | `my_map.yaml` | Localization 시 사용할 지도 파일 |
| `use_sim_time` | `false` | Gazebo 사용 시 반드시 `true` |
| `use_pose_save` | `false` | 이전 세션 pose 자동 복원 활성화 |

---

## 지도 관리

### 서비스 콜로 직접 저장

```bash
# 1. Trajectory 종료
ros2 service call /finish_trajectory cartographer_ros_msgs/srv/FinishTrajectory \
  "{trajectory_id: 0}"

# 2. pbstream 저장
ros2 service call /write_state cartographer_ros_msgs/srv/WriteState \
  "{filename: '/home/ss/maps/my_map.pbstream', include_unfinished_submaps: true}"

# 3. Nav2용 yaml/pgm 변환
ros2 run cartographer_ros cartographer_pbstream_to_ros_map \
  -pbstream_filename=/home/ss/maps/my_map.pbstream \
  -map_filestem=/home/ss/maps/my_map \
  -resolution=0.05
```

### map_saver.py 스크립트 사용 (위 3단계 자동화)

```bash
ros2 run ssbot_bringup map_saver
# 저장 경로 입력 프롬프트가 표시됩니다 (예: /home/ss/maps/my_map)
# finish_trajectory → write_state → pbstream_to_ros_map 순서로 자동 실행
```

---

## 개발 로드맵

VDA 5050 프로토콜 기반 AGV 통합 테스트 진행 중.
