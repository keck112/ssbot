#!/usr/bin/env python3
"""
Route GUI Commander
- GeoJSON 그래프 불러오기 → set_route_graph service call
- Start/Goal 노드 선택 → compute_and_track_route action 실행
- Feedback 실시간 표시 (last_node_id, next_node_id, current_edge_id 등)
- path feedback → follow_path action 연결
"""

import sys
import json
import threading

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup

from nav2_msgs.srv import SetRouteGraph
from nav2_msgs.action import ComputeAndTrackRoute, FollowPath

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QComboBox,
    QPushButton, QVBoxLayout, QHBoxLayout,
    QTextEdit, QGroupBox, QFileDialog, QLineEdit,
    QSizePolicy,
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject


# ---------------------------------------------------------------------------
# Thread-safe 로그 시그널
# ---------------------------------------------------------------------------
class _Signals(QObject):
    log = pyqtSignal(str)
    feedback_update = pyqtSignal(str)
    nav_finished = pyqtSignal(str)


# ---------------------------------------------------------------------------
# ROS 2 노드
# ---------------------------------------------------------------------------
class RouteCommanderNode(Node):
    def __init__(self):
        super().__init__('route_gui_commander')
        self._cb_group = ReentrantCallbackGroup()

        # SetRouteGraph service client
        self._graph_client = self.create_client(
            SetRouteGraph,
            'route_server/set_route_graph',
            callback_group=self._cb_group,
        )

        # ComputeAndTrackRoute action client
        self._route_client = ActionClient(
            self,
            ComputeAndTrackRoute,
            'compute_and_track_route',
            callback_group=self._cb_group,
        )

        # FollowPath action client
        self._follow_client = ActionClient(
            self,
            FollowPath,
            'follow_path',
            callback_group=self._cb_group,
        )

        self._route_goal_handle = None
        self._follow_goal_handle = None
        self._current_edge_id = None   # edge 변경 감지용
        self._latest_path = None       # feedback에서 받은 최신 path
        self._follow_replacing = False  # edge 교체 중복 방지
        self._signals: _Signals = None  # GUI에서 주입

    def set_signals(self, signals: _Signals):
        self._signals = signals

    def _log(self, msg: str):
        self.get_logger().info(msg)
        if self._signals:
            self._signals.log.emit(msg)

    # -----------------------------------------------------------------------
    # Graph 로드
    # -----------------------------------------------------------------------
    def load_graph(self, graph_filepath: str):
        if not self._graph_client.wait_for_service(timeout_sec=3.0):
            self._log('[ERROR] set_route_graph 서비스 없음. Route Server 실행 중인지 확인')
            return False

        req = SetRouteGraph.Request()
        req.graph_filepath = graph_filepath
        future = self._graph_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)

        if future.result() is None:
            self._log('[ERROR] set_route_graph 서비스 응답 없음')
            return False

        if future.result().success:
            self._log(f'[OK] 그래프 로드 완료: {graph_filepath}')
            return True
        else:
            self._log('[ERROR] 그래프 로드 실패 (서버 응답: success=False)')
            return False

    # -----------------------------------------------------------------------
    # Route 시작
    # -----------------------------------------------------------------------
    def start_route(self, start_id: int, goal_id: int):
        if not self._route_client.wait_for_server(timeout_sec=3.0):
            self._log('[ERROR] compute_and_track_route 액션 서버 없음')
            if self._signals:
                self._signals.nav_finished.emit('ERROR')
            return

        goal = ComputeAndTrackRoute.Goal()
        goal.start_id = start_id
        goal.goal_id = goal_id
        goal.use_poses = False  # ID 기반 라우팅
        goal.use_start = False  # 현재 위치에서 시작

        self._log(f'[Route] Start: {start_id} → Goal: {goal_id}')
        send_future = self._route_client.send_goal_async(
            goal,
            feedback_callback=self._route_feedback_cb,
        )
        send_future.add_done_callback(self._route_goal_response_cb)

    def _route_goal_response_cb(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self._log('[ERROR] compute_and_track_route goal 거부됨')
            if self._signals:
                self._signals.nav_finished.emit('REJECTED')
            return

        self._route_goal_handle = goal_handle
        self._log('[Route] Goal 수락됨. 경로 추적 시작...')
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._route_result_cb)

    def _route_feedback_cb(self, feedback_msg):
        fb = feedback_msg.feedback
        lines = [
            f'last_node: {fb.last_node_id}',
            f'next_node: {fb.next_node_id}',
            f'edge:      {fb.current_edge_id}',
        ]
        if fb.rerouted:
            lines.append('[재경로]')
        if fb.operations_triggered:
            lines.append(f'ops: {", ".join(fb.operations_triggered)}')

        fb_text = ' | '.join(lines)
        if self._signals:
            self._signals.feedback_update.emit(fb_text)

        if fb.path.poses:
            edge_changed = (fb.current_edge_id != self._current_edge_id)
            self._current_edge_id = fb.current_edge_id
            self._latest_path = fb.path

            if self._follow_goal_handle is None and not self._follow_replacing:
                # follow_path가 없으면 즉시 시작
                self._send_follow_path(fb.path)
            elif edge_changed and not self._follow_replacing:
                # edge 변경 시 기존 follow_path 취소 후 새 path로 교체
                self._log(f'[Follow] Edge {fb.current_edge_id} 진입 → follow_path 교체')
                self._replace_follow_path(fb.path)

    def _route_result_cb(self, future):
        result = future.result()
        status = result.status

        from action_msgs.msg import GoalStatus
        if status == GoalStatus.STATUS_SUCCEEDED:
            self._log('[Route] 경로 추적 완료 (SUCCEEDED)')
            if self._signals:
                self._signals.nav_finished.emit('SUCCEEDED')
        elif status == GoalStatus.STATUS_CANCELED:
            self._log('[Route] 경로 추적 취소됨 (CANCELED)')
            if self._signals:
                self._signals.nav_finished.emit('CANCELED')
        else:
            self._log(f'[Route] 경로 추적 종료 (status={status})')
            if self._signals:
                self._signals.nav_finished.emit(f'DONE:{status}')

        self._route_goal_handle = None

    # -----------------------------------------------------------------------
    # Follow Path 전달
    # -----------------------------------------------------------------------
    def _send_follow_path(self, path):
        if not self._follow_client.server_is_ready():
            return
        if self._follow_goal_handle is not None:
            return

        goal = FollowPath.Goal()
        goal.path = path
        goal.controller_id = 'FollowPath'
        goal.goal_checker_id = 'general_goal_checker'

        send_future = self._follow_client.send_goal_async(goal)
        send_future.add_done_callback(self._follow_goal_response_cb)

    def _replace_follow_path(self, path):
        """기존 follow_path를 취소하고 새 path로 교체 (edge 전환 시 호출)"""
        self._follow_replacing = True
        handle = self._follow_goal_handle
        if handle is not None:
            cancel_future = handle.cancel_goal_async()
            cancel_future.add_done_callback(
                lambda f, p=path: self._after_cancel(p)
            )
        else:
            self._follow_replacing = False
            self._send_follow_path(path)

    def _after_cancel(self, path):
        self._follow_goal_handle = None
        self._follow_replacing = False
        self._send_follow_path(path)

    def _follow_goal_response_cb(self, future):
        goal_handle = future.result()
        if goal_handle.accepted:
            self._follow_goal_handle = goal_handle
            result_future = goal_handle.get_result_async()
            result_future.add_done_callback(self._follow_result_cb)

    def _follow_result_cb(self, future):
        self._follow_goal_handle = None
        # follow_path 완료 즉시 최신 path로 재시작 (노드 간 gap 방지)
        if self._latest_path is not None:
            path = self._latest_path
            self._latest_path = None
            self._send_follow_path(path)

    # -----------------------------------------------------------------------
    # 정지
    # -----------------------------------------------------------------------
    def stop_all(self):
        # 상태 초기화
        self._latest_path = None
        self._current_edge_id = None
        self._follow_replacing = False

        # follow_path 취소
        if self._follow_goal_handle is not None:
            self._follow_goal_handle.cancel_goal_async()
            self._follow_goal_handle = None

        # compute_and_track_route 취소
        if self._route_goal_handle is not None:
            self._route_goal_handle.cancel_goal_async()
            self._log('[Route] 정지 요청 전송됨')
        else:
            self._log('[Route] 실행 중인 route 없음')


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------
class RouteGuiCommander(QWidget):
    def __init__(self, node: RouteCommanderNode):
        super().__init__()
        self.node = node

        self.signals = _Signals()
        self.signals.log.connect(self._append_log)
        self.signals.feedback_update.connect(self._update_feedback)
        self.signals.nav_finished.connect(self._on_nav_finished)
        self.node.set_signals(self.signals)

        self._graph_nodes: list[dict] = []

        self.setWindowTitle('Route GUI Commander')
        self.setMinimumWidth(520)
        self._build_ui()

    # -----------------------------------------------------------------------
    # UI 구성
    # -----------------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout()

        # --- Graph 불러오기 ---
        graph_group = QGroupBox('Graph')
        graph_layout = QVBoxLayout()

        file_row = QHBoxLayout()
        self.graph_path_edit = QLineEdit()
        self.graph_path_edit.setPlaceholderText('GeoJSON 파일 경로...')
        self.graph_path_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        file_row.addWidget(self.graph_path_edit)

        browse_btn = QPushButton('Browse')
        browse_btn.clicked.connect(self._on_browse)
        file_row.addWidget(browse_btn)

        load_btn = QPushButton('Load')
        load_btn.clicked.connect(self._on_load)
        load_btn.setStyleSheet('QPushButton { background-color: #2196F3; color: white; padding: 4px 12px; }')
        file_row.addWidget(load_btn)

        graph_layout.addLayout(file_row)
        graph_group.setLayout(graph_layout)
        root.addWidget(graph_group)

        # --- 노드 선택 ---
        node_group = QGroupBox('Route')
        node_layout = QVBoxLayout()

        start_row = QHBoxLayout()
        start_row.addWidget(QLabel('Start Node:'))
        self.start_combo = QComboBox()
        self.start_combo.setMinimumWidth(200)
        start_row.addWidget(self.start_combo)
        start_row.addStretch()
        node_layout.addLayout(start_row)

        goal_row = QHBoxLayout()
        goal_row.addWidget(QLabel('Goal Node: '))
        self.goal_combo = QComboBox()
        self.goal_combo.setMinimumWidth(200)
        goal_row.addWidget(self.goal_combo)
        goal_row.addStretch()
        node_layout.addLayout(goal_row)

        node_group.setLayout(node_layout)
        root.addWidget(node_group)

        # --- Start / Stop 버튼 ---
        btn_row = QHBoxLayout()

        self.start_btn = QPushButton('START')
        self.start_btn.clicked.connect(self._on_start)
        self.start_btn.setStyleSheet(
            'QPushButton { background-color: #4CAF50; color: white; font-size: 15px; padding: 10px; }'
            'QPushButton:disabled { background-color: #aaa; }'
        )
        btn_row.addWidget(self.start_btn)

        self.stop_btn = QPushButton('STOP')
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(
            'QPushButton { background-color: #f44336; color: white; font-size: 15px; padding: 10px; }'
            'QPushButton:disabled { background-color: #aaa; }'
        )
        btn_row.addWidget(self.stop_btn)

        root.addLayout(btn_row)

        # --- Feedback ---
        fb_group = QGroupBox('Feedback')
        fb_layout = QVBoxLayout()
        self.feedback_label = QLabel('대기 중...')
        self.feedback_label.setAlignment(Qt.AlignLeft)
        self.feedback_label.setWordWrap(True)
        fb_layout.addWidget(self.feedback_label)
        fb_group.setLayout(fb_layout)
        root.addWidget(fb_group)

        # --- 로그 ---
        root.addWidget(QLabel('Log:'))
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(180)
        root.addWidget(self.log_box)

        self.setLayout(root)

    # -----------------------------------------------------------------------
    # 이벤트 핸들러
    # -----------------------------------------------------------------------
    def _on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, '그래프 파일 선택', '', 'GeoJSON Files (*.geojson);;All Files (*)'
        )
        if path:
            self.graph_path_edit.setText(path)

    def _on_load(self):
        path = self.graph_path_edit.text().strip()
        if not path:
            self._append_log('[ERROR] 파일 경로를 입력하거나 Browse로 선택하세요')
            return

        # GeoJSON 파싱 → 노드 콤보박스 채우기
        try:
            with open(path, 'r') as f:
                geojson = json.load(f)
        except Exception as e:
            self._append_log(f'[ERROR] GeoJSON 파일 읽기 실패: {e}')
            return

        nodes = []
        for feat in geojson.get('features', []):
            geom = feat.get('geometry', {})
            props = feat.get('properties', {})
            if geom.get('type') == 'Point':
                nid = props.get('id', '?')
                coord = geom.get('coordinates', [0, 0])
                nodes.append({'id': nid, 'x': coord[0], 'y': coord[1]})

        if not nodes:
            self._append_log('[ERROR] 그래프에서 노드를 찾지 못했습니다')
            return

        self._graph_nodes = sorted(nodes, key=lambda n: n['id'])
        self._populate_combos()
        self._append_log(f'[OK] 노드 {len(nodes)}개 파싱 완료')

        # Route Server에 그래프 로드 (백그라운드)
        threading.Thread(
            target=lambda: self.node.load_graph(path), daemon=True
        ).start()

    def _populate_combos(self):
        self.start_combo.clear()
        self.goal_combo.clear()
        for n in self._graph_nodes:
            label = f"Node {n['id']}  ({n['x']:.1f}, {n['y']:.1f})"
            self.start_combo.addItem(label, n['id'])
            self.goal_combo.addItem(label, n['id'])

        # 기본값: start=0, goal=last
        if len(self._graph_nodes) > 1:
            self.goal_combo.setCurrentIndex(len(self._graph_nodes) - 1)

    def _on_start(self):
        start_id = self.start_combo.currentData()
        goal_id = self.goal_combo.currentData()

        if start_id is None or goal_id is None:
            self._append_log('[ERROR] Start/Goal 노드를 선택하세요')
            return

        if start_id == goal_id:
            self._append_log('[ERROR] Start와 Goal이 같습니다')
            return

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.feedback_label.setText('경로 계산 중...')

        threading.Thread(
            target=lambda: self.node.start_route(start_id, goal_id), daemon=True
        ).start()

    def _on_stop(self):
        threading.Thread(target=self.node.stop_all, daemon=True).start()

    # -----------------------------------------------------------------------
    # 시그널 슬롯
    # -----------------------------------------------------------------------
    def _append_log(self, msg: str):
        self.log_box.append(msg)
        self.log_box.verticalScrollBar().setValue(
            self.log_box.verticalScrollBar().maximum()
        )

    def _update_feedback(self, text: str):
        self.feedback_label.setText(text)

    def _on_nav_finished(self, status: str):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.feedback_label.setText(f'완료: {status}')

    def closeEvent(self, event):
        self.node.stop_all()
        rclpy.shutdown()
        event.accept()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    rclpy.init(args=sys.argv)
    node = RouteCommanderNode()

    # ROS spin을 백그라운드 스레드에서 실행
    spin_thread = threading.Thread(
        target=lambda: rclpy.spin(node), daemon=True
    )
    spin_thread.start()

    app = QApplication(sys.argv)
    window = RouteGuiCommander(node)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
