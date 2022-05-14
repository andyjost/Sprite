#pragma once
#include "cyrt/fwd.hpp"
#include <cstdint>
#include <string>

namespace cyrt
{
  // DataType tags.
  static flag_type constexpr NO_FLAGS        = 0x0;
  static flag_type constexpr TYPETAG_MASK    = 0xf;
  static flag_type constexpr F_INT_TYPE      = 0x1; // enum
  static flag_type constexpr F_CHAR_TYPE     = 0x2; // enum
  static flag_type constexpr F_FLOAT_TYPE    = 0x3; // enum
  static flag_type constexpr F_BOOL_TYPE     = 0x4; // enum
  static flag_type constexpr F_LIST_TYPE     = 0x5; // enum
  static flag_type constexpr F_TUPLE_TYPE    = 0x6; // enum
  static flag_type constexpr F_IO_TYPE       = 0x7; // enum
  static flag_type constexpr F_PARTIAL_TYPE  = 0x8; // enum
  static flag_type constexpr F_CSTRING_TYPE  = 0x9; // enum
  static flag_type constexpr F_MONADIC       = 0x10; // bitwise
  static flag_type constexpr F_OPERATOR      = 0x20; // bitwise
  static flag_type constexpr F_STATIC_OBJECT = 0x40; // bitwise

  // Note: the head must remain bitwise-compatible with ValueSet.
  struct DataType
  {
    InfoTable const * const * ctors;
    index_type size;
    char kind = 't';
    char flags = NO_FLAGS;
    char const * name = nullptr;
  };

  // Note: the head must remain bitwise-compatible with DataType.
  struct ValueSet
  {
    Arg *      args;
    index_type size;
    char       kind; // Int:'i', Float:'f', Char:'c', DataType:'t'
  };

  struct InfoTable
  {
    tag_type           tag;        // 16
    index_type         arity;      // 16
    index_type         alloc_size; // 16
    flag_type          flags;      // 8
    char const *       name;
    char const *       format;
    stepfunc_type      step;
    DataType const *   type;

    std::string repr() const;

    #ifndef NDEBUG
    InfoTable(
        tag_type           tag
      , index_type         arity
      , index_type         alloc_size
      , flag_type          flags
      , char const *       name
      , char const *       format
      , stepfunc_type      step
      , DataType const *   type
      );
    #endif
  };

  inline flag_type typetag(InfoTable const & info)
    { return info.flags & TYPETAG_MASK; }

  inline bool is_int(InfoTable const & info)
    { return typetag(info) == F_INT_TYPE; }

  inline bool is_char(InfoTable const & info)
    { return typetag(info) == F_CHAR_TYPE; }

  inline bool is_float(InfoTable const & info)
    { return typetag(info) == F_FLOAT_TYPE; }

  inline bool is_bool(InfoTable const & info)
    { return typetag(info) == F_BOOL_TYPE; }

  inline bool is_list(InfoTable const & info)
    { return typetag(info) == F_LIST_TYPE; }

  inline bool is_tuple(InfoTable const & info)
    { return typetag(info) == F_TUPLE_TYPE; }

  inline bool is_io(InfoTable const & info)
    { return typetag(info) == F_IO_TYPE; }

  inline bool is_partial(InfoTable const & info)
    { return typetag(info) == F_PARTIAL_TYPE; }

  inline bool is_operator(InfoTable const & info)
    { return info.flags & F_OPERATOR; }

  inline bool is_monadic(InfoTable const & info)
    { return info.flags & F_MONADIC; }

  inline bool is_static(InfoTable const & info)
    { return info.flags & F_STATIC_OBJECT; }

  inline bool is_static(DataType const & type)
    { return type.flags & F_STATIC_OBJECT; }

  inline bool is_special(InfoTable const & info)
    { return typetag(info); }

  inline bool is_primitive(InfoTable const & info)
  {
    switch(typetag(info))
    {
      case F_INT_TYPE:
      case F_CHAR_TYPE:
      case F_FLOAT_TYPE: return true;
      default:           return false;
    }
  }
}
