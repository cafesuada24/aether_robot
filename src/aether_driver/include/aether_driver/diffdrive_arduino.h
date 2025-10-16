#ifndef AETHER_DRIVER__DIFFDRIVE_ARDUINO_H_
#define AETHER_DRIVER__DIFFDRIVE_ARDUINO_H_

#include <unistd.h>

#include <chrono>
#include <cstring>
#include <hardware_interface/hardware_component_interface.hpp>
#include <rclcpp_lifecycle/state.hpp>

#include "aether_driver/arduino.h"
#include "config.h"
#include "hardware_interface/handle.hpp"
#include "hardware_interface/system_interface.hpp"
#include "hardware_interface/types/hardware_interface_return_values.hpp"
#include "wheel.h"

namespace aether_driver {

class DiffDriveArduino : public hardware_interface::SystemInterface {
 public:
  DiffDriveArduino();

  hardware_interface::CallbackReturn on_configure(const rclcpp_lifecycle::State& previous_state) override;
  hardware_interface::CallbackReturn on_cleanup(const rclcpp_lifecycle::State& previous_state) override;
  hardware_interface::CallbackReturn on_shutdown(const rclcpp_lifecycle::State& previous_state) override;
  hardware_interface::CallbackReturn on_error(const rclcpp_lifecycle::State& previous_state) override;
  hardware_interface::CallbackReturn on_activate(const rclcpp_lifecycle::State& previous_state) override;
  hardware_interface::CallbackReturn on_deactivate(const rclcpp_lifecycle::State& previous_state) override;


  std::vector<hardware_interface::StateInterface> export_state_interfaces() override;

  std::vector<hardware_interface::CommandInterface> export_command_interfaces() override;

  hardware_interface::CallbackReturn on_init(const hardware_interface::HardwareComponentInterfaceParams &hardware_info) override;

  hardware_interface::return_type read(const rclcpp::Time&,
                                        const rclcpp::Duration&) override;

  hardware_interface::return_type write(const rclcpp::Time&,
                                        const rclcpp::Duration&) override;

 private:
  Config cfg_{};
  Arduino arduino_ {};

  Wheel l_wheel_{};
  Wheel r_wheel_{};

  rclcpp::Logger logger_;

  std::chrono::time_point<std::chrono::system_clock> time_{};
};
}  // namespace aether_driver

#endif  // AETHER_DRIVER__DIFFDRIVE_ARDUINO_H_
