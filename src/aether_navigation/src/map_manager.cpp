#include "aether_navigation/map_manager.hpp"

#include <features.h>
#include <sqlite3.h>

#include <filesystem>
#include <rclcpp/callback_group.hpp>
#include <rclcpp/executors.hpp>
#include <rclcpp/parameter_client.hpp>
#include <rclcpp/qos.hpp>
#include <rclcpp/rclcpp.hpp>
#include <stdexcept>
#include <string>

#include "aether_interfaces/srv/get_maps.hpp"
#include "aether_interfaces/srv/load_map.hpp"
#include "aether_interfaces/srv/save_map.hpp"
#include "aether_navigation/string_utils.hpp"
#include "slam_toolbox/srv/save_map.hpp"

namespace aether_navigation {

using std::placeholders::_1;
using std::placeholders::_2;
using namespace std::chrono_literals;

MapManager::MapManager()
    : rclcpp::Node("map_manager"),
      srv_cb_group_{
          create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive)},
      save_map_cli_cb_group_{
          create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive)},
      map_set_param_cli_{std::make_shared<rclcpp::AsyncParametersClient>(
          this, "/map_server", rmw_qos_profile_parameters,
          save_map_cli_cb_group_)} {
  declare_parameters_();

  // ########################DB###########################################
  const auto db_path{get_parameter("map_db_path").as_string().c_str()};
  const auto db_open_status{sqlite3_open(db_path, &map_db_)};

  if (db_open_status != SQLITE_OK) {
    RCLCPP_ERROR(this->get_logger(), "Error open map DB: %s",
                 sqlite3_errmsg(map_db_));
    throw new std::runtime_error("FATAL: Error open map DB ");
  }

  RCLCPP_INFO(get_logger(), "Connected to map db.");

  const std::string create_table_sql{
      "CREATE TABLE IF NOT EXISTS map("
      "id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL, "
      "name VARCHAR(255) UNIQUE NOT NULL, "
      "abs_path TEXT NOT NULL );"};

  char* msg_error{};
  int exit{
      sqlite3_exec(map_db_, create_table_sql.c_str(), NULL, 0, &msg_error)};
  if (exit != SQLITE_OK) {
    RCLCPP_ERROR(get_logger(), "Error Create table: %s", msg_error);
    sqlite3_free(msg_error);
    throw new std::runtime_error("FATAL: Error Create table map DB ");
  }
  // #####################################################################

  const auto map_save_dir{this->get_parameter("map_save_dir").as_string()};

  map_directory_ = fs::absolute(map_save_dir);
  if (!fs::exists(map_directory_)) {
    fs::create_directory(map_directory_);
  }

  if (!fs::is_directory(map_directory_)) {
    throw new std::runtime_error(
        "Error: Map directory not found or not a directory: " + map_save_dir);
  }

  RCLCPP_INFO(this->get_logger(), "Map directory parameter set to: '%s'",
              map_directory_.c_str());
  // #####################################################################

  get_maps_srv_ = this->create_service<GetMaps>(
      "map_manager/get_maps",
      std::bind(&MapManager::handle_get_maps_request_, this, _1, _2),
      rclcpp::ServicesQoS(), srv_cb_group_);

  RCLCPP_INFO(this->get_logger(), "Service 'map_manager/get_maps' is ready.");

  save_map_srv_ = this->create_service<SaveMap>(
      "map_manager/save_map",
      std::bind(&MapManager::handle_save_map_request_, this, _1, _2),
      rclcpp::ServicesQoS(), srv_cb_group_);

  RCLCPP_INFO(this->get_logger(), "Service 'map_manager/save_map' is ready.");

  load_map_srv_ = this->create_service<LoadMap>(
      "map_manager/load_map",
      std::bind(&MapManager::handle_load_map_request_, this, _1, _2),
      rclcpp::ServicesQoS(), srv_cb_group_);

  RCLCPP_INFO(this->get_logger(), "Service 'map_manager/load_map' is ready.");

  save_map_cli_ = this->create_client<slam_toolbox::srv::SaveMap>(
      "/slam_toolbox/save_map", rclcpp::ServicesQoS(), save_map_cli_cb_group_);
}

MapManager::~MapManager() {
  sqlite3_close(map_db_);
  RCLCPP_INFO(get_logger(), "DB connection closed.");
}

inline void MapManager::declare_parameters_() {
  this->declare_parameter("map_save_dir", "map/");
  this->declare_parameter("map_db_path", "data/map.db");
}

