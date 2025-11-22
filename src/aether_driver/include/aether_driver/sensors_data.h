#ifndef AETHER_DRIVER__SENSORS_DATA_H_
#define AETHER_DRIVER__SENSORS_DATA_H_

#include <cstdint>

#include "imu_data.h"

namespace aether_driver {
using EncoderValue = int64_t;

struct SensorsData {
  EncoderValue left_enc{0};
  EncoderValue right_enc{0};
  IMUData imu{};
};
}  // namespace aether_driver

#endif
