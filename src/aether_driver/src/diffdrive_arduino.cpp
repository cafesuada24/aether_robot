#include "aether_driver/diffdrive_arduino.h"

#include <chrono>
#include <hardware_interface/hardware_component_interface.hpp>
#include <hardware_interface/types/hardware_component_interface_params.hpp>
#include <rclcpp/qos.hpp>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_lifecycle/state.hpp>
#include <realtime_tools/realtime_publisher.hpp>

#include "aether_interfaces/msg/motor_speed.hpp"
#include "hardware_interface/types/hardware_interface_type_values.hpp"

namespace aether_driver {
DiffDriveArduino::DiffDriveArduino()
    : logger_(rclcpp::get_logger("DiffDriveArduino")) {}

hardware_interface::CallbackReturn DiffDriveArduino::on_init(
    const hardware_interface::HardwareComponentInterfaceParams& info) {
  if (hardware_interface::SystemInterface::on_init(info) !=
      CallbackReturn::SUCCESS) {
    return hardware_interface::CallbackReturn::ERROR;
  }

  RCLCPP_INFO(logger_, "Intializing...");

  time_ = std::chrono::system_clock::now();

  cfg_.left_wheel_name = info_.hardware_parameters["left_wheel_name"];
  cfg_.right_wheel_name = info_.hardware_parameters["right_wheel_name"];
  cfg_.loop_rate_ms = std::stof(info_.hardware_parameters["loop_rate_ms"]);
  cfg_.device = info_.hardware_parameters["device"];
  cfg_.baud_rate = std::stoi(info_.hardware_parameters["baud_rate"]);
  cfg_.timeout_ms = std::stoi(info_.hardware_parameters["timeout_ms"]);
  cfg_.enc_counts_per_rev =
      std::stoi(info_.hardware_parameters["enc_counts_per_rev"]);

  // Set up the wheels
  l_wheel_.setup(cfg_.left_wheel_name, cfg_.enc_counts_per_rev);
  r_wheel_.setup(cfg_.right_wheel_name, cfg_.enc_counts_per_rev);

  // Set up the Arduino
  // arduino_.setup(cfg_.device, cfg_.baud_rate, cfg_.timeout_ms,
  //               cfg_.enc_counts_per_rev, 0.065);

  RCLCPP_INFO(logger_, "Finished initialization");

  return hardware_interface::CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn DiffDriveArduino::on_configure(
    [[maybe_unused]] const rclcpp_lifecycle::State& previous_state) {
  RCLCPP_INFO(logger_, "Configuring");

  auto node_ptr{get_node()};
  if (!node_ptr) {
    RCLCPP_ERROR(get_node()->get_logger(),
                 "Unable to lock node ptr in on_configure");
    return CallbackReturn::ERROR;
  }

  encoder_subscriber_ =
      node_ptr->create_subscription<aether_interfaces::msg::Encoder>(
          "/sensor/encoder", rclcpp::SensorDataQoS(),
          std::bind(&DiffDriveArduino::EncoderCallback, this,
                    std::placeholders::_1));
  encoder_buffer_.initRT(aether_interfaces::msg::Encoder::SharedPtr());


  rclcpp::QoS qos(1);
  qos.best_effort();
  qos.durability_volatile();
  qos.keep_last(1);

  motor_speed_publisher_ = std::make_unique<
      realtime_tools::RealtimePublisher<aether_interfaces::msg::MotorSpeed>>(
      node_ptr->create_publisher<aether_interfaces::msg::MotorSpeed>(
          "arduino_command/rpm", qos));

  // arduino_.connect();

  // if (!arduino_.connected()) {
  //   RCLCPP_WARN(logger_,
  //               "Unable to connect to arduino, please check and try again.");
  //   return CallbackReturn::FAILURE;
  // }

  // RCLCPP_INFO(logger_, "Connected to arduino nano.");

  // arduino_.send_empty_message();
  // if (arduino_.set_pid_values(400, 0, 2, 100) != 0) {
  //   RCLCPP_ERROR(logger_, "Couldn't set PID values");
  //   return hardware_interface::CallbackReturn::ERROR;
  // }

  RCLCPP_INFO(logger_, "Finished configuration.");
  return hardware_interface::CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn DiffDriveArduino::on_cleanup(
    [[maybe_unused]] const rclcpp_lifecycle::State& previous_state) {
  RCLCPP_INFO(logger_, "Cleaning up...");

  // arduino_.close();

  return hardware_interface::CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn DiffDriveArduino::on_activate(
    [[maybe_unused]] const rclcpp_lifecycle::State& previous_state) {
  // auto initial_value{aether_interfaces::msg::Encoder::SharedPtr()};
  // initial_value->left = 0;
  // initial_value->right = 0;
  encoder_buffer_.initRT(aether_interfaces::msg::Encoder::SharedPtr());
  return CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn DiffDriveArduino::on_deactivate(
    [[maybe_unused]] const rclcpp_lifecycle::State& previous_state) {
  encoder_buffer_.reset();
  // arduino_.close();
  // if (arduino_.connected()) {
  //   RCLCPP_WARN(
  //       logger_,
  //       "Unable to disconnect from arduino, please check and try again.");
  //   return CallbackReturn::FAILURE;
  // }

  RCLCPP_INFO(logger_, "Successfully disconnected from arduino nano.");
  return CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn DiffDriveArduino::on_shutdown(
    [[maybe_unused]] const rclcpp_lifecycle::State& previous_state) {
  // if (arduino_.connected()) {
  //   arduino_.close();
  // }
  return CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn DiffDriveArduino::on_error(
    [[maybe_unused]] const rclcpp_lifecycle::State& previous_state) {
  RCLCPP_ERROR(logger_, "Error happened.");
  return CallbackReturn::SUCCESS;
}

std::vector<hardware_interface::StateInterface>
DiffDriveArduino::export_state_interfaces() {
  // We need to set up a position and a velocity interface for each wheel

  std::vector<hardware_interface::StateInterface> state_interfaces;

  state_interfaces.emplace_back(hardware_interface::StateInterface(
      l_wheel_.name, hardware_interface::HW_IF_VELOCITY, &l_wheel_.vel));
  state_interfaces.emplace_back(hardware_interface::StateInterface(
      l_wheel_.name, hardware_interface::HW_IF_POSITION, &l_wheel_.pos));
  state_interfaces.emplace_back(hardware_interface::StateInterface(
      r_wheel_.name, hardware_interface::HW_IF_VELOCITY, &r_wheel_.vel));
  state_interfaces.emplace_back(hardware_interface::StateInterface(
      r_wheel_.name, hardware_interface::HW_IF_POSITION, &r_wheel_.pos));

  return state_interfaces;
}

std::vector<hardware_interface::CommandInterface>
DiffDriveArduino::export_command_interfaces() {
  // We need to set up a velocity command interface for each wheel

  std::vector<hardware_interface::CommandInterface> command_interfaces;

  command_interfaces.emplace_back(hardware_interface::CommandInterface(
      l_wheel_.name, hardware_interface::HW_IF_VELOCITY, &l_wheel_.cmd));
  command_interfaces.emplace_back(hardware_interface::CommandInterface(
      r_wheel_.name, hardware_interface::HW_IF_VELOCITY, &r_wheel_.cmd));

  return command_interfaces;
}

hardware_interface::return_type DiffDriveArduino::read(
    const rclcpp::Time&, const rclcpp::Duration& period) {
  // if (!arduino_.connected()) {
  //   return hardware_interface::return_type::ERROR;
  // }

  const auto encoder_msg{encoder_buffer_.readFromNonRT()};

  if (nullptr == encoder_msg) {
    return hardware_interface::return_type::OK;
  }

  // arduino_.read_encoder_values(l_wheel_.enc, r_wheel_.enc);
  l_wheel_.enc = encoder_msg->get()->left;
  r_wheel_.enc = encoder_msg->get()->right;

  const auto delta_seconds{period.seconds()};
  double pos_prev{l_wheel_.pos};
  l_wheel_.pos = l_wheel_.calc_enc_angle();
  l_wheel_.vel = (l_wheel_.pos - pos_prev) / delta_seconds;

  pos_prev = r_wheel_.pos;
  r_wheel_.pos = r_wheel_.calc_enc_angle();
  r_wheel_.vel = (r_wheel_.pos - pos_prev) / delta_seconds;

  return hardware_interface::return_type::OK;
}

hardware_interface::return_type DiffDriveArduino::write(
    const rclcpp::Time&, const rclcpp::Duration&) {
  // if (!arduino_.connected()) {
  //   return hardware_interface::return_type::ERROR;
  // }

  // const int16_t left_ticks_per_loop{static_cast<int16_t>(l_wheel_.cmd /
  // l_wheel_.rads_per_count /
  //                                cfg_.loop_rate_ms)};
  // const int16_t right_ticks_per_loop{static_cast<int16_t>(r_wheel_.cmd /
  // r_wheel_.rads_per_count /
  //                                 cfg_.loop_rate_ms)};
  //
  // RCLCPP_DEBUG(logger_, "passing ticks per loop: %d %d", left_ticks_per_loop,
  // right_ticks_per_loop); arduino_.drive(left_ticks_per_loop,
  // right_ticks_per_loop);
  //
  const auto left_rpm{l_wheel_.cmd * 60.0 / (2 * M_PI)};
  const auto right_rpm{r_wheel_.cmd * 60 / (2 * M_PI)};
  // arduino_.drive_rpm(left_rpm, right_rpm);
  //
  //

  aether_interfaces::msg::MotorSpeed cmd{};
  cmd.left = left_rpm;
  cmd.right = right_rpm;
  motor_speed_publisher_->try_publish(cmd);

  return hardware_interface::return_type::OK;
}

void DiffDriveArduino::EncoderCallback(
    const aether_interfaces::msg::Encoder::SharedPtr msg) {
  encoder_buffer_.writeFromNonRT(msg);
}
}  // namespace aether_driver

#include "pluginlib/class_list_macros.hpp"

PLUGINLIB_EXPORT_CLASS(aether_driver::DiffDriveArduino,
                       hardware_interface::SystemInterface)
