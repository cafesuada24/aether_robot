#include "object_tracker.hpp"

#include <algorithm>
#include <iterator>
#include <opencv2/core.hpp>
#include <opencv2/core/mat.hpp>
#include <opencv2/core/types.hpp>
#include <opencv2/features2d.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/opencv.hpp>
#include <rclcpp/logger.hpp>
#include <rclcpp/logging.hpp>
#include <rclcpp/rclcpp.hpp>

void object_tracker::find_blobs(const cv::Mat& img,
                                const TuningParams& tuning_params,
                                OutputKeyPoints& out_keypoints,
                                cv::Mat& out_img) {
  constexpr int blur{5};

  cv::Mat working_img{};
  cv::blur(img, working_img, {blur, blur});
  cv::cvtColor(working_img, working_img, cv::COLOR_BGR2HSV);

  cv::inRange(
      working_img,
      cv::Scalar(tuning_params.h_min, tuning_params.s_min, tuning_params.v_min),
      cv::Scalar(tuning_params.h_max, tuning_params.s_max, tuning_params.v_max),
      working_img);

//   RCLCPP_INFO(rclcpp::get_logger("TEST"), "%d %d %d %d %d %d",
// tuning_params.h_min, tuning_params.s_min, tuning_params.v_min,tuning_params.h_max, tuning_params.s_max, tuning_params.v_max);


  cv::dilate(working_img, working_img, cv::Mat(), cv::Point(-1, -1), 2);
  cv::erode(working_img, working_img, cv::Mat(), cv::Point(-1, -1), 2);

  apply_search_window(working_img, tuning_params.rect_perc);

  cv::SimpleBlobDetector::Params params{};

  working_img = 255 - working_img;

  params.minThreshold = 0;
  params.maxThreshold = 100;

  params.filterByArea = true;
  params.minArea = 30;
  params.maxArea = 20000;

  params.filterByCircularity = true;
  params.minConvexity = 0.5;

  params.filterByInertia = true;
  params.minInertiaRatio = 0.5;

  auto detector{cv::SimpleBlobDetector::create(params)};

  std::vector<cv::KeyPoint> keypoints{};
  detector->detect(working_img, keypoints);

  const auto sz_min_px{tuning_params.sz_min * working_img.size[1] / 100.0};
  const auto sz_max_px{tuning_params.sz_max * working_img.size[1] / 100.0};

  KeyPoints keypoints_filtered{};
  std::copy_if(keypoints.begin(), keypoints.end(),
               std::back_inserter(keypoints_filtered),
               [sz_min_px, sz_max_px](const cv::KeyPoint& kp) {
                 return kp.size > sz_min_px && kp.size < sz_max_px;
               });

  cv::drawKeypoints(img, keypoints_filtered, out_img, {0, 0, 255},
                    cv::DrawMatchesFlags::DRAW_RICH_KEYPOINTS);
  const auto search_window_px{
      convert_rect_perc_to_pixels(img.size, tuning_params.rect_perc)};
  cv::rectangle(out_img, search_window_px, {255, 0, 0}, 5);

  for (auto& kp : keypoints_filtered) {
    normalize_keypoint(img.size, kp, kp);
  }

  // cv::cvtColor(working_img, out_img, cv::COLOR_HSV2BGR);
  out_keypoints = keypoints_filtered;
}

void object_tracker::normalize_keypoint(cv::MatSize size,
                                        const cv::KeyPoint& in_kp,
                                        cv::KeyPoint& out_kp) {
  const auto center_x{size[0] / 2};
  const auto center_y{size[1] / 2};

  cv::KeyPoint new_kp{};
  new_kp.pt.x = (in_kp.pt.x - center_x) / center_x;
  new_kp.pt.y = (in_kp.pt.y - center_y) / center_y;
  new_kp.size = in_kp.size / size[1];

  out_kp = new_kp;
}

void object_tracker::apply_search_window(cv::Mat& img,
                                         const RectPerc& window_adim) {
  assert(window_adim.size() == 4);

  const auto roi{convert_rect_perc_to_pixels(img.size, window_adim)};

  cv::Mat mask{cv::Mat::zeros(img.size(), img.type())};
  //
  img(roi).copyTo(mask(roi));
  mask.copyTo(img);
}

cv::Rect object_tracker::convert_rect_perc_to_pixels(
    const cv::MatSize size, const RectPerc& rect_perc) {
  assert(rect_perc.size() == 4);

  cv::Rect rect{};
  rect.x = static_cast<int>(size[1] * rect_perc[0] / 100);
  rect.y = static_cast<int>(size[0] * rect_perc[1] / 100);
  rect.width = static_cast<int>(size[1] * (rect_perc[2] - rect_perc[0]) / 100);
  rect.height = static_cast<int>(size[0] * (rect_perc[3] - rect_perc[1]) / 100);

  return rect;
}
