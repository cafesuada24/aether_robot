#include <image_transport/image_transport.hpp>
#include <image_transport/publisher.hpp>
#include <rclcpp/logging.hpp>
#include <rclcpp/qos.hpp>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp/subscription.hpp>
#include <rclcpp_components/register_node_macro.hpp>
#include <sensor_msgs/image_encodings.hpp>

#include "cv_bridge/cv_bridge.hpp"
#include "geometry_msgs/msg/point.hpp"
#include "object_tracker.hpp"
#include "sensor_msgs/msg/image.hpp"

namespace object_tracker::node {
class ObjectDetector : public rclcpp::Node {
 public:
  explicit ObjectDetector(
      const rclcpp::NodeOptions& options = rclcpp::NodeOptions())
      : Node("object_detector", options),
        image_sub_{image_transport::create_subscription(
            this, "/image_in",
            std::bind(&ObjectDetector::ImageCallback, this,
                      std::placeholders::_1),
            "raw", rclcpp::SensorDataQoS().get_rmw_qos_profile())},
        image_pub_{image_transport::create_publisher(this, "/image_out")},
        detected_object_{create_publisher<geometry_msgs::msg::Point>(
            "/detected_object", 10)} {
    ReadParameters();
  }

 private:
  void ReadParameters() {
    this->declare_parameter("x_min", 0);
    this->declare_parameter("x_max", 100);
    this->declare_parameter("y_min", 0);
    this->declare_parameter("y_max", 100);
    this->declare_parameter("h_min", 0);
    this->declare_parameter("h_max", 180);
    this->declare_parameter("s_min", 0);
    this->declare_parameter("s_max", 255);
    this->declare_parameter("v_min", 0);
    this->declare_parameter("v_max", 255);
    this->declare_parameter("sz_min", 0);
    this->declare_parameter("sz_max", 100);

    tuning_params_.rect_perc = {
        static_cast<uint8_t>(this->get_parameter("x_min").as_int()),
        static_cast<uint8_t>(this->get_parameter("y_min").as_int()),
        static_cast<uint8_t>(this->get_parameter("x_max").as_int()),
        static_cast<uint8_t>(this->get_parameter("y_max").as_int())};

    tuning_params_.h_min = this->get_parameter("h_min").as_int();
    tuning_params_.h_max = this->get_parameter("h_max").as_int();
    tuning_params_.s_min = this->get_parameter("s_min").as_int();
    tuning_params_.s_max = this->get_parameter("s_max").as_int();
    tuning_params_.v_min = this->get_parameter("v_min").as_int();
    tuning_params_.v_max = this->get_parameter("v_max").as_int();
    tuning_params_.sz_min = this->get_parameter("sz_min").as_int();
    tuning_params_.sz_max = this->get_parameter("sz_max").as_int();
  }

  void ImageCallback(const sensor_msgs::msg::Image::ConstSharedPtr& msg) {
    cv_bridge::CvImagePtr cv_img_ptr;

    try {
      cv_img_ptr = cv_bridge::toCvCopy(msg, sensor_msgs::image_encodings::BGR8);
    } catch (cv_bridge::Exception& e) {
      RCLCPP_ERROR(get_logger(), "cv_bridge exception: %s", e.what());
      return;
    }

    KeyPoints keypoints{};
    try {
      cv::Mat out_img{};
      find_blobs(cv_img_ptr->image, tuning_params_, keypoints, out_img);

      cv_bridge::CvImage cv_out_img{};
      cv_out_img.image = out_img;
      cv_out_img.encoding = "bgr8";
      image_pub_.publish(cv_out_img.toImageMsg());

    } catch (cv_bridge::Exception& ex) {
      RCLCPP_ERROR(get_logger(), "CV Bridge error: %s", ex.what());
    }

    geometry_msgs::msg::Point point_out{};
    for (const auto& kp : keypoints) {
      const auto s{kp.size};
      if (s > point_out.z) {
        point_out.x = kp.pt.x;
        point_out.y = kp.pt.y;
        point_out.z = s;
      }
    }

    if (point_out.z > 0) {
      detected_object_->publish(point_out);
    }
  }

  image_transport::Subscriber image_sub_;
  image_transport::Publisher image_pub_;

  rclcpp::Publisher<geometry_msgs::msg::Point>::SharedPtr detected_object_;

  TuningParams tuning_params_{};
};
}  // namespace object_tracker::node

RCLCPP_COMPONENTS_REGISTER_NODE(object_tracker::node::ObjectDetector)
