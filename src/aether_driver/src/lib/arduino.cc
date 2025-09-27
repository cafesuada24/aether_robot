#include <aether_driver/arduino.h>

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
}  // namespace aether_driver
