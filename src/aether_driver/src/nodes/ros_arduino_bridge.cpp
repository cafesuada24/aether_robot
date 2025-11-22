#include <rclcpp/qos.hpp>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/imu.hpp>

#include "aether_driver/arduino.h"
#include "aether_driver/sensors_data.h"
#include "aether_interfaces/msg/encoder.hpp"
#include "aether_interfaces/msg/motor_speed.hpp"

using namespace std::chrono_literals;

namespace aether_driver {
class ROSArduinoBridge : public rclcpp::Node {
 public:
  ROSArduinoBridge()
      : Node("ros_arduino_bridge"),
        timer_{create_wall_timer(
            20ms, std::bind(&ROSArduinoBridge::TimerCallback, this))},
        imu_publisher_{create_publisher<sensor_msgs::msg::Imu>(
            "/sensor/imu", rclcpp::SensorDataQoS())},
        encoder_publisher_{create_publisher<aether_interfaces::msg::Encoder>(
            "/sensor/encoder", rclcpp::SensorDataQoS())} {
    declare_parameters();

    rclcpp::QoS qos(1);
    qos.best_effort();
    qos.durability_volatile();
    qos.keep_last(1);

    motor_speed_sub_ = create_subscription<aether_interfaces::msg::MotorSpeed>(
        "arduino_command/rpm", qos,
        std::bind(&ROSArduinoBridge::MotorSpeedCallback, this,
                  std::placeholders::_1));

    arduino_.setup(this->get_parameter("serial_port").as_string(),
                   this->get_parameter("baudrate").as_int(),
                   this->get_parameter("serial_timeout_ms").as_int(),
                   this->get_parameter("encoder_count_per_rev").as_int(),
                   this->get_parameter("wheel_diameter_meter").as_double());

    arduino_.connect();

    if (!arduino_.connected()) {
      RCLCPP_WARN(get_logger(),
                  "Unable to connect to arduino, please check and try again.");
    }
  }

 private:
  aether_driver::Arduino arduino_{};
  rclcpp::TimerBase::SharedPtr timer_;
  rclcpp::Publisher<sensor_msgs::msg::Imu>::SharedPtr imu_publisher_;
  rclcpp::Publisher<aether_interfaces::msg::Encoder>::SharedPtr
      encoder_publisher_;
  // rclcpp::Subscription<aether_interfaces> vel_cmd_subscriber_;

  std::atomic<double> left_motor_rpm_{0};
  std::atomic<double> right_motor_rpm_{0};
  rclcpp::Subscription<aether_interfaces::msg::MotorSpeed>::SharedPtr
      motor_speed_sub_;
  void MotorSpeedCallback(
      const aether_interfaces::msg::MotorSpeed::ConstSharedPtr msg) {
    left_motor_rpm_.store(msg->left);
    right_motor_rpm_.store(msg->right);
  }

  void TimerCallback() {
    if (!arduino_.connected()) {
      return;
    }

    arduino_.drive_rpm(left_motor_rpm_.load(), right_motor_rpm_.load());

    aether_driver::SensorsData data{};
    arduino_.read_sensors(data);

    sensor_msgs::msg::Imu imu_data{};
    imu_data.angular_velocity.x = data.imu.gyro[0];
    imu_data.angular_velocity.y = data.imu.gyro[1];
    imu_data.angular_velocity.z = data.imu.gyro[2];
    imu_data.linear_acceleration.x = data.imu.linear[0];
    imu_data.linear_acceleration.y = data.imu.linear[1];
    imu_data.linear_acceleration.z = data.imu.linear[2];

    imu_publisher_->publish(imu_data);

    aether_interfaces::msg::Encoder enc_data{};
    enc_data.left = data.left_enc;
    enc_data.right = data.right_enc;
    encoder_publisher_->publish(enc_data);
  }

  void declare_parameters() {
    this->declare_parameter("serial_port", "/dev/ttyUSB0");
    this->declare_parameter("baudrate", 57600);
    this->declare_parameter("serial_timeout_ms", 1000);
    this->declare_parameter("encoder_count_per_rev", 20);
    this->declare_parameter("wheel_diameter_meter", 0.065);
  }
};

};  // namespace aether_driver

int main(int argc, char** argv) {
  rclcpp::init(argc, argv);

  try {
    rclcpp::spin(std::make_shared<aether_driver::ROSArduinoBridge>());
  } catch (const aether_driver::SerialException& ex) {
    RCLCPP_ERROR(rclcpp::get_logger("ros_arduino_bridge"), "%s", ex.what());
  }

  rclcpp::shutdown();
}
