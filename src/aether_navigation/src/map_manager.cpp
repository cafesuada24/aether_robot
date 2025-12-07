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

namespace {
bool query_map_by_id(sqlite3* db, const int map_id, std::string& name,
                     std::string& abs_path, const rclcpp::Logger& logger) {
  sqlite3_stmt* stmt{};
  const char* sql{"SELECT name, abs_path FROM map WHERE id=?;"};

  int rc{sqlite3_prepare_v2(db, sql, -1, &stmt, nullptr)};
  if (rc != SQLITE_OK) {
    RCLCPP_ERROR(logger, "Failed to prepare SELECT statement: %s",
                 sqlite3_errmsg(db));
    return false;
  }

  sqlite3_bind_int(stmt, 1, map_id);

  rc = sqlite3_step(stmt);
  if (rc != SQLITE_ROW) {
    RCLCPP_ERROR(logger, "Failed to retrieve map with id %d (rc=%d, msg=%s)",
                 map_id, rc, sqlite3_errmsg(db));
    sqlite3_finalize(stmt);
    return false;
  }

  const auto* name_cstr{
      reinterpret_cast<const char*>(sqlite3_column_text(stmt, 0))};
  const auto* abs_path_cstr{
      reinterpret_cast<const char*>(sqlite3_column_text(stmt, 1))};

  if (!name_cstr || !abs_path_cstr) {
    RCLCPP_ERROR(logger, "Retrieved null fields for map id %d", map_id);
    sqlite3_finalize(stmt);
    return false;
  }

  name = name_cstr;
  abs_path = abs_path_cstr;

  sqlite3_finalize(stmt);
  return true;
}
}  // namespace

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
    RCLCPP_INFO(this->get_logger(),
                "Map directory '%s' does not exist. Creating...",
                map_directory_.c_str());
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
  // NEW: update map service
  update_map_srv_ = this->create_service<UpdateMap>(
      "map_manager/update_map",
      std::bind(&MapManager::handle_update_map_request_, this, _1, _2),
      rclcpp::ServicesQoS(), srv_cb_group_);

  RCLCPP_INFO(this->get_logger(), "Service 'map_manager/update_map' is ready.");

  // NEW: delete map service
  delete_map_srv_ = this->create_service<DeleteMap>(
      "map_manager/delete_map",
      std::bind(&MapManager::handle_delete_map_request_, this, _1, _2),
      rclcpp::ServicesQoS(), srv_cb_group_);

  RCLCPP_INFO(this->get_logger(), "Service 'map_manager/delete_map' is ready.");

  save_map_cli_ = this->create_client<slam_toolbox::srv::SaveMap>(
      "/slam_toolbox/save_map", rclcpp::ServicesQoS(), save_map_cli_cb_group_);
}

