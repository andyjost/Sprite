#include "cyrt/cyrt.hpp"
#include <cmath>
#include <functional>
#include <string>

using namespace cyrt;

namespace cyrt
{
  static inline unboxed_float_type _builtin_minusFloat(unboxed_float_type x, unboxed_float_type y)
    { return y - x; }
  static inline unboxed_float_type _builtin_divFloat(unboxed_float_type x, unboxed_float_type y)
    { return y / x; }

  // The checked primitives on Int (currylib/defs/checked.def).  Int is 64
  // bits, and a result outside the range is an error, not a wrapped value
  // (issue #105); a division by zero is an error, not a signal (issue
  // #106).  Each function returns true when the result exists.  The
  // divisions follow the Prelude: div and mod round toward minus infinity,
  // quot and rem toward zero.  The one quotient that overflows is the
  // minimum divided by -1; its remainder is zero, and it is taken before
  // the division, which traps on it.
  static inline bool _checked_plusInt(unboxed_int_type x, unboxed_int_type y, unboxed_int_type & r)
    { return !__builtin_add_overflow(x, y, &r); }
  static inline bool _checked_minusInt(unboxed_int_type x, unboxed_int_type y, unboxed_int_type & r)
    { return !__builtin_sub_overflow(x, y, &r); }
  static inline bool _checked_timesInt(unboxed_int_type x, unboxed_int_type y, unboxed_int_type & r)
    { return !__builtin_mul_overflow(x, y, &r); }
  static inline bool _checked_divInt(unboxed_int_type x, unboxed_int_type y, unboxed_int_type & r)
  {
    if(y == 0) return false;
    if(y == -1) return !__builtin_sub_overflow(0, x, &r);
    r = x / y;
    if(x % y != 0 && (x < 0) != (y < 0)) --r;
    return true;
  }
  static inline bool _checked_modInt(unboxed_int_type x, unboxed_int_type y, unboxed_int_type & r)
  {
    if(y == 0) return false;
    if(y == -1) { r = 0; return true; }
    r = x % y;
    if(r != 0 && (r < 0) != (y < 0)) r += y;
    return true;
  }
  static inline bool _checked_quotInt(unboxed_int_type x, unboxed_int_type y, unboxed_int_type & r)
  {
    if(y == 0) return false;
    if(y == -1) return !__builtin_sub_overflow(0, x, &r);
    r = x / y;
    return true;
  }
  static inline bool _checked_remInt(unboxed_int_type x, unboxed_int_type y, unboxed_int_type & r)
  {
    if(y == 0) return false;
    if(y == -1) { r = 0; return true; }
    r = x % y;
    return true;
  }
  // The integral doubles from -2^63 up to, but not including, 2^63 convert
  // to Int exactly.  The comparison is false for NaN.
  static inline bool _int_range(unboxed_float_type t)
    { return t >= -9223372036854775808.0 && t < 9223372036854775808.0; }
  static inline bool _checked_truncateFloat(unboxed_float_type x, unboxed_int_type & r)
  {
    unboxed_float_type const t = std::trunc(x);
    if(!_int_range(t)) return false;
    r = (unboxed_int_type) t;
    return true;
  }
  // Half away from zero, as PAKCS rounds.
  static inline bool _checked_roundFloat(unboxed_float_type x, unboxed_int_type & r)
  {
    unboxed_float_type const t = std::round(x);
    if(!_int_range(t)) return false;
    r = (unboxed_int_type) t;
    return true;
  }

  // The messages.  An operand is the text of its value, in parentheses when
  // it is negative, as Curry shows an argument.  The Python backend spells
  // the same messages (backends/py/currylib/prelude/math.py).
  static std::string _operand(Node * node)
  {
    std::string const text = node->str();
    return (!text.empty() && text[0] == '-') ? "(" + text + ")" : text;
  }
  static std::string _overflow_message(char const * op, Node * x, Node * y)
    { return "integer overflow: " + _operand(x) + " " + op + " " + _operand(y); }
  static std::string _division_message(char const * name, Node * x, Node * y)
  {
    bool const zero = NodeU{y}.int_->value == 0;
    return std::string(zero ? "division by zero: " : "integer overflow: ")
        + name + " " + _operand(x) + " " + _operand(y);
  }
  static std::string _conversion_message(char const * name, Node * x)
    { return std::string("integer overflow: ") + name + " " + _operand(x); }

