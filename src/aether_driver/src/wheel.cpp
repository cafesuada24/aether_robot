// Copyright (c) 2025 Cafesuada
// All rights reserved.

#include "aether_driver/wheel.h"

#include <cmath>

namespace aether_driver {
Wheel::Wheel(const std::string &wheel_name, const int counts_per_rev) {
  setup(wheel_name, counts_per_rev);
}

void Wheel::setup(const std::string &wheel_name, const int counts_per_rev) {
  name = wheel_name;
  rads_per_count = (2 * M_PI) / counts_per_rev;
}

double Wheel::calc_enc_angle() const { return enc * rads_per_count; }
}  // namespace aether_driver
