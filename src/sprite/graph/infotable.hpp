#pragma once
#include "sprite/tags.hpp"
#include "sprite/types.hpp"
#include <cstdint>

namespace sprite
{
  // Mututally-exclusive flags:
  static flag_type constexpr NO_FLAGS       = 0x0;
  static flag_type constexpr INT_TYPE       = 0x1; // Prelude.Int
  static flag_type constexpr CHAR_TYPE      = 0x2; // Prelude.Char
  static flag_type constexpr FLOAT_TYPE     = 0x3; // Prelude.Float
  static flag_type constexpr BOOL_TYPE      = 0x4; // Constructor of Prelude.Bool
  static flag_type constexpr LIST_TYPE      = 0x5; // Constructor of Prelude.List
  static flag_type constexpr TUPLE_TYPE     = 0x6; // Constructor of Prelude.() et. al
  static flag_type constexpr IO_TYPE        = 0x7; // Constructor of Prelude.IO
  static flag_type constexpr PARTIAL_TYPE   = 0x8; // A partial application
  static flag_type constexpr OPERATOR       = 0x9; // Whether a function is an operator.

  // Combinable flags:
  static flag_type constexpr MONADIC = 0x1;  // Whether any monadic function can be reached.

  struct InfoTable
  {
    tag_type           tag;        // 16
    index_type         arity;      // 16
    index_type         alloc_size; // 16
    flag_type          flags;      // 8
    flag_type          bitflags;   // 8
    char const *       name;
    char const *       format;
    stepfunc_type      step;
    typecheckfunc_type typecheck;
    Typedef * const    typedef_;


  };
}
