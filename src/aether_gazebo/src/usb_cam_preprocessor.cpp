// Copyright (c) 2025 Cafesuada
// All rights reserved.

#include <opencv2/core/types.hpp>
#include <rclcpp/executors.hpp>
#include <rclcpp/publisher.hpp>
#include <rclcpp/qos.hpp>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/image_encodings.hpp>

#include "cv_bridge/cv_bridge.hpp"
#include "image_transport/image_transport.hpp"
#include "sensor_msgs/msg/image.hpp"
#include "sensor_msgs/srv/set_camera_info.hpp"

namespace articubot {
using std::placeholders::_1;
using std::placeholders::_2;

constexpr int camWidth{1280};
constexpr int camHeight{480};

const cv::Rect roi_left(camWidth / 2, 0, camWidth / 2, camHeight);
const cv::Rect roi_right(0, 0, camWidth / 2, camHeight);

class UsbCamPreprocessor : public rclcpp::Node {
 public:
  explicit UsbCamPreprocessor()
      : Node("usb_cam_preprocessor"),
        usb_cam_sub_{image_transport::create_subscription(
            this, "camera/image_raw",
            std::bind(&UsbCamPreprocessor::process_callback, this, _1), "raw",
            rclcpp::SensorDataQoS().get_rmw_qos_profile())},
        left_cam_pub_{
            image_transport::create_publisher(this, "camera/left/image_raw")},
        right_cam_pub_{
            image_transport::create_publisher(this, "camera/right/image_raw")},
        set_camera_info_srv_{create_service<sensor_msgs::srv::SetCameraInfo>(
            "camera/set_camera_info",
            std::bind(&UsbCamPreprocessor::set_camera_info_callback, this, _1,
                      _2))},
        set_left_camera_info_srv_{
            create_service<sensor_msgs::srv::SetCameraInfo>(
                "camera/left/set_camera_info",
                std::bind(&UsbCamPreprocessor::set_left_camera_info_callback,
                          this, _1, _2))},
        set_right_camera_info_srv_{
            create_service<sensor_msgs::srv::SetCameraInfo>(
                "camera/right/set_camera_info",
                std::bind(&UsbCamPreprocessor::set_right_camera_info_callback,
                          this, _1, _2))} {}

 private:
  void set_camera_info_callback(
      const sensor_msgs::srv::SetCameraInfo::Request::SharedPtr request,
      sensor_msgs::srv::SetCameraInfo::Response::SharedPtr response) {
    response->success = true;
    response->status_message = "Camera info updated";
  }

  void set_left_camera_info_callback(
      const sensor_msgs::srv::SetCameraInfo::Request::SharedPtr request,
      sensor_msgs::srv::SetCameraInfo::Response::SharedPtr response) {
    response->success = true;
    response->status_message = "Camera info updated";
  }

  void set_right_camera_info_callback(
      const sensor_msgs::srv::SetCameraInfo::Request::SharedPtr request,
      sensor_msgs::srv::SetCameraInfo::Response::SharedPtr response) {
    response->success = true;
    response->status_message = "Camera info updated";
  }

  void process_callback(const sensor_msgs::msg::Image::ConstSharedPtr& msg) {
    auto cv_ptr{cv_bridge::toCvCopy(msg, sensor_msgs::image_encodings::RGB8)};
    auto& img_src{cv_ptr->image};
    cv::Mat img_left{}, img_right{};
    img_src(roi_left).copyTo(img_left);
    img_src(roi_right).copyTo(img_right);

    cv_bridge::CvImage cv_img_left{};
    cv_img_left.header.stamp = cv_ptr->header.stamp;
    cv_img_left.header.frame_id = "camera_left";
    cv_img_left.encoding = sensor_msgs::image_encodings::RGB8;
    cv_img_left.image = img_left;

    cv_bridge::CvImage cv_img_right{};
    cv_img_right.header.stamp = cv_ptr->header.stamp;
    cv_img_right.header.frame_id = "camera_right";
    cv_img_right.encoding = sensor_msgs::image_encodings::RGB8;
    cv_img_right.image = img_right;

    left_cam_pub_.publish(cv_img_left.toImageMsg());
    right_cam_pub_.publish(cv_img_right.toImageMsg());
  }

  image_transport::Subscriber usb_cam_sub_;
  image_transport::Publisher left_cam_pub_;
  image_transport::Publisher right_cam_pub_;
  // rclcpp::Publisher<sensor_msgs::msg::Image>::SharedPtr left_cam_pub_;
  // rclcpp::Publisher<sensor_msgs::msg::Image>::SharedPtr right_cam_pub_;

  rclcpp::Service<sensor_msgs::srv::SetCameraInfo>::SharedPtr
      set_camera_info_srv_,
      set_left_camera_info_srv_, set_right_camera_info_srv_;
};

}  // namespace articubot

int main(int argc, char** argv) {
  rclcpp::init(argc, argv);

  auto node{std::make_shared<articubot::UsbCamPreprocessor>()};
  rclcpp::spin(node);
  rclcpp::shutdown();

  return 0;
}
