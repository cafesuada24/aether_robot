#ifndef AETHER_DRIVER__ARDUINO_H_
#define AETHER_DRIVER__ARDUINO_H_

#include <cstdint>
#include <string>
#include <math.h>

#include "aether_driver/sensors_data.h"
#include "aether_driver/serial/serial.h"

namespace aether_driver {
class Arduino {
 public:
  explicit Arduino(const std::string& serial = "/dev/ttyUSB0",
                   const uint16_t baudrate = 9600,
                   const uint64_t timeout_ms = 1000,
                   const uint16_t encoder_resolution = 20,
                   const float wheel_diameter_meter = 0.01);

  void setup(const std::string& serial = "/dev/ttyUSB0",
             const uint16_t braud = 9600, const uint64_t timeout_ms = 1000,
             const uint16_t encoder_resolution = 20,
             const float wheel_diameter_meter = 0.01);

  void connect();

  bool connected() const;

  void close();

  bool drive_m_per_sec(const float left_speed, const float right_speed);

  bool stop_motors();

  bool set_pid_values(const uint16_t k_p, const uint16_t k_d,
                      const uint16_t k_i, const uint16_t k_o);
  void read_encoder_values(int64_t& left, int64_t& right);

  void send_empty_message();

  bool drive(const int16_t left_ticks_per_loop,
             const int16_t right_ticks_per_loop);

  bool drive_rpm(const float left_rpm, const float right_rpm);

  bool read_sensors(SensorsData& sensors_data);

 private:
  static constexpr auto PID_RATE{30};
  static constexpr auto PID_INTERVAL{1000.0 / 30};

  static constexpr double GYRO_MUL {M_PI / 180};
  static constexpr double LINEAR_MUL {9.80665};

  Serial serial_{};

  uint16_t encoder_count_{0};
  uint16_t encoder_resolution_{};
  float wheel_diameter_meter_{};

  int16_t calc_ticks_per_loop(const float speed) const;
  float ensure_speed(const float speed) const;
};
}  // namespace aether_driver

#endif  // AETHER_DRIVER__ARDUINO_H_
