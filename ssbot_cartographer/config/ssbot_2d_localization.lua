include "ssbot_2d.lua"

TRAJECTORY_BUILDER.pure_localization_trimmer = {
  max_submaps_to_keep = 3,
}

-- 포인트 수 줄이기 (성능 개선)
TRAJECTORY_BUILDER_2D.voxel_filter_size = 0.05
TRAJECTORY_BUILDER_2D.adaptive_voxel_filter.max_length = 0.9
TRAJECTORY_BUILDER_2D.adaptive_voxel_filter.min_num_points = 100

-- motion filter 조정
TRAJECTORY_BUILDER_2D.motion_filter.max_time_seconds = 0.5
TRAJECTORY_BUILDER_2D.motion_filter.max_distance_meters = 0.1
TRAJECTORY_BUILDER_2D.motion_filter.max_angle_radians = math.rad(0.5)

-- pose graph 최적화 빈도 줄이기
POSE_GRAPH.optimize_every_n_nodes = 40
POSE_GRAPH.global_sampling_ratio = 0.002
POSE_GRAPH.constraint_builder.sampling_ratio = 0.1
POSE_GRAPH.constraint_builder.min_score = 0.55
POSE_GRAPH.global_constraint_search_after_n_seconds = 15.

return options