  static std::string _message_plusInt(Node * x, Node * y)
    { return _overflow_message("+", x, y); }
  static std::string _message_minusInt(Node * x, Node * y)
    { return _overflow_message("-", x, y); }
  static std::string _message_timesInt(Node * x, Node * y)
    { return _overflow_message("*", x, y); }
  static std::string _message_divInt(Node * x, Node * y)
    { return _division_message("div", x, y); }
  static std::string _message_modInt(Node * x, Node * y)
    { return _division_message("mod", x, y); }
  static std::string _message_quotInt(Node * x, Node * y)
    { return _division_message("quot", x, y); }
  static std::string _message_remInt(Node * x, Node * y)
    { return _division_message("rem", x, y); }
  static std::string _message_truncateFloat(Node * x)
    { return _conversion_message("truncate", x); }
  static std::string _message_roundFloat(Node * x)
    { return _conversion_message("round", x); }
}

extern "C"
{
  #define UBSPEC (prim_acosFloat, std::acos, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_acoshFloat, std::acosh, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_asinFloat, std::asin, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_asinhFloat, std::asinh, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_atanFloat, std::atan, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_atanhFloat, std::atanh, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_cosFloat, std::cos, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_coshFloat, std::cosh, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_divFloat, _builtin_divFloat, 2, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define CHECKED_SPEC (divInt, _checked_divInt, 2, int_, _message_divInt)
  #include "cyrt/currylib/defs/checked.def"

  #define UBSPEC (eqChar, std::equal_to<void>(), 2, char_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (eqFloat, std::equal_to<void>(), 2, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (eqInt, std::equal_to<void>(), 2, int_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_expFloat, std::exp, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_intToFloat, unboxed_float_type, 1, int_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_logFloat, std::log, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (ltEqChar, std::less_equal<void>(), 2, char_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (ltEqFloat, std::less_equal<void>(), 2, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (ltEqInt, std::less_equal<void>(), 2, int_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_minusFloat, _builtin_minusFloat, 2, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define CHECKED_SPEC (minusInt, _checked_minusInt, 2, int_, _message_minusInt)
  #include "cyrt/currylib/defs/checked.def"

  #define CHECKED_SPEC (modInt, _checked_modInt, 2, int_, _message_modInt)
  #include "cyrt/currylib/defs/checked.def"

  #define UBSPEC (negateFloat, std::negate<void>(), 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_plusFloat, std::plus<void>(), 2, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define CHECKED_SPEC (plusInt, _checked_plusInt, 2, int_, _message_plusInt)
  #include "cyrt/currylib/defs/checked.def"

  #define CHECKED_SPEC (quotInt, _checked_quotInt, 2, int_, _message_quotInt)
  #include "cyrt/currylib/defs/checked.def"

  #define CHECKED_SPEC (remInt, _checked_remInt, 2, int_, _message_remInt)
  #include "cyrt/currylib/defs/checked.def"

  #define CHECKED_SPEC (prim_roundFloat, _checked_roundFloat, 1, float_, _message_roundFloat)
  #include "cyrt/currylib/defs/checked.def"

  #define UBSPEC (prim_sinFloat, std::sin, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_sinhFloat, std::sinh, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_sqrtFloat, std::sqrt, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_tanFloat, std::tan, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_tanhFloat, std::tanh, 1, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_timesFloat, std::multiplies<void>(), 2, float_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define CHECKED_SPEC (timesInt, _checked_timesInt, 2, int_, _message_timesInt)
  #include "cyrt/currylib/defs/checked.def"

  #define CHECKED_SPEC (prim_truncateFloat, _checked_truncateFloat, 1, float_, _message_truncateFloat)
  #include "cyrt/currylib/defs/checked.def"
}
