#pragma once
#include <cstdint>
#include "sprite/types.hpp"

namespace sprite
{
  static constexpr tag_type NOTAG = std::numeric_limits<tag_type>::min();
  static constexpr tag_type T_SETGRD = -7;
  static constexpr tag_type T_FAIL   = -6;
  static constexpr tag_type T_CONSTR = -5;
  static constexpr tag_type T_FREE   = -4;
  static constexpr tag_type T_FWD    = -3;
  static constexpr tag_type T_CHOICE = -2;
  static constexpr tag_type T_FUNC   = -1;
  static constexpr tag_type T_CTOR   =  0;
}
