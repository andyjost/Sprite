#pragma once
#include <cassert>
#include <string>

namespace sprite { namespace llvm
{
  /**
   * @brief A string and a flag indicating whether the name is flexible.
   * Flexible names can be modified to resolve conflicts.
   */
  struct globalname : std::string
  {
    using std::string::string;

    globalname(std::string str, bool is_flexible)
      : std::string(str), is_flexible(is_flexible)
    {
      assert(!str.empty() || is_flexible);
    }

    bool is_flexible = false;
  };

  // Creates a flexible name.
  inline globalname flexible(std::string str = std::string())
    { return globalname(str, true); }
}}
