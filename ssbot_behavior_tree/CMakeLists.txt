cmake_minimum_required(VERSION 3.8)
project(ssbot_behavior_tree)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(nav2_behavior_tree REQUIRED)
find_package(nav2_msgs REQUIRED)
find_package(behaviortree_cpp REQUIRED)

# ── BT 커스텀 노드 플러그인 빌드 ──────────────────────
add_library(ssbot_bt_nodes SHARED
  src/bt_nodes/wait_action.cpp
)

target_include_directories(ssbot_bt_nodes PUBLIC
  include
)

ament_target_dependencies(ssbot_bt_nodes
  rclcpp
  nav2_behavior_tree
  nav2_msgs
  behaviortree_cpp
)

install(TARGETS ssbot_bt_nodes
  DESTINATION lib
)

install(DIRECTORY include/
  DESTINATION include
)
# ────────────────────────────────────────────────────

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

install(DIRECTORY behavior_trees
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
