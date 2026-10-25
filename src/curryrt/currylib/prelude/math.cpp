#include "curryrt/curryrt.hpp"
#include "curryrt/currylib/prelude.hpp"
#include <cmath>
#include <functional>
#include <string>

using namespace curryrt;

namespace curryrt
{
  static inline unboxed_float_type _builtin_minusFloat(unboxed_float_type x, unboxed_float_type y)
    { return y - x; }
  static inline unboxed_float_type _builtin_divFloat(unboxed_float_type x, unboxed_float_type y)
    { return y / x; }

  // Checked word arithmetic is the fast path.  Overflow promotes through
  // integer_binary; division by zero remains an evaluation error.  div/mod
  // round toward minus infinity, and quot/rem toward zero.
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
  // it is negative, as Curry shows an argument.  The former runtime spells
  // the same messages (the former implementation).
  static std::string _operand(Node * node)
  {
    std::string const text = node->str();
    return (!text.empty() && text[0] == '-') ? "(" + text + ")" : text;
  }
  static std::string _division_message(char const * name, Node * x, Node * y)
  {
    bool const zero = !is_bigint(y) && NodeU{y}.int_->value == 0;
    return std::string(zero ? "division by zero: " : "integer overflow: ")
        + name + " " + _operand(x) + " " + _operand(y);
  }
  static std::string _conversion_message(char const * name, Node * x)
    { return std::string("integer overflow: ") + name + " " + _operand(x); }

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
  #include "curryrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_acoshFloat, std::acosh, 1, float_)
  #include "curryrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_asinFloat, std::asin, 1, float_)
  #include "curryrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_asinhFloat, std::asinh, 1, float_)
  #include "curryrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_atanFloat, std::atan, 1, float_)
  #include "curryrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_atanhFloat, std::atanh, 1, float_)
  #include "curryrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_cosFloat, std::cos, 1, float_)
  #include "curryrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_coshFloat, std::cosh, 1, float_)
  #include "curryrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_divFloat, _builtin_divFloat, 2, float_)
  #include "curryrt/currylib/defs/unboxed.def"

  static tag_type divInt_step(RuntimeState * rts, Configuration * C)
  {
    Cursor root = C->cursor();
    Variable x = root[0];
    auto tag = rts->hnf(C, &x);
    if(tag < T_CTOR) return tag;
    Variable y = root[1];
    tag = rts->hnf(C, &y);
    if(tag < T_CTOR) return tag;
    unboxed_int_type value;
    if(!is_bigint(x.target) && !is_bigint(y.target)
        && _checked_divInt(NodeU{x.target}.int_->value,
             NodeU{y.target}.int_->value, value))
      return root->rewrite(&Int_Info, value);
    if(!is_bigint(y.target) && NodeU{y.target}.int_->value == 0)
    {
      C->set_error(_message_divInt(x.target, y.target), ErrorKind::division);
      return E_ERROR;
    }
    root->forward_to(integer_binary('d', x.target, y.target));
    return T_FWD;
  }
  InfoTable const divInt_Info {
      T_FUNC, 2, sizeof(Node2), F_STATIC_OBJECT, "divInt", "pp"
    , divInt_step, nullptr
    };

  #define UBSPEC (eqChar, std::equal_to<void>(), 2, char_)
  #include "curryrt/currylib/defs/unboxed.def"

  #define UBSPEC (eqFloat, std::equal_to<void>(), 2, float_)
  #include "curryrt/currylib/defs/unboxed.def"

  static tag_type eqInt_step(RuntimeState * rts, Configuration * C)
  {
    Cursor root = C->cursor();
    Variable x = root[0];
    auto tag = rts->hnf(C, &x);
    if(tag < T_CTOR) return tag;
    Variable y = root[1];
    tag = rts->hnf(C, &y);
    if(tag < T_CTOR) return tag;
    root->forward_to(integer_compare(x.target, y.target) == 0 ? True : False);
    return T_FWD;
  }
  InfoTable const eqInt_Info {
      T_FUNC, 2, sizeof(Node2), F_STATIC_OBJECT, "eqInt", "pp"
    , eqInt_step, nullptr
    };

  #define UBSPEC (prim_expFloat, std::exp, 1, float_)
  #include "curryrt/currylib/defs/unboxed.def"

  static tag_type prim_intToFloat_step(RuntimeState * rts, Configuration * C)
  {
    Cursor root = C->cursor();
    Variable x = root[0];
    auto tag = rts->hnf(C, &x);
    if(tag < T_CTOR) return tag;
    return root->rewrite(&Float_Info, integer_float(x.target));
  }
  InfoTable const prim_intToFloat_Info {
      T_FUNC, 1, sizeof(Node1), F_STATIC_OBJECT, "prim_intToFloat", "p"
    , prim_intToFloat_step, nullptr
    };

