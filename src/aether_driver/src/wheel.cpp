#include "aether_driver/wheel.h"

#include <cmath>

namespace aether_driver {
Wheel::Wheel(const std::string &wheel_name, const int counts_per_rev)
    : name{wheel_name}, rads_per_count{(2 * M_PI) / counts_per_rev} {}

double Wheel::calcEncAngle() const { return enc * rads_per_count; }

}  // namespace aether_driver