void MapManager::handle_get_maps_request_(
    GetMaps::Request::ConstSharedPtr request,
    GetMaps::Response::SharedPtr response) {
  (void)request;  // Request is empty in this service

  response->map_names.clear();
  response->map_ids.clear();
  response->success = false;

  const char* sql{"SELECT id, name FROM map;"};

  static const auto exec_callback{
      [](void* data, int argc, char** argv, char** azColName) {
        auto* response_ptr{static_cast<GetMaps::Response::SharedPtr*>(data)};

        if (argc < 1 || !response_ptr) {
          return 1;
        }

        const uint16_t id{static_cast<uint16_t>(std::stoi(argv[0]))};
        const std::string name{argv[1]};

        (*response_ptr)->map_ids.push_back(id);
        (*response_ptr)->map_names.push_back(name);
        return 0;
      }};

  int exec_status{sqlite3_exec(map_db_, sql, exec_callback, &response, NULL)};

  if (exec_status != 0) {
    response->message = "Error retrieving maps";
    return;
  }

  response->success = true;
  response->message = "Successfully found " +
                      std::to_string(response->map_names.size()) + " map(s).";
  RCLCPP_INFO(this->get_logger(), "%s", response->message.c_str());
}

void MapManager::handle_save_map_request_(
    SaveMap::Request::ConstSharedPtr request,
    SaveMap::Response::SharedPtr response) {
  RCLCPP_INFO(get_logger(), "Saving Map");
  response->success = true;

  const auto map_name{string_utils::toValidPathName(request->map_name)};

  if (map_name.empty()) {
    RCLCPP_ERROR(get_logger(), "Trying to save an empty map name");
    response->message = "Map name cannot be empty";
    response->success = false;
    return;
  }

  const auto abs_path{(map_directory_ / map_name).string()};

  auto save_map_req{std::make_shared<slam_toolbox::srv::SaveMap::Request>()};
  save_map_req->name.data = abs_path;
  auto future{save_map_cli_->async_send_request(save_map_req)};
  if (future.wait_for(4s) != std::future_status::ready) {
    RCLCPP_ERROR(get_logger(), "Failed to save map");
    response->message = "Failed to save map.";
    response->success = false;
    return;
  }

  sqlite3_stmt* stmt{};
  const char* sql{"INSERT INTO map(name, abs_path) VALUES(?, ?);"};
  int rc{sqlite3_prepare_v2(map_db_, sql, -1, &stmt, nullptr)};
  if (rc != SQLITE_OK) {
    RCLCPP_ERROR(get_logger(), "Failed to prepare statement: %s",
                 sqlite3_errmsg(map_db_));
    response->message = "Failed to save map.";
    return;
  }

  sqlite3_bind_text(stmt, 1, map_name.c_str(), -1, SQLITE_TRANSIENT);
  sqlite3_bind_text(stmt, 2, abs_path.c_str(), -1, SQLITE_TRANSIENT);

  rc = sqlite3_step(stmt);
  sqlite3_finalize(stmt);

  if (rc != SQLITE_DONE) {
    RCLCPP_ERROR(get_logger(), "Failed to save map: %s",
                 sqlite3_errmsg(map_db_));
    response->message = "Failed to save map";
    response->success = false;
    return;
  }

  RCLCPP_INFO(get_logger(), "New map saved: %s", abs_path.c_str());
}

void MapManager::handle_load_map_request_(
    LoadMap::Request::ConstSharedPtr request,
    LoadMap::Response::SharedPtr response) {
  response->success = false;

  sqlite3_stmt* stmt{};
  const char* sql{"SELECT abs_path FROM map WHERE id=?;"};
  int rc{sqlite3_prepare_v2(map_db_, sql, -1, &stmt, nullptr)};
  if (rc != SQLITE_OK) {
    RCLCPP_ERROR(get_logger(), "Failed to prepare statement: %s",
                 sqlite3_errmsg(map_db_));
    response->message = "Failed to retrieve the map.";
    return;
  }

  sqlite3_bind_int(stmt, 1, request->map_id);

  if (sqlite3_step(stmt) != SQLITE_ROW) {
    RCLCPP_ERROR(get_logger(), "Failed to retrieve the map: %s",
                 sqlite3_errmsg(map_db_));
    response->message = "Failed to retrieve the map.";
    return;
  }

  const std::string abs_path{
      reinterpret_cast<const char*>(sqlite3_column_text(stmt, 0))};
  sqlite3_finalize(stmt);

  RCLCPP_INFO(get_logger(), "Loading: %s", abs_path.c_str());

  const auto future{map_set_param_cli_->set_parameters(
      {rclcpp::Parameter("yaml_filename", abs_path + ".yaml")})};
  future.wait();

  if (!future.valid()) {
    RCLCPP_ERROR(get_logger(), "Invalid future");
    response->message = "Failed to set the map.";
    return;
  }

  const auto set_result {future.get()[0]};

  if (!set_result.successful) {
    RCLCPP_ERROR(get_logger(), "Set map error: %s", set_result.reason.c_str());
    response->message = "Failed to set the map.";
    return;
  }

  response->success = true;
}
};  // namespace aether_navigation
