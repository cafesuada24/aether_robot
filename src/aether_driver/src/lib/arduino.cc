#include <aether_driver/arduino.h>

#include <cmath>
#include <iostream>

namespace aether_driver {
Arduino::Arduino(const std::string& serial, const uint16_t braud,
                 const uint64_t timeout_ms, const uint16_t encoder_resolution,
                 const float wheel_diameter_meter, const float gear_reduction)
    : encoder_resolution_{encoder_resolution},
      wheel_diameter_meter_{wheel_diameter_meter},
      gear_reduction_{gear_reduction} {
  auto timeout{aether_driver::Timeout::simpleTimeout(timeout_ms)};

  serial_.setPort(serial);
  serial_.setBaudrate(braud);
  serial_.setTimeout(timeout);

  serial_.open();

  if (!serial_.isOpen()) {
    throw aether_driver::SerialException("Port is not opened");
  }
}

bool Arduino::drive_m_per_sec(const float left_speed, const float right_speed) {
  if (wheel_diameter_meter_ <= 0) {
    std::cerr << "wheel diameter is not set";
    throw std::exception();
  }

  if (encoder_resolution_ <= 0) {
    std::cerr << "encoder resolution is not set";
    throw std::exception();
  }

  if (gear_reduction_ <= 0) {
    std::cerr << "gear reduction is not set";
    throw std::exception();
  }

  if (left_speed <= 0 || right_speed <= 0) {
    std::cerr << "expected positive speeds, passed values: " << "{ "
              << left_speed << ", " << right_speed << " }";
    throw std::exception();
  }

  const auto left_rev_per_sec{left_speed / (wheel_diameter_meter_ * M_PI)};
  const auto right_rev_per_sec{right_speed / (wheel_diameter_meter_ * M_PI)};
  const auto left_ticks_per_loop{static_cast<int>(
      left_rev_per_sec * encoder_resolution_ * PID_INTERVAL * gear_reduction_)};
  const auto right_ticks_per_loop{
      static_cast<int>(right_rev_per_sec * encoder_resolution_ * PID_INTERVAL *
                       gear_reduction_)};

  return drive(left_ticks_per_loop, right_ticks_per_loop);
}

bool Arduino::drive(const uint16_t left_ticks_per_loop,
                    const uint16_t right_ticks_per_loop) {
  std::ostringstream oss{};

  oss << "m " << left_ticks_per_loop << ' ' << right_ticks_per_loop << '\r';

  serial_.write(oss.str());

  return std::strcmp(serial_.read(255).c_str(), "OK") == 0;
}
}  // namespace aether_driver
