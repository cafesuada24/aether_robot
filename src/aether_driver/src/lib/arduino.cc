#include <aether_driver/arduino.h>

#include <algorithm>
#include <cmath>
#include <iostream>
#include <string>

namespace aether_driver {

using namespace std::string_literals;
Arduino::Arduino(const std::string& serial, const uint16_t braud,
                 const uint64_t timeout_ms, const uint16_t encoder_resolution,
                 const float wheel_diameter_meter,
                 const float min_linear_speed_m_per_s,
                 const float max_linear_speed_m_per_s)

{
  setup(serial, braud, timeout_ms, encoder_resolution, wheel_diameter_meter,
        min_linear_speed_m_per_s, max_linear_speed_m_per_s);
}

void Arduino::setup(const std::string& serial, const uint16_t braud,
                    const uint64_t timeout_ms,
                    const uint16_t encoder_resolution,
                    const float wheel_diameter_meter,
                    const float min_linear_speed_m_per_s,
                    const float max_linear_speed_m_per_s) {
  encoder_resolution_ = encoder_resolution;
  wheel_diameter_meter_ = wheel_diameter_meter;
  // gear_reduction_{gear_reduction},
  min_linear_speed_m_per_s_ = min_linear_speed_m_per_s;
  max_linear_speed_m_per_s_ = max_linear_speed_m_per_s;

  auto timeout{aether_driver::Timeout::simpleTimeout(timeout_ms)};
  serial_.setPort(serial);
  serial_.setBaudrate(braud);
  serial_.setTimeout(timeout);
}

void Arduino::connect() {
  if (!connected()) {
    serial_.open();
  }
}

void Arduino::close() {
  if (connected()) {
    serial_.close();
  }
}

int16_t Arduino::calc_ticks_per_loop(const float speed) const {
  if (wheel_diameter_meter_ <= 0) {
    std::cerr << "wheel diameter is not set";
    throw aether_driver::SerialException(
        "Parameter 'wheel_diameter' is not set correctly.");
  }

  if (encoder_resolution_ <= 0) {
    std::cerr << "encoder resolution is not set";
    throw aether_driver::SerialException(
        "Parameter 'encoder_resolution' is not set correctly.");
  }

  return std::round(speed / (wheel_diameter_meter_ * M_PI * PID_RATE) *
                    encoder_resolution_);
}

float Arduino::ensure_speed(const float speed) const {
  float spd{0.0};
  if (speed != 0.0) {
    spd = std::clamp((speed < 0 ? -1 : 1) * speed, min_linear_speed_m_per_s_,
                     max_linear_speed_m_per_s_);
    if (speed < 0) {
      spd *= -1;
    }
  }
  return spd;
};

bool Arduino::drive_m_per_sec(const float left_speed, const float right_speed) {
  const auto left_spd{ensure_speed(left_speed)};
  const auto right_spd{ensure_speed(right_speed)};

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

bool Arduino::drive(const int16_t left_ticks_per_loop,
                    const int16_t right_ticks_per_loop) {
  std::ostringstream oss{};

  oss << "m " << left_ticks_per_loop << ' ' << right_ticks_per_loop << '\r';

  serial_.write(oss.str());

  return std::strcmp(serial_.readline().c_str(), "OK") == 0;
}

bool Arduino::connected() const { return serial_.isOpen(); }

void Arduino::read_encoder_values(int64_t& left, int64_t& right) {
  serial_.write("e\r"s);

  const auto response{serial_.readline()};

  const std::string delimiter{" "};
  size_t del_pos{response.find(delimiter)};
  std::string token_1{response.substr(0, del_pos)};
  std::string token_2{response.substr(del_pos + delimiter.length())};

  left = std::atoll(token_1.c_str());
  right = std::atoll(token_2.c_str());
};

bool Arduino::set_pid_values(const float k_p, const float k_d, const float k_i,
                             const float k_o) {
  std::stringstream ss;
  ss << "u " << k_p << ":" << k_d << ":" << k_i << ":" << k_o << "\r";
  serial_.write(ss.str());
  return std::strcmp(serial_.readline().c_str(), "OK") == 0;
}

void Arduino::send_empty_message() { serial_.write("\r"); }
}  // namespace aether_driver