MapManager::~MapManager() {
  if (map_db_ != nullptr) {
    sqlite3_close(map_db_);
    map_db_ = nullptr;
    RCLCPP_INFO(get_logger(), "DB connection closed.");
  }
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
      [](void* data, int argc, char** argv, char**) {
        auto* response_ptr{static_cast<GetMaps::Response::SharedPtr*>(data)};
        if (!response_ptr || !(*response_ptr)) {
          return 1;
        }

        if (argc < 2 || !argv[0] || !argv[1]) {
          return 1;
        }

        const auto id{static_cast<uint16_t>(std::stoi(argv[0]))};
        const std::string name{argv[1]};

        (*response_ptr)->map_ids.push_back(id);
        (*response_ptr)->map_names.push_back(name);
        return 0;
      }};

  int exec_status{sqlite3_exec(map_db_, sql, exec_callback, &response, NULL)};

  if (exec_status != 0) {
    response->message = "Error retrieving maps";
    RCLCPP_ERROR(this->get_logger(), "Error retrieving maps: %s",
                 sqlite3_errmsg(map_db_));
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
  response->success = false;

  const auto map_name{request->map_name};
  const auto file_name{string_utils::toValidPathName(request->map_name)};

  if (file_name.empty()) {
    RCLCPP_ERROR(get_logger(), "Trying to save an empty map name");
    response->message = "Map name cannot be empty";
    return;
  }

  if (!save_map_cli_->wait_for_service(2s)) {
    RCLCPP_ERROR(get_logger(), "slam_toolbox save_map service not available");
    response->message = "slam_toolbox save_map service not available.";
    return;
  }

  const auto abs_path{(map_directory_ / file_name).string()};

  auto save_map_req{std::make_shared<slam_toolbox::srv::SaveMap::Request>()};
  save_map_req->name.data = abs_path;

  auto future{save_map_cli_->async_send_request(save_map_req)};
  if (future.wait_for(4s) != std::future_status::ready) {
    RCLCPP_ERROR(get_logger(), "Failed to save map: future not ready");
    response->message = "Failed to save map (timeout calling slam_toolbox).";
    return;
  }

  const auto result{future.get()};
  if (!result) {
    RCLCPP_ERROR(get_logger(), "Failed to save map: null response");
    response->message = "Failed to save map (no response from slam_toolbox).";
    return;
  }

  // slam_toolbox SaveMap: 0 = SUCCESS
  if (result->result != result->RESULT_SUCCESS) {
    RCLCPP_ERROR(get_logger(), "slam_toolbox save_map returned error code: %u",
                 result->result);
    response->message = "slam_toolbox failed to save map.";
    return;
  }

  sqlite3_stmt* stmt{};
  const char* sql{"INSERT INTO map(name, abs_path) VALUES(?, ?);"};
  int rc{sqlite3_prepare_v2(map_db_, sql, -1, &stmt, nullptr)};
  if (rc != SQLITE_OK) {
    RCLCPP_ERROR(get_logger(), "Failed to prepare statement: %s",
                 sqlite3_errmsg(map_db_));
    response->message = "Failed to save map (DB error).";
    return;
  }

  sqlite3_bind_text(stmt, 1, map_name.c_str(), -1, SQLITE_TRANSIENT);
  sqlite3_bind_text(stmt, 2, abs_path.c_str(), -1, SQLITE_TRANSIENT);

  rc = sqlite3_step(stmt);
  sqlite3_finalize(stmt);

  if (rc != SQLITE_DONE) {
    RCLCPP_ERROR(get_logger(), "Failed to save map (DB step): %s",
                 sqlite3_errmsg(map_db_));
    response->message = "Failed to save map (DB Error).";
    return;
  }

  response->success = true;
  response->map_id = static_cast<uint16_t>(sqlite3_last_insert_rowid(map_db_));

  RCLCPP_INFO(get_logger(), "New map saved: %s (id=%u)", abs_path.c_str(),
              response->map_id);
}

void MapManager::handle_load_map_request_(
    LoadMap::Request::ConstSharedPtr request,
    LoadMap::Response::SharedPtr response) {
  response->success = false;

  std::string name;
  std::string abs_path;
  if (!query_map_by_id(map_db_, request->map_id, name, abs_path,
                       this->get_logger())) {
    response->message = "Failed to retrieve the map.";
    return;
  }

  RCLCPP_INFO(get_logger(), "Loading map id=%u, name='%s', path='%s'",
              request->map_id, name.c_str(), abs_path.c_str());

  if (!map_set_param_cli_->wait_for_service(2s)) {
    RCLCPP_ERROR(get_logger(),
                 "Parameter service for /map_server not available");
    response->message = "Failed to set the map (map_server not available).";
    return;
  }

  const auto future{map_set_param_cli_->set_parameters(
      {rclcpp::Parameter("yaml_filename", abs_path + ".yaml")})};

  future.wait();

  if (!future.valid()) {
    RCLCPP_ERROR(get_logger(), "Invalid future returned by set_parameters");
    response->message = "Failed to set the map.";
    return;
  }

  const auto set_result{future.get()[0]};

  if (!set_result.successful) {
    RCLCPP_ERROR(get_logger(), "Set map error: %s", set_result.reason.c_str());
    response->message = "Failed to set the map.";
    return;
  }

  response->success = true;
  response->message = "Map loaded successfully.";
}

