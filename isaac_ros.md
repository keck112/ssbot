# Isaac ROS 연동 계획 (Docker 방식)

> 공식 문서: https://nvidia-isaac-ros.github.io/getting_started/index.html
> 작성일: 2026-03-24

---

## 목표

`isaac_ros_cloud_control` 패키지의 VDA 5050 관련 기능을 ssbot에 연동한다.
NVIDIA 공식 권장 방식인 **Docker 환경**으로 Isaac ROS를 구성하고, 기존 ssbot (Gazebo + Nav2) 스택과 ROS 2 통신으로 연결한다.

---

## 왜 Docker인가

Isaac ROS 공식 문서에서 세 가지 환경 격리 모드를 제공한다:

| 모드 | 격리 수준 | 공식 권장 여부 |
|------|-----------|---------------|
| **Docker** | 높음 (컨테이너 완전 격리) | ✅ Recommended |
| Virtual Environment | 중간 | - |
| Bare Metal | 없음 (시스템 직접 설치) | ⚠️ Advanced users only, 시스템 파손 위험 |

---

## 환경 구성 단계 (공식 문서 기준)

### Step 1. Isaac ROS CLI 설치

```bash
sudo apt-get install isaac-ros-cli
```

### Step 2. Docker Engine 설치

공식 Ubuntu 가이드 참고: https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository

### Step 3. NVIDIA Container Toolkit 설치 및 Docker 런타임 설정

```bash
# 설치: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html
# Docker 런타임 설정: 위 링크의 Configuring Docker 섹션 참고
```

### Step 4. 사용자를 docker 그룹에 추가

```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Step 5. Docker 재시작

```bash
sudo systemctl daemon-reload && sudo systemctl restart docker
```

### Step 6. Docker 사전 점검

```bash
docker info | grep -E "Runtimes|Default Runtime"
docker run --rm hello-world
docker run --rm --gpus all ubuntu:24.04 bash -lc 'echo "NVIDIA runtime OK"'
```

### Step 7. Isaac ROS CLI 초기화 (Docker 모드)

```bash
sudo isaac-ros init docker
```

---

## ssbot과의 연동 구조

```
[ssbot (Native Linux)]          [Isaac ROS (Docker 컨테이너)]
  Gazebo Harmonic                  isaac_ros_cloud_control
  Nav2 Stack                         └─ isaac_ros_vda5050_client
  /cmd_vel, /odom, /scan            └─ isaac_ros_mission_client
       ↕  ROS 2 (DDS)  ↕                └─ isaac_ros_mqtt_bridge
  VDA 5050 명령 수신 ──────────────→  VDA 5050 Order 처리
  Nav2 Action 호출  ←──────────────  Nav2 명령 발행
```

- Docker 컨테이너와 host의 ROS 2 통신은 **DDS (기본 FastDDS)** 를 통해 같은 네트워크에서 자동 연결된다.
- `ROS_DOMAIN_ID`를 양쪽 동일하게 설정하면 토픽/액션이 공유된다.

---

## 진행 순서 (TODO)

- [ ] Step 1~7: Docker 환경 구성 완료
- [ ] Isaac ROS 컨테이너에서 `isaac_ros_cloud_control` 빌드 확인
- [ ] ssbot ↔ Isaac ROS 컨테이너 간 ROS 2 통신 테스트 (`/cmd_vel` 등 토픽 확인)
- [ ] `isaac_ros_vda5050_client` 동작 확인 (VDA 5050 Order 수신 → Nav2 명령 변환)
- [ ] ssbot VDA 5050 클라이언트와 통합 테스트

---

## isaac_ros_cloud_control 패키지 구성

### 사용할 패키지

| 패키지 | 역할 |
|--------|------|
| `isaac_ros_vda5050_client` | VDA 5050 Order → Nav2 변환 핵심 노드 |
| `isaac_ros_mission_client` | Order 수신/State 보고 통합 |
| `isaac_ros_mqtt_bridge` | MQTT ↔ ROS 2 브릿지 |
| `vda5050_msgs` | VDA 5050 메시지 정의 |
| `vda5050_action_handler` | 액션 핸들러 플러그인 베이스 |
| `vda5050_action_handler_plugins` | 액션 타입별 플러그인 구현 |

### 제외할 패키지 (Isaac Sim / NVIDIA 하드웨어 전용)

| 패키지 | 제외 이유 |
|--------|----------|
| `isaac_ros_mega_controller` | Isaac Sim + AWS S3 자동화 전용 |
| `isaac_ros_mega_node_monitor` | Nova Carter 하드웨어 종속 설정 |
| `isaac_ros_scene_recorder` | Isaac Sim 씬 캡처 전용 |
| `isaac_ros_scene_recorder_interface` | scene_recorder 의존 인터페이스 |

---

## Order 수신 → 실행 흐름 (vda5050_client_node.cpp 분석)

### 전체 흐름

```
FMS / GUI
  │ vda5050_msgs/Order
  ▼
