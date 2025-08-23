#include <functional>
#include <rclcpp/duration.hpp>
#include <rclcpp/logging.hpp>
#include <rclcpp/node.hpp>
#include <rclcpp/publisher.hpp>
#include <rclcpp/subscription.hpp>
#include <rclcpp/time.hpp>

#include "geometry_msgs/msg/point.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "rclcpp_components/register_node_macro.hpp"

namespace object_tracker::node {

using std::placeholders::_1;

using namespace std::chrono_literals;

class ObjectFollow : public rclcpp::Node {
 public:
  explicit ObjectFollow(const rclcpp::NodeOptions& options = rclcpp::NodeOptions())
      : Node("object_follow", options),
        timer_{create_wall_timer(
            50ms, std::bind(&ObjectFollow::TimerCallback, this))},
        detected_object_sub_{create_subscription<geometry_msgs::msg::Point>(
            "/detected_object", 10,
            std::bind(&ObjectFollow::DetectedObjectRcvCallback, this, _1))},
        vel_pub_{create_publisher<geometry_msgs::msg::Twist>("/out_vel", 10)} {
    ReadParameters();
  
    last_rcv_time_ = now() - rcv_timeout_secs_ - 1s;
  }

 private:
  void ReadParameters() {
    this->declare_parameter("rcv_timeout_secs", 1.0);
    this->declare_parameter("max_size_thresh", 0.1);
    this->declare_parameter("forward_chase_speed", 0.1);
    this->declare_parameter("angular_search_speed", 0.5);
    this->declare_parameter("angular_chase_multiplier", 0.7);
    this->declare_parameter("max_dist_thresh", 0.1);
    this->declare_parameter("filter_value", 0.1);

    this->rcv_timeout_secs_ = std::chrono::duration<double>(
        this->get_parameter("rcv_timeout_secs").as_double());
    this->angular_search_speed_ =
        this->get_parameter("angular_search_speed").as_double();
    this->angular_chase_multiplier_ =
        this->get_parameter("angular_chase_multiplier").as_double();
    this->forward_chase_speed_ =
        this->get_parameter("forward_chase_speed").as_double();
    this->max_dist_thresh_ = this->get_parameter("max_dist_thresh").as_double();
    this->filter_value_ = this->get_parameter("filter_value").as_double();
  }

  void TimerCallback() {
    geometry_msgs::msg::Twist msg_to_pub{};

    if (now() - last_rcv_time_ < rcv_timeout_secs_) {
      RCLCPP_INFO(get_logger(), "Target: {dist: %.2lf, h-offset: %.2lf}",
                  target_distance_, target_h_offset_);
      if (target_distance_ < max_dist_thresh_) {
        msg_to_pub.linear.x = this->forward_chase_speed_;
      }
      msg_to_pub.angular.z = -angular_chase_multiplier_ * target_h_offset_;
    } else {
      RCLCPP_INFO(get_logger(), "Target lost");
      msg_to_pub.angular.z = this->angular_search_speed_;
    }

    vel_pub_->publish(msg_to_pub);
  }

  void DetectedObjectRcvCallback(geometry_msgs::msg::Point::UniquePtr msg) {
    this->target_h_offset_ =
        this->target_h_offset_ * filter_value_ + msg->x * (1.0 - filter_value_);
    this->target_distance_ =
        this->target_distance_ * filter_value_ + msg->z * (1.0 - filter_value_);
    last_rcv_time_ = now();
  }

  rclcpp::Duration rcv_timeout_secs_{1s};
  double forward_chase_speed_;
  double angular_search_speed_;
  double angular_chase_multiplier_;
  double max_dist_thresh_;
  double filter_value_;

  double target_distance_;
  double target_h_offset_;

  rclcpp::Time last_rcv_time_;

  rclcpp::TimerBase::SharedPtr timer_;

  rclcpp::Subscription<geometry_msgs::msg::Point>::SharedPtr
      detected_object_sub_;
  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr vel_pub_;
};
}  // namespace object_tracker::node

RCLCPP_COMPONENTS_REGISTER_NODE(object_tracker::node::ObjectFollow);
