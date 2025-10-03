#include <aether_driver/arduino.h>

#include <algorithm>
#include <cmath>
#include <iostream>

namespace aether_driver {
Arduino::Arduino(const std::string& serial, const uint16_t braud,
                 const uint64_t timeout_ms, const uint16_t encoder_resolution,
                 const float wheel_diameter_meter, const float gear_reduction,
                 const float min_linear_speed_m_per_s,
                 const float max_linear_speed_m_per_s)

    : encoder_resolution_{encoder_resolution},
      wheel_diameter_meter_{wheel_diameter_meter},
      gear_reduction_{gear_reduction},
      min_linear_speed_m_per_s_{min_linear_speed_m_per_s},
      max_linear_speed_m_per_s_{max_linear_speed_m_per_s} {
  auto timeout{aether_driver::Timeout::simpleTimeout(timeout_ms)};

  serial_.setPort(serial);
  serial_.setBaudrate(braud);
  serial_.setTimeout(timeout);

  serial_.open();

  if (!serial_.isOpen()) {
    throw aether_driver::SerialException("Port is not opened");
  }
}

int16_t Arduino::calc_ticks_per_loop(const float speed) const {
  if (wheel_diameter_meter_ <= 0) {
    std::cerr << "wheel diameter is not set";
    throw std::exception();
  }

  if (encoder_resolution_ <= 0) {
    std::cerr << "encoder resolution is not set";
    throw std::exception();
  }

  return std::round(speed / (wheel_diameter_meter_ * M_PI * PID_RATE) * encoder_resolution_);
}

float Arduino::ensure_speed(const float speed) const {
  float spd {0.0};
  if (speed != 0.0) {
    spd = std::clamp((speed < 0 ? -1 : 1) * speed, min_linear_speed_m_per_s_, max_linear_speed_m_per_s_);
    if (speed < 0) {
      spd *= -1;
    }
  }
  return spd;
};

bool Arduino::drive_m_per_sec(const float left_speed, const float right_speed) {
  const auto left_spd {ensure_speed(left_speed)};
  const auto right_spd {ensure_speed(right_speed)};

  // std::ostringstream oss{};
  //
  // if (left_speed == 0.0 && right_speed == 0.0) {
  //   oss << "o ";
  // } else {
  //   oss << "o "
  //       << static_cast<int>(std::clamp(left_speed, 0.3f, 0.8f) / 0.8 * 180)
  //       << ' '
  //       << static_cast<int>(std::clamp(right_speed, 0.3f, 0.8f) / 0.8 * 180)
  //       << '\r';
  // }
  //
  // serial_.write(oss.str());
  //
  // return std::strcmp(serial_.read(2).c_str(), "OK") == 0;


  // if (gear_reduction_ <= 0) {
  //   std::cerr << "gear reduction is not set";
  //   throw std::exception();
  // }

  // if (left_speed <= 0 || right_speed <= 0) {
  //   std::cerr << "expected positive speeds, passed values: " << "{ "
  //             << left_speed << ", " << right_speed << " }";
  //   throw std::exception();
  // }

  // const auto left_rev_per_sec{left_speed / (wheel_diameter_meter_ * M_PI)};
  // const auto right_rev_per_sec{right_speed / (wheel_diameter_meter_ * M_PI)};
  // const auto left_ticks_per_loop{static_cast<int>(
  //     left_rev_per_sec * encoder_resolution_ * PID_INTERVAL *
  //     gear_reduction_)};
  // const auto right_ticks_per_loop{
  //     static_cast<int>(right_rev_per_sec * encoder_resolution_ * PID_INTERVAL
  //     *
  //                      gear_reduction_)};

  const auto left_ticks_per_loop{calc_ticks_per_loop(left_spd)};
  const auto right_ticks_per_loop{calc_ticks_per_loop(right_spd)};

  return drive(left_ticks_per_loop, right_ticks_per_loop);
}

bool Arduino::drive(const uint16_t left_ticks_per_loop,
                    const uint16_t right_ticks_per_loop) {
  std::ostringstream oss{};

  oss << "m " << left_ticks_per_loop << ' ' << right_ticks_per_loop << '\r';

  serial_.write(oss.str());

  return std::strcmp(serial_.read(2).c_str(), "OK") == 0;
}
}  // namespace aether_driver
