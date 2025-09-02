#ifndef OBJECT_TRACKER__OBJECT_TRACKER_HPP_
#define OBJECT_TRACKER__OBJECT_TRACKER_HPP_

#include <opencv2/core/types.hpp>
#include <opencv2/opencv.hpp>
#include <vector>

namespace object_tracker {

using KeyPoints = std::vector<cv::KeyPoint>;
using OutputKeyPoints = KeyPoints;

using RectPerc = std::vector<uint8_t>;

struct TuningParams {
  RectPerc rect_perc {0, 0, 100, 100};
  uint8_t h_min {0};
  uint8_t h_max {180};
  uint8_t s_min {0};
  uint8_t s_max {255};
  uint8_t v_min {0};
  uint8_t v_max {255};
  uint8_t sz_min {0};
  uint8_t sz_max {100};
};

void find_blobs(const cv::Mat& img, const TuningParams& tuning_params, OutputKeyPoints& out_keypoints,
                cv::Mat& out_img);

void normalize_keypoint(const cv::MatSize size, const cv::KeyPoint& in_kp,
                        cv::KeyPoint& out_kp);

void apply_search_window(cv::Mat& img,
                         const RectPerc& window_adim = {0, 0, 1, 1});

cv::Rect convert_rect_perc_to_pixels(const cv::MatSize size,
                                     const RectPerc& rect_perc);

}  // namespace object_tracker

#endif
