#include <rclcpp/node.hpp>
#include "aether_driver/arduino.h"

class ROSArduinoBridge : public rclcpp::Node {
public:
  ROSArduinoBridge() : Node("ros_arduino_bridge") {
    declare_parameters();
  }

private:
  aether_driver::Arduino arduino_ {};

  void declare_parameters() {
    this->declare_parameter("serial_port", "/dev/ttyUSB0");
    this->declare_parameter("baudrate", 57600);
    this->declare_parameter("serial_timeout_ms", 1000);
  }
};
