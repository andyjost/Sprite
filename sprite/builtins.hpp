/**
 * @file
 * @brief Interface to built-in types.
 */
#pragma once
#include "sprite/node.hpp"
#include <algorithm>
#include <iterator>
#include <vector>

namespace sprite
{
  /**
   * Preprocessor table defining of built-in types.  The format is:
   *     (op,type,rep,arity,infix)
   */
  #define SPRITE_SEQ_ALL_OP            \
      ((OP_INT_ADD,   INT,   +, 2, 1)) \
      ((OP_INT_SUB,   INT,   -, 2, 1)) \
      ((OP_INT_MUL,   INT,   *, 2, 1)) \
      ((OP_INT_DIV,   INT,   /, 2, 1)) \
      ((OP_FLOAT_ADD, FLOAT, +, 2, 1)) \
      ((OP_FLOAT_SUB, FLOAT, -, 2, 1)) \
      ((OP_FLOAT_MUL, FLOAT, *, 2, 1)) \
      ((OP_FLOAT_DIV, FLOAT, /, 2, 1)) \
      /**/

  /// The built-in data constructors.
  // enum BuiltinCtor
  // {
  //   C_END // Must be last.
  // };

  /// The built-in operations.
  enum BuiltinOp
  {
      OP_INT_ADD, OP_INT_SUB, OP_INT_MUL, OP_INT_DIV
    , OP_FLOAT_ADD, OP_FLOAT_SUB, OP_FLOAT_MUL, OP_FLOAT_DIV
    , OP_END // Must be last.
  };

  namespace meta
  {
    /// Computes the TagValue (e.g., INT) associated with a builtin operation.
    template<BuiltinOp> struct TagValueOf;
    template<> struct TagValueOf<OP_INT_ADD> : TagValue<INT> {};
    template<> struct TagValueOf<OP_INT_SUB> : TagValue<INT> {};
    template<> struct TagValueOf<OP_INT_MUL> : TagValue<INT> {};
    template<> struct TagValueOf<OP_INT_DIV> : TagValue<INT> {};
    template<> struct TagValueOf<OP_FLOAT_ADD> : TagValue<FLOAT> {};
    template<> struct TagValueOf<OP_FLOAT_SUB> : TagValue<FLOAT> {};
    template<> struct TagValueOf<OP_FLOAT_MUL> : TagValue<FLOAT> {};
    template<> struct TagValueOf<OP_FLOAT_DIV> : TagValue<FLOAT> {};

    /// Returns the arity of each builtin function.
    template<BuiltinOp> struct ArityOf;
    template<> struct ArityOf<OP_INT_ADD> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_INT_SUB> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_INT_MUL> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_INT_DIV> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_FLOAT_ADD> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_FLOAT_SUB> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_FLOAT_MUL> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_FLOAT_DIV> : mpl::size_t<2> {};
  }
}
