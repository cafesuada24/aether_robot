// Copyright (c) 2025 Cafesuada
// All rights reserved.

#include "aether_navigation/string_utils.hpp"

#include <set>
#include <string>

namespace aether_navigation::string_utils {
std::string toValidPathName(const std::string& input) {
  if (input.empty()) {
    return "";
  }

  // 1. Define common invalid characters for Windows and Unix-like systems
  // Windows: <, >, :, ", /, \, |, ?, *
  // Unix-like: / (handled by logic below), NUL character

  std::string sanitized{""};
  bool previous_was_delimiter{
      false};  // Used to prevent multiple consecutive underscores

  for (char c : input) {
    if (invalid_filename_chars.count(c)) {
      // Replace explicit invalid characters with a space
      if (!previous_was_delimiter) {
        sanitized += '_';
        previous_was_delimiter = true;
      }
      continue;
    }
    if (std::isspace(static_cast<unsigned char>(c)) || c == '-' || c == '_') {
      // Treat spaces, hyphens, and existing underscores as delimiters
      if (!previous_was_delimiter) {
        sanitized += '_';
        previous_was_delimiter = true;
      }
      continue;
    }
    if (std::isalnum(static_cast<unsigned char>(c))) {
      // Append alphanumeric characters (converted to lowercase)
      sanitized += c;
      previous_was_delimiter = false;
      continue;
    }
    // Optionally remove other non-alphanumeric, non-space, non-delimiter
    // characters If you want to keep characters like '.', you would adjust
    // the logic here. For robust path naming, we treat these as delimiters
    // too, or just skip them.
    if (!previous_was_delimiter) {
      sanitized += '_';
      previous_was_delimiter = true;
    }
  }

  // 2. Remove leading underscores
  size_t first_char{sanitized.find_first_not_of('_')};
  if (first_char == std::string::npos) {
    return "";  // The input contained only invalid/delimiter characters
  }
  sanitized = sanitized.substr(first_char);

  // 3. Remove trailing underscores
  size_t last_char{sanitized.find_last_not_of('_')};
  if (last_char != std::string::npos) {
    sanitized = sanitized.substr(0, last_char + 1);
  }

  return sanitized;
}
};  // namespace aether_navigation::string_utils
