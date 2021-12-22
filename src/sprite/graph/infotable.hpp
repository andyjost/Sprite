#pragma once
#include "sprite/tags.hpp"
#include <cstdint>

namespace sprite
{
  // Constructor flags.
  static flag_type constexpr INT_TYPE       = 0x1; // Prelude.Int
  static flag_type constexpr CHAR_TYPE      = 0x2; // Prelude.Char
  static flag_type constexpr FLOAT_TYPE     = 0x3; // Prelude.Float
  static flag_type constexpr BOOL_TYPE      = 0x4; // Constructor of Prelude.Bool
  static flag_type constexpr LIST_TYPE      = 0x5; // Constructor of Prelude.List
  static flag_type constexpr TUPLE_TYPE     = 0x6; // Constructor of Prelude.() et. al
  static flag_type constexpr IO_TYPE        = 0x7; // Constructor of Prelude.IO
  static flag_type constexpr PARTIAL_TYPE   = 0x8; // A partial application
  // Function flags.
  static flag_type constexpr MONADIC = 0x9;  // Whether any monadic function can be reached.

  struct InfoTable
  {
    char const *       name;
    arity_type         arity;
    tag_type           tag;
    stepfunc_type      step;
    formatfunc_type    format;
    typecheckfunc_type typecheck;
    Typedef * const    typedef_;
    flag_type          flags;
    char const *       packing;
    size_t             alloc_size;
  };
}
