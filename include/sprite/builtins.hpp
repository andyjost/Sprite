/**
 * @file
 * @brief Interface to built-in types.
 */
#pragma once
#include "sprite/node.hpp"
#include <vector>

namespace sprite
{
  /// The built-in operations.
  enum BuiltinOp
  {
      OP_INT_ADD, OP_INT_SUB, OP_INT_MUL, OP_INT_DIV, OP_INT_MOD
    , OP_INT_LT, OP_INT_LE, OP_INT_EQ, OP_INT_NE, OP_INT_GE, OP_INT_GT
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
    template<> struct TagValueOf<OP_INT_MOD> : TagValue<INT> {};
    template<> struct TagValueOf<OP_INT_LT>  : TagValue<INT> {};
    template<> struct TagValueOf<OP_INT_LE>  : TagValue<INT> {};
    template<> struct TagValueOf<OP_INT_EQ>  : TagValue<INT> {};
    template<> struct TagValueOf<OP_INT_NE>  : TagValue<INT> {};
    template<> struct TagValueOf<OP_INT_GE>  : TagValue<INT> {};
    template<> struct TagValueOf<OP_INT_GT>  : TagValue<INT> {};
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
    template<> struct ArityOf<OP_INT_MOD> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_INT_LT> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_INT_LE> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_INT_EQ> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_INT_NE> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_INT_GE> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_INT_GT> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_FLOAT_ADD> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_FLOAT_SUB> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_FLOAT_MUL> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_FLOAT_DIV> : mpl::size_t<2> {};

    /// Tells whether the builtin is a comparison function.
    template<BuiltinOp> struct IsComparison;
    template<> struct IsComparison<OP_INT_ADD> : mpl::false_ {};
    template<> struct IsComparison<OP_INT_SUB> : mpl::false_ {};
    template<> struct IsComparison<OP_INT_MUL> : mpl::false_ {};
    template<> struct IsComparison<OP_INT_DIV> : mpl::false_ {};
    template<> struct IsComparison<OP_INT_MOD> : mpl::false_ {};
    template<> struct IsComparison<OP_INT_LT>  : mpl::true_ {};
    template<> struct IsComparison<OP_INT_LE>  : mpl::true_ {};
    template<> struct IsComparison<OP_INT_EQ>  : mpl::true_ {};
    template<> struct IsComparison<OP_INT_NE>  : mpl::true_ {};
    template<> struct IsComparison<OP_INT_GE>  : mpl::true_ {};
    template<> struct IsComparison<OP_INT_GT>  : mpl::true_ {};
    template<> struct IsComparison<OP_FLOAT_ADD> : mpl::false_ {};
    template<> struct IsComparison<OP_FLOAT_SUB> : mpl::false_ {};
    template<> struct IsComparison<OP_FLOAT_MUL> : mpl::false_ {};
    template<> struct IsComparison<OP_FLOAT_DIV> : mpl::false_ {};
  }
}
