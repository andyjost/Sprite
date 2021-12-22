#include <cstdint>

namespace sprite
{
  using tag_type = int16_t;
  tag_type constexpr T_SETGRD = -7;
  tag_type constexpr T_FAIL   = -6;
  tag_type constexpr T_CONSTR = -5;
  tag_type constexpr T_FREE   = -4;
  tag_type constexpr T_FWD    = -3;
  tag_type constexpr T_CHOICE = -2;
  tag_type constexpr T_FUNC   = -1;
  tag_type constexpr T_CTOR   =  0; // constructors for each Curry type are numbered from zero.
}
