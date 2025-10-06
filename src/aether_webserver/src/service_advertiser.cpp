#include <avahi-client/client.h>
#include <avahi-client/publish.h>
#include <avahi-common/alternative.h>
#include <avahi-common/error.h>
#include <avahi-common/malloc.h>
#include <avahi-common/simple-watch.h>

#include <rclcpp/rclcpp.hpp>
#include <rclcpp/utilities.hpp>

class ServiceAdvertiser : public rclcpp::Node {
 public:
  ServiceAdvertiser() : Node("service_advertiser") {
    declare_parameters();

    if (!(simple_poll_ = avahi_simple_poll_new())) {
      RCLCPP_ERROR(get_logger(), "Failed to create simple poll object.");
      goto fail;
    }
    client_ =
        avahi_client_new(avahi_simple_poll_get(simple_poll_),
                         AVAHI_CLIENT_NO_FAIL, client_callback, this, &error_);
    if (!client_) {
      RCLCPP_ERROR(get_logger(), "Failed to create client: %s.",
                   avahi_strerror(error_));
      goto fail;
    }

    avahi_thread_ = std::thread(&ServiceAdvertiser::run_avahi_loop, this);

    return;
  fail:
    if (avahi_thread_.joinable()) {
      if (simple_poll_) {
        avahi_simple_poll_quit(simple_poll_);
      }
      avahi_thread_.join();
    }
    if (client_) {
      avahi_client_free(client_);
    }

    if (simple_poll_) {
      avahi_simple_poll_free(simple_poll_);
    }

    throw std::runtime_error("ServiceAdvertiser initialization failed.");
  }

  ~ServiceAdvertiser() override {
    if (avahi_thread_.joinable()) {
      if (simple_poll_) {
        avahi_simple_poll_quit(simple_poll_);
      }
      avahi_thread_.join();
    }
    if (client_) {
      avahi_client_free(client_);
    }
    if (simple_poll_) {
      avahi_simple_poll_free(simple_poll_);
    }
    RCLCPP_INFO(this->get_logger(), "Avahi service unregistered.");
  }

 private:
  AvahiSimplePoll *simple_poll_{nullptr};
  AvahiClient *client_{nullptr};
  AvahiEntryGroup *group_{nullptr};
  std::thread avahi_thread_;
  int error_{0};

  void declare_parameters() {}

  void run_avahi_loop() {
    assert(simple_poll_);
    RCLCPP_INFO(get_logger(), "Starting Avahi simple poll loop...");
    avahi_simple_poll_loop(simple_poll_);
    error_ = 0;
  }

  void create_services(AvahiClient *c) {
    assert(c);
    if (!group_) {
      if (!(group_ = avahi_entry_group_new(c, entry_group_callback, this))) {
        RCLCPP_ERROR(get_logger(), "avahi_entry_group_new() failed: %s",
                     avahi_strerror(avahi_client_errno(c)));
        throw std::exception();
      }
    }

    if (!avahi_entry_group_is_empty(group_)) {
      return;
    }

    RCLCPP_INFO(get_logger(), "Registering service: 'RobotWebserver'");

    int ret{};

    if ((ret = avahi_entry_group_add_service(
             group_, AVAHI_IF_UNSPEC, AVAHI_PROTO_UNSPEC, AvahiPublishFlags(0),
             "RobotWebserver", "_foxglove._tcp", nullptr, nullptr, 8765,
             nullptr)) < 0) {
      if (ret == AVAHI_ERR_COLLISION) {
        goto collision;
      }

      RCLCPP_ERROR(get_logger(), "Failed to add _foxglove._tcp service: %s\n",
                   avahi_strerror(ret));
      goto fail;
    }

    if ((ret = avahi_entry_group_commit(group_)) < 0) {
      RCLCPP_ERROR(get_logger(), "Failed to commit entry group: %s\n",
                   avahi_strerror(ret));
      goto fail;
    }
    return;

  collision:
    RCLCPP_ERROR(get_logger(), "Service name collision");
    return;
  fail:
    avahi_simple_poll_quit(simple_poll_);
  }

  static void entry_group_callback(AvahiEntryGroup *g,
                                   AvahiEntryGroupState state,
                                   AVAHI_GCC_UNUSED void *userdata) {
    auto *self{static_cast<ServiceAdvertiser *>(userdata)};

    assert(g == self->group_ || self->group_ == nullptr);

    self->group_ = g;

    switch (state) {
      case AVAHI_ENTRY_GROUP_ESTABLISHED:
        /* The entry group has been established successfully */
        RCLCPP_INFO(self->get_logger(),
                    "Service 'RobotWebserver' successfully established.\n");
        break;
      case AVAHI_ENTRY_GROUP_COLLISION: {
        RCLCPP_ERROR(self->get_logger(), "Service name collision");
        break;
      }
      case AVAHI_ENTRY_GROUP_FAILURE:
        RCLCPP_ERROR(self->get_logger(), "Entry group failure: %s\n",
                     avahi_strerror(
                         avahi_client_errno(avahi_entry_group_get_client(g))));
        /* Some kind of failure happened while we were registering our services
         */
        avahi_simple_poll_quit(self->simple_poll_);
        break;
      case AVAHI_ENTRY_GROUP_UNCOMMITED:
      case AVAHI_ENTRY_GROUP_REGISTERING:;
    }
  }

  static void client_callback(AvahiClient *c, AvahiClientState state,
                              void *userdata) {
    assert(c);

    auto *self{static_cast<ServiceAdvertiser *>(userdata)};
    switch (state) {
      case AVAHI_CLIENT_S_RUNNING:
        self->create_services(c);
        break;
      case AVAHI_CLIENT_FAILURE:
        RCLCPP_ERROR(self->get_logger(), "Client failure: %s\n",
                     avahi_strerror(avahi_client_errno(c)));
        avahi_simple_poll_quit(self->simple_poll_);
        break;
      case AVAHI_CLIENT_S_COLLISION:
        /* Let's drop our registered services. When the server is back
         * in AVAHI_SERVER_RUNNING state we will register them
         * again with the new host name. */
      case AVAHI_CLIENT_S_REGISTERING:
        /* The server records are now being established. This
         * might be caused by a host name change. We need to wait
         * for our own records to register until the host name is
         * properly esatblished. */
        if (self->group_) avahi_entry_group_reset(self->group_);
        break;
      case AVAHI_CLIENT_CONNECTING:;
    }
  }
};

int main(const int argc, const char **argv) {
  rclcpp::init(argc, argv);
  try {
    rclcpp::spin(std::make_shared<ServiceAdvertiser>());
  } catch (const std::exception& ex) {
    RCLCPP_ERROR(rclcpp::get_logger("service_advertiser"), "%s", ex.what());
  }
  rclcpp::shutdown();
}
