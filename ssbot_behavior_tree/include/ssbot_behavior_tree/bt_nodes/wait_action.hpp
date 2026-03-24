#ifndef SSBOT_BEHAVIOR_TREE__BT_NODES__WAIT_ACTION_HPP_
#define SSBOT_BEHAVIOR_TREE__BT_NODES__WAIT_ACTION_HPP_

#include <string>

#include "nav2_behavior_tree/bt_action_node.hpp"
#include "nav2_msgs/action/wait.hpp"

namespace ssbot_bt
{

/**
 * BtActionNode 상속 구조:
 *   BT::ActionNodeBase  (BehaviorTree.CPP)
 *       └── nav2_behavior_tree::BtActionNode<ActionT>  (Nav2)
 *               └── ssbot_bt::WaitAction  (우리가 만드는 것)
 *
 * BtActionNode<nav2_msgs::action::Wait> 를 상속하면
 * Action 서버 연결, Goal 전송, Feedback/Result 처리를 자동으로 해준다.
 * 우리는 on_tick() 에서 goal_ 을 세팅하기만 하면 된다.
 */
class WaitAction : public nav2_behavior_tree::BtActionNode<nav2_msgs::action::Wait>
{
public:
  WaitAction(
    const std::string & xml_tag_name,
    const std::string & action_name,
    const BT::NodeConfiguration & conf);

  // BT 틱마다 호출 — goal_ 세팅
  void on_tick() override;

  // BT XML에서 받을 포트(입력값) 정의
  static BT::PortsList providedPorts()
  {
    return providedBasicPorts({
      BT::InputPort<double>("wait_duration", 1.0, "대기 시간 (초)")
    });
  }
};

}  // namespace ssbot_bt

#endif  // SSBOT_BEHAVIOR_TREE__BT_NODES__WAIT_ACTION_HPP_
