#ifndef AETHER_NAVIGATION__MAP_MANAGER_HPP_
#define AETHER_NAVIGATION__MAP_MANAGER_HPP_

#include <rclcpp/rclcpp.hpp>

#include "aether_interfaces/srv/get_maps.hpp"

namespace aether_navigation {
namespace fs = std::filesystem;
class MapManager : public rclcpp::Node {
 public:
  using GetMaps = aether_interfaces::srv::GetMaps;

  MapManager();

 private:
  void handle_get_maps_request_(GetMaps::Request::ConstSharedPtr request,
                                GetMaps::Response::SharedPtr response);

  std::string map_directory_{};
  rclcpp::Service<GetMaps>::SharedPtr get_maps_srv_{};
};
};  // namespace aether_navigation

#endif
