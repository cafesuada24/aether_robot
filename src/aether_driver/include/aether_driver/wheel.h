// Copyright (c) 2025 Cafesuada
// All rights reserved.

#ifndef AETHER_DRIVER__WHEEL_H_
#define AETHER_DRIVER__WHEEL_H_

#include <cstdint>
#include <string>

namespace aether_driver {

class Wheel {
 public:
  std::string name{""};
  int64_t enc{0};
  double cmd{0};
  double pos{0};
  double vel{0};
  double eff{0};
  double velSetPt{0};
  double rads_per_count{0};

  Wheel() = default;

  Wheel(const std::string &wheel_name, const int counts_per_rev);

  void setup(const std::string &wheel_name, const int counts_per_rev);

  double calc_enc_angle() const;
};
}  // namespace aether_driver

#endif  // AETHER_DRIVER__WHEEL_H_
