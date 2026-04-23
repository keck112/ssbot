#!/usr/bin/env python3
import os
import subprocess

import rclpy
from cartographer_ros_msgs.srv import FinishTrajectory, WriteState


def call_service(node, client, request, timeout_sec=10.0):
    future = client.call_async(request)
    rclpy.spin_until_future_complete(node, future, timeout_sec=timeout_sec)
    if not future.done():
        return None, 'timeout'
    return future.result(), None


def main():
    rclpy.init()
    node = rclpy.create_node('map_saver')

    finish_client = node.create_client(FinishTrajectory, '/finish_trajectory')
    write_client = node.create_client(WriteState, '/write_state')

    # 저장 경로 입력
    print('\n=== Cartographer Map Saver ===')
    save_path = input('저장 경로를 입력하세요 (예: /home/ss/maps/my_map): ').strip()

    if not save_path:
        print('[ERROR] 경로가 입력되지 않았습니다.')
        node.destroy_node()
        rclpy.shutdown()
        return

    pbstream_path = save_path if save_path.endswith('.pbstream') else save_path + '.pbstream'
    map_stem = pbstream_path.replace('.pbstream', '')

    save_dir = os.path.dirname(pbstream_path)
    if save_dir and not os.path.exists(save_dir):
        os.makedirs(save_dir, exist_ok=True)
        print(f'[INFO] 디렉토리 생성: {save_dir}')

    # finish_trajectory 서비스 대기
    print('\n[1/3] finish_trajectory 서비스 대기 중...')
    if not finish_client.wait_for_service(timeout_sec=5.0):
        print('[ERROR] finish_trajectory 서비스를 찾을 수 없습니다. Cartographer가 실행 중인지 확인하세요.')
        node.destroy_node()
        rclpy.shutdown()
        return

    req = FinishTrajectory.Request()
    req.trajectory_id = 0
    result, err = call_service(node, finish_client, req)

    if err:
        print(f'[ERROR] finish_trajectory 타임아웃')
        node.destroy_node()
        rclpy.shutdown()
        return

    if result.status.code != 0:
        print(f'[ERROR] finish_trajectory 실패: {result.status.message}')
        node.destroy_node()
        rclpy.shutdown()
        return

    print(f'[OK] trajectory_id=0 종료 완료')

    # write_state 서비스 대기
    print('\n[2/3] pbstream 저장 중...')
    if not write_client.wait_for_service(timeout_sec=5.0):
        print('[ERROR] write_state 서비스를 찾을 수 없습니다.')
        node.destroy_node()
        rclpy.shutdown()
        return

    req = WriteState.Request()
    req.filename = pbstream_path
    req.include_unfinished_submaps = True
    result, err = call_service(node, write_client, req)

    if err:
        print(f'[ERROR] write_state 타임아웃')
        node.destroy_node()
        rclpy.shutdown()
        return

    if result.status.code != 0:
        print(f'[ERROR] write_state 실패: {result.status.message}')
        node.destroy_node()
        rclpy.shutdown()
        return

    print(f'[OK] pbstream 저장 완료: {pbstream_path}')

    node.destroy_node()
    rclpy.shutdown()

    # pgm + yaml 변환
    print('\n[3/3] pgm + yaml 변환 중...')
    cmd = [
        'ros2', 'run', 'cartographer_ros', 'cartographer_pbstream_to_ros_map',
        f'-pbstream_filename={pbstream_path}',
        f'-map_filestem={map_stem}',
        '-resolution=0.05',
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)

    if proc.returncode != 0:
        print(f'[ERROR] pgm/yaml 변환 실패:\n{proc.stderr}')
        return

    print(f'[OK] pgm 저장 완료: {map_stem}.pgm')
    print(f'[OK] yaml 저장 완료: {map_stem}.yaml')
    print(f'\n=== 저장 완료 ===')
    print(f'  pbstream : {pbstream_path}')
    print(f'  pgm      : {map_stem}.pgm')
    print(f'  yaml     : {map_stem}.yaml')


if __name__ == '__main__':
    main()
