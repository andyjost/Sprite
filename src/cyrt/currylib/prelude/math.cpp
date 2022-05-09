#include "cyrt/cyrt.hpp"
#include <cmath>
#include <functional>

using namespace cyrt;

namespace cyrt
{
  static inline unboxed_int_type _builtin_modInt(unboxed_int_type x, unboxed_int_type y)
    { return x - y * (x/y); }
  static inline unboxed_int_type _builtin_remInt(unboxed_int_type x, unboxed_int_type y)
    { return x - y * unboxed_int_type(unboxed_float_type(x) / unboxed_float_type(y)); }
}

extern "C"
{
  #define NAME acosFloat
  #define PRIM std::cos
  #include "cyrt/currylib/defs/unboxed_unary_float.def"

  #define NAME acoshFloat
  #define PRIM std::cosh
  #include "cyrt/currylib/defs/unboxed_unary_float.def"

  #define NAME asinFloat
  #define PRIM std::asin
  #include "cyrt/currylib/defs/unboxed_unary_float.def"

  #define NAME asinhFloat
  #define PRIM std::asinh
  #include "cyrt/currylib/defs/unboxed_unary_float.def"

  #define NAME atanFloat
  #define PRIM std::atan
  #include "cyrt/currylib/defs/unboxed_unary_float.def"

  #define NAME atanhFloat
  #define PRIM std::atanh
  #include "cyrt/currylib/defs/unboxed_unary_float.def"

  #define NAME cosFloat
  #define PRIM std::cos
  #include "cyrt/currylib/defs/unboxed_unary_float.def"

  #define NAME coshFloat
  #define PRIM std::cosh
  #include "cyrt/currylib/defs/unboxed_unary_float.def"

  #define NAME divFloat
  #define PRIM std::divides<void>()
  #include "cyrt/currylib/defs/unboxed_binary_float.def"

  #define NAME divInt
  #define PRIM std::divides<void>()
  #include "cyrt/currylib/defs/unboxed_binary_int.def"

  #define NAME eqChar
  #define PRIM std::equal_to<void>()
  #include "cyrt/currylib/defs/unboxed_binary_char.def"

  #define NAME eqFloat
  #define PRIM std::equal_to<void>()
  #include "cyrt/currylib/defs/unboxed_binary_float.def"

  #define NAME eqInt
  #define PRIM std::equal_to<void>()
  #include "cyrt/currylib/defs/unboxed_binary_int.def"

  #define NAME expFloat
  #define PRIM std::exp
  #include "cyrt/currylib/defs/unboxed_unary_float.def"

  #define NAME intToFloat
  #define PRIM float
  #include "cyrt/currylib/defs/unboxed_unary_float.def"

  #define NAME logFloat
  #define PRIM std::log
  #include "cyrt/currylib/defs/unboxed_unary_float.def"

  #define NAME ltEqChar
  #define PRIM std::less_equal<void>()
  #include "cyrt/currylib/defs/unboxed_binary_char.def"

  #define NAME ltEqFloat
  #define PRIM std::less_equal<void>()
  #include "cyrt/currylib/defs/unboxed_binary_float.def"

  #define NAME ltEqInt
  #define PRIM std::less_equal<void>()
  #include "cyrt/currylib/defs/unboxed_binary_int.def"

  #define NAME minusFloat
  #define PRIM std::minus<void>()
  #include "cyrt/currylib/defs/unboxed_binary_float.def"

  #define NAME minusInt
  #define PRIM std::minus<void>()
  #include "cyrt/currylib/defs/unboxed_binary_int.def"

  #define NAME modInt
  #define PRIM cyrt::_builtin_modInt
  #include "cyrt/currylib/defs/unboxed_binary_int.def"

  #define NAME negateFloat
  #define PRIM std::negate<void>()
  #include "cyrt/currylib/defs/unboxed_unary_float.def"

  #define NAME plusFloat
  #define PRIM std::plus<void>()
  #include "cyrt/currylib/defs/unboxed_binary_float.def"

  #define NAME plusInt
  #define PRIM std::plus<void>()
  #include "cyrt/currylib/defs/unboxed_binary_int.def"

  #define NAME quotInt
  #define PRIM std::divides<unboxed_float_type>() // true division followed by integer truncation.
  #include "cyrt/currylib/defs/unboxed_binary_int.def"

  #define NAME remInt
  #define PRIM cyrt::_builtin_remInt
  #include "cyrt/currylib/defs/unboxed_binary_int.def"

  #define NAME roundFloat
  #define PRIM std::round
  #include "cyrt/currylib/defs/unboxed_unary_float.def"

  #define NAME sinFloat
  #define PRIM std::sin
  #include "cyrt/currylib/defs/unboxed_unary_float.def"

  #define NAME sinhFloat
  #define PRIM std::sinh
  #include "cyrt/currylib/defs/unboxed_unary_float.def"

  #define NAME sqrtFloat
  #define PRIM std::sqrt
  #include "cyrt/currylib/defs/unboxed_unary_float.def"

  #define NAME tanFloat
  #define PRIM std::tan
  #include "cyrt/currylib/defs/unboxed_unary_float.def"

  #define NAME tanhFloat
  #define PRIM std::tanh
  #include "cyrt/currylib/defs/unboxed_unary_float.def"

  #define NAME timesFloat
  #define PRIM std::multiplies<void>()
  #include "cyrt/currylib/defs/unboxed_binary_float.def"

  #define NAME timesInt
  #define PRIM std::multiplies<void>()
  #include "cyrt/currylib/defs/unboxed_binary_int.def"

  #define NAME truncateFloat
  #define PRIM std::trunc
  #include "cyrt/currylib/defs/unboxed_unary_float.def"
}
