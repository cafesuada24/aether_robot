#include "aether_navigation/map_manager.hpp"

#include <algorithm>
#include <filesystem>
#include <rclcpp/rclcpp.hpp>
#include <string>

#include "aether_interfaces/srv/get_maps.hpp"

namespace aether_navigation {
using std::placeholders::_1;
using std::placeholders::_2;

MapManager::MapManager() : rclcpp::Node("map_manager") {
  this->declare_parameter<std::string>("map_directory", "map/");
  map_directory_ = this->get_parameter("map_directory").as_string();

  RCLCPP_INFO(this->get_logger(), "Map directory parameter set to: '%s'",
              map_directory_.c_str());

  get_maps_srv_ = this->create_service<GetMaps>(
      "map_manager/get_maps",
      std::bind(&MapManager::handle_get_maps_request_, this, _1, _2));

  RCLCPP_INFO(this->get_logger(), "Service 'map_manager/get_maps' is ready.");
}

void MapManager::handle_get_maps_request_(
    GetMaps::Request::ConstSharedPtr request,
    GetMaps::Response::SharedPtr response) {
  (void)request;  // Request is empty in this service

  response->map_names.clear();
  response->success = false;

  // Check if the directory exists and is accessible
  if (!fs::exists(map_directory_)) {
    fs::create_directory(map_directory_);
  }

  if (!fs::is_directory(map_directory_)) {
    response->message =
        "Error: Map directory not found or not a directory: " + map_directory_;
    RCLCPP_ERROR(this->get_logger(), "%s", response->message.c_str());
    return;
  }

  try {
    // Iterate through the directory
    for (const auto& entry : fs::directory_iterator(map_directory_)) {
      if (entry.is_regular_file()) {
        std::string filename{entry.path().filename().string()};

        // Check if the file ends with .yaml (case-insensitive check is often
        // safer)
        if (filename.size() > 5 &&
            filename.substr(filename.size() - 5) == ".yaml") {
          // Remove the .yaml extension to get the map name
          std::string map_name = filename.substr(0, filename.size() - 5);
          response->map_names.push_back(filename);
          RCLCPP_DEBUG(this->get_logger(), "Found map: %s", map_name.c_str());
        }
      }
    }

    // Sort the list for consistent output
    std::sort(response->map_names.begin(), response->map_names.end());

    response->success = true;
    response->message = "Successfully found " +
                        std::to_string(response->map_names.size()) + " map(s).";
    RCLCPP_INFO(this->get_logger(), "%s", response->message.c_str());

  } catch (const fs::filesystem_error& e) {
    response->message = "Filesystem Error: " + std::string(e.what());
    RCLCPP_ERROR(this->get_logger(), "%s", response->message.c_str());
    return;
  }
}
};  // namespace aether_navigation
