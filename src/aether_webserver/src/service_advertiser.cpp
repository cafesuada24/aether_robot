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
    if (!(simple_poll_ = avahi_simple_poll_new())) {
      RCLCPP_ERROR(get_logger(), "Failed to create simple poll object.");
      throw std::exception();
    }
    client_ =
        avahi_client_new(avahi_simple_poll_get(simple_poll_),
                         AVAHI_CLIENT_NO_FAIL, client_callback, this, &error_);
    if (!client_) {
      RCLCPP_ERROR(get_logger(), "Failed to create client: %s.",
                   avahi_strerror(error_));
      throw std::exception();
    }
  }

  ~ServiceAdvertiser() {
    avahi_simple_poll_quit(simple_poll_);
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
  std::thread avahi_thread_{};
  int error_{0};

  void create_services(AvahiClient *c) {
  }

  static void entry_group_callback(AvahiEntryGroup *g,
                                   AvahiEntryGroupState state,
                                   AVAHI_GCC_UNUSED void *userdata) {
  }

  static void client_callback(AvahiClient *c, AvahiClientState state,
                              void *userdata) {
  }
};

int main(const int argc, const char **argv) {
  rclcpp::init(argc, argv);

  try {
    rclcpp::spin(std::make_shared<ServiceAdvertiser>());
  } catch (const std::exception &ex) {
    RCLCPP_ERROR(rclcpp::get_logger("service_advertiser"), "%s", ex.what());
  }
  rclcpp::shutdown();
}
