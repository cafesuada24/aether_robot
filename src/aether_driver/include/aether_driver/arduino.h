#ifndef AETHER_DRIVER__ARDUINO_H_
#define AETHER_DRIVER__ARDUINO_H_

#include <cstdint>
#include <string>
#include "aether_driver/serial/serial.h"
namespace aether_driver {
class Arduino {
 public:
  explicit Arduino(const std::string& serial = "/dev/ttyUSB0",
                   const uint16_t braud = 9600,
                   const uint64_t timeout_ms = 1000,
                   const uint16_t encoder_resolution = 20,
                   const float wheel_diameter_meter = 0.01, 
                   const float gear_reduction = 1/120
                   );

  bool drive_m_per_sec(const float left_speed, const float right_speed);

  bool stop_motors();
 private:
  static constexpr auto PID_RATE {30};
  static constexpr auto PID_INTERVAL {1000.0 / 30};

  Serial serial_ {};
  
  uint16_t encoder_count_ {0};
  uint16_t encoder_resolution_ {};
  float wheel_diameter_meter_ {}; 
  float gear_reduction_ {};

  bool drive(const uint16_t left_ticks_per_loop, const uint16_t right_ticks_per_loop);
};
}  // namespace aether_driver

#endif  // AETHER_DRIVER__ARDUINO_H_
