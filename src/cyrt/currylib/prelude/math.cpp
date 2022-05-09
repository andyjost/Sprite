#include "cyrt/cyrt.hpp"
#include <cmath>
#include <functional>

using namespace cyrt;

extern "C"
{
  #define NAME acosFloat
  #define PRIM std::cos
  #include "cyrt/unboxed_unary_float.def"

  #define NAME acoshFloat
  #define PRIM std::cosh
  #include "cyrt/unboxed_unary_float.def"

  #define NAME asinFloat
  #define PRIM std::asin
  #include "cyrt/unboxed_unary_float.def"

  #define NAME asinhFloat
  #define PRIM std::asinh
  #include "cyrt/unboxed_unary_float.def"

  #define NAME atanFloat
  #define PRIM std::atan
  #include "cyrt/unboxed_unary_float.def"

  #define NAME atanhFloat
  #define PRIM std::atanh
  #include "cyrt/unboxed_unary_float.def"

  #define NAME cosFloat
  #define PRIM std::cos
  #include "cyrt/unboxed_unary_float.def"

  #define NAME coshFloat
  #define PRIM std::cosh
  #include "cyrt/unboxed_unary_float.def"

  #define NAME divFloat
  #define PRIM std::divides<void>()
  #include "cyrt/unboxed_binary_float.def"

  #define NAME divInt
  #include "cyrt/not_used.def"

  #define NAME eqChar
  #define PRIM std::equal_to<void>()
  #include "cyrt/unboxed_binary_char.def"

  #define NAME eqFloat
  #define PRIM std::equal_to<void>()
  #include "cyrt/unboxed_binary_float.def"

  #define NAME eqInt
  #define PRIM std::equal_to<void>()
  #include "cyrt/unboxed_binary_int.def"

  #define NAME expFloat
  #define PRIM std::exp
  #include "cyrt/unboxed_unary_float.def"

  #define NAME intToFloat
  #define PRIM float
  #include "cyrt/unboxed_unary_float.def"

  #define NAME logFloat
  #define PRIM std::log
  #include "cyrt/unboxed_unary_float.def"

  #define NAME ltEqChar
  #define PRIM std::less_equal<void>()
  #include "cyrt/unboxed_binary_char.def"

  #define NAME ltEqFloat
  #define PRIM std::less_equal<void>()
  #include "cyrt/unboxed_binary_float.def"

  #define NAME ltEqInt
  #define PRIM std::less_equal<void>()
  #include "cyrt/unboxed_binary_int.def"

  #define NAME minusFloat
  #define PRIM std::minus<void>()
  #include "cyrt/unboxed_binary_float.def"

  #define NAME minusInt
  #define PRIM std::minus<void>()
  #include "cyrt/unboxed_binary_int.def"

  #define NAME modInt
  #include "cyrt/not_used.def"

  #define NAME negateFloat
  #define PRIM std::negate<void>()
  #include "cyrt/unboxed_unary_float.def"

  #define NAME plusFloat
  #define PRIM std::plus<void>()
  #include "cyrt/unboxed_binary_float.def"

  #define NAME plusInt
  #define PRIM std::plus<void>()
  #include "cyrt/unboxed_binary_int.def"

  #define NAME quotInt
  #include "cyrt/not_used.def"

  #define NAME remInt
  #include "cyrt/not_used.def"

  #define NAME roundFloat
  #define PRIM std::round
  #include "cyrt/unboxed_unary_float.def"

  #define NAME sinFloat
  #define PRIM std::sin
  #include "cyrt/unboxed_unary_float.def"

  #define NAME sinhFloat
  #define PRIM std::sinh
  #include "cyrt/unboxed_unary_float.def"

  #define NAME sqrtFloat
  #define PRIM std::sqrt
  #include "cyrt/unboxed_unary_float.def"

  #define NAME tanFloat
  #define PRIM std::tan
  #include "cyrt/unboxed_unary_float.def"

  #define NAME tanhFloat
  #define PRIM std::tanh
  #include "cyrt/unboxed_unary_float.def"

  #define NAME timesFloat
  #define PRIM std::multiplies<void>()
  #include "cyrt/unboxed_binary_float.def"

  #define NAME timesInt
  #define PRIM std::multiplies<void>()
  #include "cyrt/unboxed_binary_int.def"

  #define NAME truncateFloat
  #define PRIM std::trunc
  #include "cyrt/unboxed_unary_float.def"
}
