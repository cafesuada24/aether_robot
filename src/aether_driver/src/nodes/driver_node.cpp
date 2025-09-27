#include <aether_driver/serial/serial.h>

#include <aether_interfaces/srv/velocity.hpp>
#include <algorithm>
#include <exception>
#include <functional>
#include <memory>
#include <rclcpp/executors.hpp>
#include <rclcpp/logger.hpp>
#include <rclcpp/node.hpp>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp/service.hpp>
#include <rclcpp/utilities.hpp>
#include <sstream>

#include "aether_driver/arduino.h"
#include "aether_interfaces/srv/velocity.hpp"

class DriverNode : public rclcpp::Node {
 public:
  DriverNode()
      : Node("driver"),
        drive_service_{create_service<aether_interfaces::srv::Velocity>(
            "~/drive",
            std::bind(&DriverNode::DriveServiceCallback, this,
                      std::placeholders::_1, std::placeholders::_2),
            10)} {
    declare_parameters();

    arduino_ = new aether_driver::Arduino(
        get_parameter("serial_port").as_string(),
        get_parameter("braudrate").as_int(),
        get_parameter("serial_timeout_ms").as_int(),
        get_parameter("encoder_resolution").as_int(),
        get_parameter("wheel_diameter_meter").as_double(),
        get_parameter("gear_reduction").as_double());

    RCLCPP_INFO(get_logger(), "Connected to ardunio");
  }

  ~DriverNode() {
    arduino_ = nullptr;
    RCLCPP_INFO(get_logger(), "Arduino connection closed");
  }

 private:
  void declare_parameters() {
    this->declare_parameter("serial_port", "/dev/ttyUSB0");
    this->declare_parameter("baudrate", 57600);
    this->declare_parameter("serial_timeout_ms", 500);
    this->declare_parameter("wheel_diameter_meter", 0.065);
    this->declare_parameter("encoder_resolution", 20);
    this->declare_parameter("gear_reduction", 1 / 48);
  }

  void DriveServiceCallback(
      const std::shared_ptr<aether_interfaces::srv::Velocity::Request> request,
      std::shared_ptr<aether_interfaces::srv::Velocity::Response> response) {
    if (arduino_ == nullptr) {
      RCLCPP_DEBUG(get_logger(), "Arduino driver is not initialized");
      throw new std::exception();
    }
    const auto vel_cmd{request->velocity_command.twist};
    response->code = 0;
    response->message = "Success";

    RCLCPP_INFO(get_logger(),
                "Incoming request: {linear: %.2f (m/s), angular: %.2f (rad/s)}",
                vel_cmd.linear.x, vel_cmd.angular.z);

    try {
      RCLCPP_DEBUG(get_logger(), "Driving with speeds: %fm/s, %fm/s", vel_cmd.linear.x,
                   vel_cmd.linear.x);
      arduino_->drive_m_per_sec(vel_cmd.linear.x, vel_cmd.linear.x);
    } catch (std::exception& ex) {
      response->code = 1;
      response->message = ex.what();
      RCLCPP_DEBUG(get_logger(), "Error driving robot: %s", ex.what());
    }
  }

  aether_driver::Arduino* arduino_;

  // Subscriber

  // Services
  rclcpp::Service<aether_interfaces::srv::Velocity>::SharedPtr drive_service_;
};

int main(int argc, char** argv) {
  rclcpp::init(argc, argv);

  try {
    rclcpp::spin(std::make_shared<DriverNode>());
  } catch (const aether_driver::SerialException& ex) {
    RCLCPP_ERROR(rclcpp::get_logger("aether_driver"), "%s", ex.what());
  }

  rclcpp::shutdown();
}