  #define UBSPEC (prim_logFloat, std::log, 1, float_)
  #include "curryrt/currylib/defs/unboxed.def"

  #define UBSPEC (ltEqChar, std::less_equal<void>(), 2, char_)
  #include "curryrt/currylib/defs/unboxed.def"

  #define UBSPEC (ltEqFloat, std::less_equal<void>(), 2, float_)
  #include "curryrt/currylib/defs/unboxed.def"

  static tag_type ltEqInt_step(RuntimeState * rts, Configuration * C)
  {
    Cursor root = C->cursor();
    Variable x = root[0];
    auto tag = rts->hnf(C, &x);
    if(tag < T_CTOR) return tag;
    Variable y = root[1];
    tag = rts->hnf(C, &y);
    if(tag < T_CTOR) return tag;
    root->forward_to(integer_compare(x.target, y.target) <= 0 ? True : False);
    return T_FWD;
  }
  InfoTable const ltEqInt_Info {
      T_FUNC, 2, sizeof(Node2), F_STATIC_OBJECT, "ltEqInt", "pp"
    , ltEqInt_step, nullptr
    };

  #define UBSPEC (prim_minusFloat, _builtin_minusFloat, 2, float_)
  #include "curryrt/currylib/defs/unboxed.def"

  static tag_type minusInt_step(RuntimeState * rts, Configuration * C)
  {
    Cursor root = C->cursor();
    Variable x = root[0];
    auto tag = rts->hnf(C, &x);
    if(tag < T_CTOR) return tag;
    Variable y = root[1];
    tag = rts->hnf(C, &y);
    if(tag < T_CTOR) return tag;
    unboxed_int_type value;
    if(!is_bigint(x.target) && !is_bigint(y.target)
        && _checked_minusInt(NodeU{x.target}.int_->value,
             NodeU{y.target}.int_->value, value))
      return root->rewrite(&Int_Info, value);
    root->forward_to(integer_binary('-', x.target, y.target));
    return T_FWD;
  }
  InfoTable const minusInt_Info {
      T_FUNC, 2, sizeof(Node2), F_STATIC_OBJECT, "minusInt", "pp"
    , minusInt_step, nullptr
    };

  static tag_type modInt_step(RuntimeState * rts, Configuration * C)
  {
    Cursor root = C->cursor();
    Variable x = root[0];
    auto tag = rts->hnf(C, &x);
    if(tag < T_CTOR) return tag;
    Variable y = root[1];
    tag = rts->hnf(C, &y);
    if(tag < T_CTOR) return tag;
    unboxed_int_type value;
    if(!is_bigint(x.target) && !is_bigint(y.target)
        && _checked_modInt(NodeU{x.target}.int_->value,
             NodeU{y.target}.int_->value, value))
      return root->rewrite(&Int_Info, value);
    if(!is_bigint(y.target) && NodeU{y.target}.int_->value == 0)
    {
      C->set_error(_message_modInt(x.target, y.target), ErrorKind::division);
      return E_ERROR;
    }
    root->forward_to(integer_binary('m', x.target, y.target));
    return T_FWD;
  }
  InfoTable const modInt_Info {
      T_FUNC, 2, sizeof(Node2), F_STATIC_OBJECT, "modInt", "pp"
    , modInt_step, nullptr
    };

  #define UBSPEC (negateFloat, std::negate<void>(), 1, float_)
  #include "curryrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_plusFloat, std::plus<void>(), 2, float_)
  #include "curryrt/currylib/defs/unboxed.def"

  static tag_type plusInt_step(RuntimeState * rts, Configuration * C)
  {
    Cursor root = C->cursor();
    Variable x = root[0];
    auto tag = rts->hnf(C, &x);
    if(tag < T_CTOR) return tag;
    Variable y = root[1];
    tag = rts->hnf(C, &y);
    if(tag < T_CTOR) return tag;
    unboxed_int_type value;
    if(!is_bigint(x.target) && !is_bigint(y.target)
        && _checked_plusInt(NodeU{x.target}.int_->value,
             NodeU{y.target}.int_->value, value))
      return root->rewrite(&Int_Info, value);
    root->forward_to(integer_binary('+', x.target, y.target));
    return T_FWD;
  }
  InfoTable const plusInt_Info {
      T_FUNC, 2, sizeof(Node2), F_STATIC_OBJECT, "plusInt", "pp"
    , plusInt_step, nullptr
    };

