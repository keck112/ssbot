#include "ssbot_behavior_tree/bt_nodes/wait_action.hpp"
#include "behaviortree_cpp/bt_factory.h"

namespace ssbot_bt
{

WaitAction::WaitAction(
  const std::string & xml_tag_name,
  const std::string & action_name,
  const BT::NodeConfiguration & conf)
: BtActionNode<nav2_msgs::action::Wait>(xml_tag_name, action_name, conf)
{
}

void WaitAction::on_tick()
{
  // BT XML의 wait_duration 포트에서 값을 읽어서 goal_ 에 세팅
  // goal_ 은 부모 클래스(BtActionNode)가 갖고 있는 멤버변수
  double wait_duration = 1.0;
  getInput("wait_duration", wait_duration);

  goal_.time.sec = static_cast<int>(wait_duration);
  goal_.time.nanosec = 0;
  
}

}  // namespace ssbot_bt

// BT 플러그인 등록 매크로
// Nav2 bt_navigator가 이 .so 파일을 로드할 때 이 이름으로 노드를 찾는다
BT_REGISTER_NODES(factory)
{
  BT::NodeBuilder builder = [](const std::string & name, const BT::NodeConfiguration & config) {
      return std::make_unique<ssbot_bt::WaitAction>(name, "wait", config);
    };

  factory.registerBuilder<ssbot_bt::WaitAction>("SsbotWait", builder);
}
