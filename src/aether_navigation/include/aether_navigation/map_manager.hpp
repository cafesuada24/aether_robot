#ifndef AETHER_NAVIGATION__MAP_MANAGER_HPP_
#define AETHER_NAVIGATION__MAP_MANAGER_HPP_

#include <sqlite3.h>

#include <filesystem>
#include <rclcpp/callback_group.hpp>
#include <rclcpp/client.hpp>
#include <rclcpp/parameter_client.hpp>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp/subscription.hpp>
#include <slam_toolbox/srv/save_map.hpp>

#include "aether_interfaces/srv/get_maps.hpp"
#include "aether_interfaces/srv/save_map.hpp"
#include "aether_interfaces/srv/load_map.hpp"
#include "aether_interfaces/srv/update_map.hpp"
#include "aether_interfaces/srv/delete_map.hpp"

namespace aether_navigation {
namespace fs = std::filesystem;
class MapManager : public rclcpp::Node {
 public:
  using GetMaps = aether_interfaces::srv::GetMaps;
  using SaveMap = aether_interfaces::srv::SaveMap;
  using LoadMap = aether_interfaces::srv::LoadMap;
  using UpdateMap = aether_interfaces::srv::UpdateMap;
  using DeleteMap = aether_interfaces::srv::DeleteMap;

  MapManager();
  ~MapManager();

 private:
  fs::path map_directory_{};
  rclcpp::CallbackGroup::SharedPtr srv_cb_group_;

  inline void declare_parameters_();

  rclcpp::Service<GetMaps>::SharedPtr get_maps_srv_{};
  void handle_get_maps_request_(GetMaps::Request::ConstSharedPtr request,
                                GetMaps::Response::SharedPtr response);

  rclcpp::Service<SaveMap>::SharedPtr save_map_srv_{};
  void handle_save_map_request_(SaveMap::Request::ConstSharedPtr request,
                                SaveMap::Response::SharedPtr response);
  
  rclcpp::Service<LoadMap>::SharedPtr load_map_srv_ {};
  void handle_load_map_request_(LoadMap::Request::ConstSharedPtr request,
                                LoadMap::Response::SharedPtr response);

  rclcpp::Service<UpdateMap>::SharedPtr update_map_srv_ {};
  void handle_update_map_request_(UpdateMap::Request::ConstSharedPtr request,
                                UpdateMap::Response::SharedPtr response);
  rclcpp::Service<DeleteMap>::SharedPtr delete_map_srv_ {};
  void handle_delete_map_request_(DeleteMap::Request::ConstSharedPtr request,
                                DeleteMap::Response::SharedPtr response);

  rclcpp::CallbackGroup::SharedPtr save_map_cli_cb_group_;
  rclcpp::Client<slam_toolbox::srv::SaveMap>::SharedPtr save_map_cli_{};

  rclcpp::AsyncParametersClient::SharedPtr map_set_param_cli_;



  sqlite3* map_db_;
};
};  // namespace aether_navigation

#endif
