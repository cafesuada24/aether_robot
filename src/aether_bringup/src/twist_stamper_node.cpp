#include <rclcpp/rclcpp.hpp>

#include "geometry_msgs/msg/twist.hpp"
#include "geometry_msgs/msg/twist_stamped.hpp"

class TwistStamper : public rclcpp::Node {
 public:
  TwistStamper() : Node("twist_stamper") {
    declare_parameters();

    const std::string input_topic{
        this->get_parameter("input_topic").as_string()};
    const std::string output_topic{
        this->get_parameter("output_topic").as_string()};
    this->frame_id_ = this->get_parameter("frame_id").as_string();

    subscription_ = this->create_subscription<geometry_msgs::msg::Twist>(
        input_topic, 10,
        std::bind(&TwistStamper::twist_callback, this, std::placeholders::_1));
    RCLCPP_INFO(this->get_logger(), "Subscribed to %s", input_topic.c_str());

    publisher_ = this->create_publisher<geometry_msgs::msg::TwistStamped>(
        output_topic, 10);
    RCLCPP_INFO(this->get_logger(), "Publishing to %s", output_topic.c_str());
  }

 private:
  void declare_parameters() {
    this->declare_parameter("input_topic", "/cmd_vel");
    this->declare_parameter("output_topic", "/cmd_vel_stamped");
    this->declare_parameter("frame_id", "base_link");
  }

  void twist_callback(const geometry_msgs::msg::Twist::SharedPtr msg) {
    auto stamped_twist_msg{
        std::make_unique<geometry_msgs::msg::TwistStamped>()};

    stamped_twist_msg->header.stamp = this->get_clock()->now();
    stamped_twist_msg->header.frame_id = this->frame_id_;

    stamped_twist_msg->twist.linear = msg->linear;
    stamped_twist_msg->twist.angular = msg->angular;

    publisher_->publish(std::move(stamped_twist_msg));
    RCLCPP_DEBUG(this->get_logger(), "Published TwistStamped message");
  }

  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr subscription_{};
  rclcpp::Publisher<geometry_msgs::msg::TwistStamped>::SharedPtr publisher_{};
  std::string frame_id_{};
};

int main(int argc, char *argv[]) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<TwistStamper>());
  rclcpp::shutdown();
  return 0;
}
