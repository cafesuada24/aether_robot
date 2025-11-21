#ifndef AETHER_DRIVER__IMU_DATA_H_
#define AETHER_DRIVER__IMU_DATA_H_
#include <vector>
namespace aether_driver {
struct IMUData {
  std::vector<double> linear{}; 
  std::vector<double> gyro{};

  IMUData() {
    linear.resize(3);
    gyro.resize(3); 
  }
};
}  // namespace aether_driver

#endif
