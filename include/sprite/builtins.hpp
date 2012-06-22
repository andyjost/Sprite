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
      OP_LT, OP_LE, OP_EQ, OP_NE, OP_GE, OP_GT
    , OP_INT_ADD, OP_INT_SUB, OP_INT_MUL, OP_INT_DIV, OP_INT_MOD
    , OP_FLOAT_ADD, OP_FLOAT_SUB, OP_FLOAT_MUL, OP_FLOAT_DIV
    , OP_END // Must be last.
  };

  /// The built-in constructors (numbered from CTOR for each type).
  enum BuiltinCtor
  {
      C_TUPLE2 = CTOR
    , C_TUPLE3 = CTOR
    , C_TUPLE4 = CTOR
    , C_TUPLE5 = CTOR
    , C_TUPLE6 = CTOR
    , C_TUPLE7 = CTOR
    , C_TUPLE8 = CTOR
    , C_TUPLE9 = CTOR
    , C_END
  };

  /// The built-in constructor labels (sequentially numbered).
  enum BuiltinCtorLabel
  {
      CL_TUPLE2 = 0
    , CL_TUPLE3
    , CL_TUPLE4
    , CL_TUPLE5
    , CL_TUPLE6
    , CL_TUPLE7
    , CL_TUPLE8
    , CL_TUPLE9
    , CL_END
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
    // No TagValueOf (result) for comparisons.
    template<> struct TagValueOf<OP_FLOAT_ADD> : TagValue<FLOAT> {};
    template<> struct TagValueOf<OP_FLOAT_SUB> : TagValue<FLOAT> {};
    template<> struct TagValueOf<OP_FLOAT_MUL> : TagValue<FLOAT> {};
    template<> struct TagValueOf<OP_FLOAT_DIV> : TagValue<FLOAT> {};

    /// Returns the arity of each builtin function.
    template<BuiltinOp> struct ArityOf;
    template<> struct ArityOf<OP_LT> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_LE> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_EQ> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_NE> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_GE> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_GT> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_INT_ADD> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_INT_SUB> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_INT_MUL> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_INT_DIV> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_INT_MOD> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_FLOAT_ADD> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_FLOAT_SUB> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_FLOAT_MUL> : mpl::size_t<2> {};
    template<> struct ArityOf<OP_FLOAT_DIV> : mpl::size_t<2> {};

    /// Tells whether the builtin is a comparison function.
    template<BuiltinOp> struct IsComparison : mpl::false_ {};
    template<> struct IsComparison<OP_LT>  : mpl::true_ {};
    template<> struct IsComparison<OP_LE>  : mpl::true_ {};
    template<> struct IsComparison<OP_EQ>  : mpl::true_ {};
    template<> struct IsComparison<OP_NE>  : mpl::true_ {};
    template<> struct IsComparison<OP_GE>  : mpl::true_ {};
    template<> struct IsComparison<OP_GT>  : mpl::true_ {};
  }
}