void MapManager::handle_update_map_request_(
    UpdateMap::Request::ConstSharedPtr request,
    UpdateMap::Response::SharedPtr response) {
  response->success = false;

  std::string old_name {};
  std::string old_abs_path {};
  if (!query_map_by_id(map_db_, request->map_id, old_name, old_abs_path,
                       this->get_logger())) {
    response->message = "Map not found.";
    return;
  }

  const auto new_name_raw{request->name};
  const auto new_file_name{string_utils::toValidPathName(new_name_raw)};

  if (new_file_name.empty()) {
    RCLCPP_ERROR(get_logger(), "Trying to rename map to an empty name");
    response->message = "New map name cannot be empty.";
    return;
  }

  // const auto new_abs_path{(map_directory_ / new_file_name).string()};

  if (new_name_raw == old_name) {
    response->success = true;
    response->message = "Map name unchanged.";
    return;
  }
  //
  // const fs::path old_base{old_abs_path};
  // const fs::path new_base{new_abs_path};
  //
  // const fs::path old_yaml{old_base.string() + ".yaml"};
  // const fs::path old_pgm{old_base.string() + ".pgm"};
  // const fs::path new_yaml{new_base.string() + ".yaml"};
  // const fs::path new_pgm{new_base.string() + ".pgm"};
  //
  // std::error_code ec;
  //
  // if (fs::exists(old_yaml, ec)) {
  //   fs::rename(old_yaml, new_yaml, ec);
  //   if (ec) {
  //     RCLCPP_ERROR(get_logger(), "Failed to rename yaml from '%s' to '%s': %s",
  //                  old_yaml.c_str(), new_yaml.c_str(), ec.message().c_str());
  //     response->message = "Failed to rename map yaml file.";
  //     return;
  //   }
  // }
  //
  // ec.clear();
  // if (fs::exists(old_pgm, ec)) {
  //   fs::rename(old_pgm, new_pgm, ec);
  //   if (ec) {
  //     RCLCPP_ERROR(get_logger(), "Failed to rename pgm from '%s' to '%s': %s",
  //                  old_pgm.c_str(), new_pgm.c_str(), ec.message().c_str());
  //     response->message = "Failed to rename map pgm file.";
  //     return;
  //   }
  // }

  // Update DB row
  sqlite3_stmt* stmt{};
  const char* sql{"UPDATE map SET name = ? WHERE id = ?;"};

  int rc{sqlite3_prepare_v2(map_db_, sql, -1, &stmt, nullptr)};
  if (rc != SQLITE_OK) {
    RCLCPP_ERROR(get_logger(), "Failed to prepare UPDATE statement: %s",
                 sqlite3_errmsg(map_db_));
    if (stmt) {
      sqlite3_finalize(stmt);
    }
    response->message = "Failed to update map (DB error).";
    return;
  }

  sqlite3_bind_text(stmt, 1, new_name_raw.c_str(), -1, SQLITE_TRANSIENT);
  sqlite3_bind_int(stmt, 2, request->map_id);

  rc = sqlite3_step(stmt);
  sqlite3_finalize(stmt);

  if (rc != SQLITE_DONE) {
    RCLCPP_ERROR(get_logger(), "Failed to update map (DB step): %s",
                 sqlite3_errmsg(map_db_));
    response->message = "Failed to update map (DB error).";
    return;
  }

  RCLCPP_INFO(get_logger(), "Map id=%u renamed from '%s' to '%s'",
              request->map_id, old_name.c_str(), new_name_raw.c_str());

  response->success = true;
  response->message = "Map updated successfully.";
}

void MapManager::handle_delete_map_request_(
    DeleteMap::Request::ConstSharedPtr request,
    DeleteMap::Response::SharedPtr response) {
  response->success = false;

  std::string name;
  std::string abs_path;
  if (!query_map_by_id(map_db_, request->map_id, name, abs_path,
                       this->get_logger())) {
    response->message = "Map not found.";
    return;
  }

  const fs::path base{abs_path};
  const fs::path yaml{base.string() + ".yaml"};
  const fs::path pgm{base.string() + ".pgm"};

  std::error_code ec;

  if (fs::exists(yaml, ec)) {
    fs::remove(yaml, ec);
    if (ec) {
      RCLCPP_WARN(get_logger(), "Failed to remove yaml '%s': %s", yaml.c_str(),
                  ec.message().c_str());
    }
  }

  ec.clear();
  if (fs::exists(pgm, ec)) {
    fs::remove(pgm, ec);
    if (ec) {
      RCLCPP_WARN(get_logger(), "Failed to remove pgm '%s': %s", pgm.c_str(),
                  ec.message().c_str());
    }
  }

  // Remove DB row
  sqlite3_stmt* stmt{};
  const char* sql{"DELETE FROM map WHERE id = ?;"};

  int rc{sqlite3_prepare_v2(map_db_, sql, -1, &stmt, nullptr)};
  if (rc != SQLITE_OK) {
    RCLCPP_ERROR(get_logger(), "Failed to prepare DELETE statement: %s",
                 sqlite3_errmsg(map_db_));
    if (stmt) {
      sqlite3_finalize(stmt);
    }
    response->message = "Failed to delete map (DB error).";
    return;
  }

  sqlite3_bind_int(stmt, 1, request->map_id);

  rc = sqlite3_step(stmt);
  sqlite3_finalize(stmt);

  if (rc != SQLITE_DONE) {
    RCLCPP_ERROR(get_logger(), "Failed to delete map (DB step): %s",
                 sqlite3_errmsg(map_db_));
    response->message = "Failed to delete map (DB error).";
    return;
  }

  RCLCPP_INFO(get_logger(), "Map id=%u, name='%s' deleted (base path='%s')",
              request->map_id, name.c_str(), abs_path.c_str());

  response->success = true;
  response->message = "Map deleted successfully.";
}
};  // namespace aether_navigation