/client_commands 토픽
  │
  ▼
Vda5050ClientNode
  ├─ OrderCallback()          ← Order 수신, 모든 액션 WAITING으로 초기화
  ├─ ExecuteOrderCallback()   ← 200ms 루프: 노드 도착 확인 + 액션 처리
  │    └─ ExecuteAction()     ← pluginlib으로 action_type별 핸들러 호출
  ├─ NavigateThroughPoses()   ← Nav2 navigate_through_poses action 호출
  ├─ InstantActionsCallback() ← 즉각 정지/취소 비동기 처리
  └─ StateTimerCallback()     ← /agv_state 주기 발행 (1초)
```

### 노드 도착 후 액션 처리 로직 (blockingType)

```
reached_waypoint_ == true 시:

현재 노드의 액션 순회
  ├─ HARD blocking + WAITING  → ExecuteAction() 호출 후 완료 대기 (주행 정지)
  ├─ HARD blocking + RUNNING  → 완료될 때까지 return (주행 정지)
  ├─ SOFT blocking + WAITING  → ExecuteAction() 호출, 주행은 stop_driving=true
  ├─ NONE blocking + WAITING  → ExecuteAction() 호출, 주행 계속
  └─ 모든 액션 FINISHED       → next_stop_++ → NavigateThroughPoses() 재호출
```

### 액션 핸들러 플러그인 목록

| 플러그인 | 처리 action_type | ssbot 적용 |
|---------|-----------------|-----------|
| `docking_handler` | dock / undock | Nav2 DockRobot action 호출 |
| `map_handler` | startPause 등 | 맵 전환 |
| `apriltag_handler` | AprilTag 인식 | Isaac Sim 전용 |
| `pick_and_place_handler` | 매니퓰레이터 | Isaac Sim 전용 |
| `scene_recorder_handler` | 씬 녹화 | Isaac Sim 전용 |

> ssbot용 커스텀 액션 핸들러를 pluginlib 플러그인으로 추가 구현 가능

### ROS 인터페이스 요약

| 방향 | 토픽 / 액션 | 타입 |
|------|------------|------|
| 수신 | `/client_commands` | `vda5050_msgs/Order` |
| 수신 | `/instant_actions_commands` | `vda5050_msgs/InstantActions` |
| 발행 | `/agv_state` | `vda5050_msgs/AGVState` |
| 발행 | `/factsheet` | `vda5050_msgs/Factsheet` |
| Action Client | `navigate_through_poses` | `nav2_msgs/NavigateThroughPoses` |
| TF 조회 | `map` → `base_link` | 현재 위치 추적 |

---

## 참고

- Isaac ROS Cloud Control 리포지토리: https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_cloud_control
- VDA 5050 공식 사양: https://github.com/VDA5050/VDA5050
- ssbot VDA 5050 개발 목표: `CLAUDE.md` → "Current Development Goal" 섹션 참고
