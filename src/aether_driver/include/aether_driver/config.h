#ifndef AETHER_DRIVER__CONFIG_H_
#define AETHER_DRIVER__CONFIG_H_
#include <string>

namespace aether_driver {
struct Config {
  std::string left_wheel_name{"left_wheel"};
  std::string right_wheel_name{"right_wheel"};
  float loop_rate_ms{30};
  std::string device{"/dev/ttyUSB0"};
  int baud_rate{57600};
  int timeout_ms{1000};
  int enc_counts_per_rev{40};
};
}  // namespace aether_driver

#endif  // AETHER_DRIVER__CONFIG_H_
