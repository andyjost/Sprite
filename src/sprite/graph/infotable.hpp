#pragma once
#include "sprite/fwd.hpp"
#include <cstdint>

namespace sprite
{
	enum TypeTag : flag_type
	{ 
      NO_FLAGS, INT_TYPE, CHAR_TYPE, FLOAT_TYPE, BOOL_TYPE, LIST_TYPE
    , TUPLE_TYPE, IO_TYPE, PARTIAL_TYPE, OPERATOR
	  };

  static flag_type constexpr MONADIC = 0x1;  // Whether any monadic function can be reached.

  struct Type
  {
    InfoTable const * const * ctors;
    index_type size;
    char kind = 't';
  };

  struct ValueSet
  {
    Arg *      args;
    index_type size;
    char       kind; // Int:'i', Float:'f', Char:'c', Type:'t'
  };

  struct InfoTable
  {
    tag_type           tag;        // 16
    index_type         arity;      // 16
    index_type         alloc_size; // 16
    TypeTag            typetag;    // 8
    flag_type          flags;      // 8
    char const *       name;
    char const *       format;
    stepfunc_type      step;
    typecheckfunc_type typecheck;
    Type const *       type;
  };
}