  static tag_type quotInt_step(RuntimeState * rts, Configuration * C)
  {
    Cursor root = C->cursor();
    Variable x = root[0];
    auto tag = rts->hnf(C, &x);
    if(tag < T_CTOR) return tag;
    Variable y = root[1];
    tag = rts->hnf(C, &y);
    if(tag < T_CTOR) return tag;
    unboxed_int_type value;
    if(!is_bigint(x.target) && !is_bigint(y.target)
        && _checked_quotInt(NodeU{x.target}.int_->value,
             NodeU{y.target}.int_->value, value))
      return root->rewrite(&Int_Info, value);
    if(!is_bigint(y.target) && NodeU{y.target}.int_->value == 0)
    {
      C->set_error(_message_quotInt(x.target, y.target), ErrorKind::division);
      return E_ERROR;
    }
    root->forward_to(integer_binary('q', x.target, y.target));
    return T_FWD;
  }
  InfoTable const quotInt_Info {
      T_FUNC, 2, sizeof(Node2), F_STATIC_OBJECT, "quotInt", "pp"
    , quotInt_step, nullptr
    };

  static tag_type remInt_step(RuntimeState * rts, Configuration * C)
  {
    Cursor root = C->cursor();
    Variable x = root[0];
    auto tag = rts->hnf(C, &x);
    if(tag < T_CTOR) return tag;
    Variable y = root[1];
    tag = rts->hnf(C, &y);
    if(tag < T_CTOR) return tag;
    unboxed_int_type value;
    if(!is_bigint(x.target) && !is_bigint(y.target)
        && _checked_remInt(NodeU{x.target}.int_->value,
             NodeU{y.target}.int_->value, value))
      return root->rewrite(&Int_Info, value);
    if(!is_bigint(y.target) && NodeU{y.target}.int_->value == 0)
    {
      C->set_error(_message_remInt(x.target, y.target), ErrorKind::division);
      return E_ERROR;
    }
    root->forward_to(integer_binary('r', x.target, y.target));
    return T_FWD;
  }
  InfoTable const remInt_Info {
      T_FUNC, 2, sizeof(Node2), F_STATIC_OBJECT, "remInt", "pp"
    , remInt_step, nullptr
    };

  static tag_type prim_roundFloat_step(RuntimeState * rts, Configuration * C)
  {
    Cursor root = C->cursor();
    Variable x = root[0];
    auto tag = rts->hnf(C, &x);
    if(tag < T_CTOR) return tag;
    auto t = std::round(NodeU{x.target}.float_->value);
    if(_int_range(t)) return root->rewrite(&Int_Info, unboxed_int_type(t));
    if(!std::isfinite(t))
    {
      C->set_error(_message_roundFloat(x.target), ErrorKind::overflow);
      return E_ERROR;
    }
    root->forward_to(integer(t));
    return T_FWD;
  }
  InfoTable const prim_roundFloat_Info {
      T_FUNC, 1, sizeof(Node1), F_STATIC_OBJECT, "prim_roundFloat", "p"
    , prim_roundFloat_step, nullptr
    };

  #define UBSPEC (prim_sinFloat, std::sin, 1, float_)
  #include "curryrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_sinhFloat, std::sinh, 1, float_)
  #include "curryrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_sqrtFloat, std::sqrt, 1, float_)
  #include "curryrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_tanFloat, std::tan, 1, float_)
  #include "curryrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_tanhFloat, std::tanh, 1, float_)
  #include "curryrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_timesFloat, std::multiplies<void>(), 2, float_)
  #include "curryrt/currylib/defs/unboxed.def"

  static tag_type timesInt_step(RuntimeState * rts, Configuration * C)
  {
    Cursor root = C->cursor();
    Variable x = root[0];
    auto tag = rts->hnf(C, &x);
    if(tag < T_CTOR) return tag;
    Variable y = root[1];
    tag = rts->hnf(C, &y);
    if(tag < T_CTOR) return tag;
    unboxed_int_type value;
    if(!is_bigint(x.target) && !is_bigint(y.target)
        && _checked_timesInt(NodeU{x.target}.int_->value,
             NodeU{y.target}.int_->value, value))
      return root->rewrite(&Int_Info, value);
    root->forward_to(integer_binary('*', x.target, y.target));
    return T_FWD;
  }
  InfoTable const timesInt_Info {
      T_FUNC, 2, sizeof(Node2), F_STATIC_OBJECT, "timesInt", "pp"
    , timesInt_step, nullptr
    };

  static tag_type prim_truncateFloat_step(RuntimeState * rts, Configuration * C)
  {
    Cursor root = C->cursor();
    Variable x = root[0];
    auto tag = rts->hnf(C, &x);
    if(tag < T_CTOR) return tag;
    auto t = std::trunc(NodeU{x.target}.float_->value);
    if(_int_range(t)) return root->rewrite(&Int_Info, unboxed_int_type(t));
    if(!std::isfinite(t))
    {
      C->set_error(_message_truncateFloat(x.target), ErrorKind::overflow);
      return E_ERROR;
    }
    root->forward_to(integer(t));
    return T_FWD;
  }
  InfoTable const prim_truncateFloat_Info {
      T_FUNC, 1, sizeof(Node1), F_STATIC_OBJECT, "prim_truncateFloat", "p"
    , prim_truncateFloat_step, nullptr
    };
}
