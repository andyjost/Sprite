#include "cyrt/cyrt.hpp"
#include <cmath>
#include <functional>

using namespace cyrt;

namespace cyrt
{
  static inline unboxed_int_type _builtin_remInt(unboxed_int_type x, unboxed_int_type y)
    { return x - y * unboxed_int_type(unboxed_float_type(x) / unboxed_float_type(y)); }
  static inline unboxed_int_type _builtin_floordivInt(unboxed_int_type x, unboxed_int_type y)
  {
    switch(((x<0) ? 2 : 0) + ((y<0) ? 1 : 0))
    {
      case 0: return x / y;
      case 1: return (-x + y + 1) / (-y);
      case 2: return (x - y + 1) / y;
      case 3: return x / y;
    }
    return x >= 0 ? x / y : (x - y + 1) / y;
  }
  static inline unboxed_int_type _builtin_modInt(unboxed_int_type x, unboxed_int_type y)
    { return x - y * _builtin_floordivInt(x, y); }
  static inline unboxed_float_type _builtin_minusFloat(unboxed_float_type x, unboxed_float_type y)
    { return y - x; }
  static inline unboxed_float_type _builtin_divFloat(unboxed_float_type x, unboxed_float_type y)
    { return y / x; }
}

extern "C"
{
  #define UBSPEC (acosFloat, std::acos, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (acoshFloat, std::acosh, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (asinFloat, std::asin, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (asinhFloat, std::asinh, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (atanFloat, std::atan, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (atanhFloat, std::atanh, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (cosFloat, std::cos, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (coshFloat, std::cosh, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (divFloat, _builtin_divFloat, 2, float_)
  #define SHOWN_NAME prim_divFloat
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (divInt, _builtin_floordivInt, 2, int_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (eqChar, std::equal_to<void>(), 2, char_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (eqFloat, std::equal_to<void>(), 2, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (eqInt, std::equal_to<void>(), 2, int_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (expFloat, std::exp, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (intToFloat, unboxed_float_type, 1, int_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (logFloat, std::log, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (ltEqChar, std::less_equal<void>(), 2, char_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (ltEqFloat, std::less_equal<void>(), 2, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (ltEqInt, std::less_equal<void>(), 2, int_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (minusFloat, _builtin_minusFloat, 2, float_)
  #define SHOWN_NAME prim_minusFloat
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (minusInt, std::minus<void>(), 2, int_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (modInt, cyrt::_builtin_modInt, 2, int_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (negateFloat, std::negate<void>(), 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (plusFloat, std::plus<void>(), 2, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (plusInt, std::plus<void>(), 2, int_)
  #include "cyrt/currylib/defs/unboxed.def"

  // true division followed by integer truncation.
  #define UBSPEC (quotInt, (unboxed_int_type) std::divides<unboxed_float_type>(), 2, int_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (remInt, cyrt::_builtin_remInt, 2, int_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (roundFloat, (unboxed_int_type) std::round, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (sinFloat, std::sin, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (sinhFloat, std::sinh, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (sqrtFloat, std::sqrt, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (tanFloat, std::tan, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (tanhFloat, std::tanh, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (timesFloat, std::multiplies<void>(), 2, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (timesInt, std::multiplies<void>(), 2, int_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (truncateFloat, (unboxed_int_type) std::trunc, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"
}
