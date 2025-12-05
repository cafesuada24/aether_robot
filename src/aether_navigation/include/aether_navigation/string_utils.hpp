#ifndef AETHER_NAVIGATION__STRING_UTILTS_
#define AETHER_NAVIGATION__STRING_UTILTS_
#include <set>
#include <string>

namespace aether_navigation::string_utils {

static const std::set<char> invalid_filename_chars{'<',  '>', ':', '"', '/',
                                            '\\', '|', '?', '*', '\0'};
/**
 * @brief Transforms a given string into a valid, underscore-separated file path
 * component.
 * * This function performs the following steps:
 * 1. Converts the entire string to lowercase.
 * 2. Replaces all invalid file system characters with a space.
 * 3. Replaces sequences of spaces and dashes with a single underscore.
 * 4. Removes any leading or trailing underscores.
 * * @param input The original string to transform.
 * @return The sanitized, valid path name component.
 *
 * author: cafesuada
 */
std::string toValidPathName(const std::string& input);
};  // namespace aether_navigation::string_utils

#endif
