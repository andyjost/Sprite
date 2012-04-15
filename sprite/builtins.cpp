/**
 * @file
 * @brief Implementation of built-in types.
 */
#include "sprite/builtins.hpp"
#include "sprite/exec.hpp"

// ====== Guards ======

namespace
{
  using namespace sprite;

  // The guard function determines which operands to a builtin operation are
  // valid.

  /// An arithmetic guard that allows all operands.
  struct NoGuard
  {
    NoGuard() {}
    // Unary
    template<typename Arg> bool operator()(Arg const &) const { return true; }
    // Binary
    template<typename Lhs, typename Rhs>
      bool operator()(Lhs const &, Rhs const &) const { return true; }
  };

  /// An arithmetic guard that disallows a rhs of zero.
  struct DivGuard
  {
    DivGuard() {}
    template<typename Lhs, typename Rhs>
      bool operator()(Lhs const &, Rhs const & rhs) const { return rhs != 0; }
  };

  /// A metafunction that returns the guard associated with an operation.
  template<BuiltinOp Op> struct GuardOf : mpl::identity<NoGuard> {};
  template<> struct GuardOf<OP_INT_DIV> : mpl::identity<DivGuard> {};
  template<> struct GuardOf<OP_FLOAT_DIV> : mpl::identity<DivGuard> {};

  // ====== UnguardedExecute ======

  /// Executes an operation without any guard.
  template<BuiltinOp Op> struct UnguardedExecute;
  #define SPRITE_DEFINE_OP(builtin_op,op)                \
      template<> struct UnguardedExecute<builtin_op>     \
      {                                                  \
        UnguardedExecute() {}                            \
                                                         \
        template<typename T>                             \
        T operator()(T const & lhs, T const & rhs) const \
          { return (lhs op rhs); }                       \
      };                                                 \
      /**/

  SPRITE_DEFINE_OP(OP_INT_ADD,+)
  SPRITE_DEFINE_OP(OP_INT_SUB,-)
  SPRITE_DEFINE_OP(OP_INT_MUL,*)
  SPRITE_DEFINE_OP(OP_INT_DIV,/)
  SPRITE_DEFINE_OP(OP_FLOAT_ADD,+)
  SPRITE_DEFINE_OP(OP_FLOAT_SUB,-)
  SPRITE_DEFINE_OP(OP_FLOAT_MUL,*)
  SPRITE_DEFINE_OP(OP_FLOAT_DIV,/)

  #undef SPRITE_DEFINE_OP

  // ====== GuardedExecute ======

  /**
   * @brief Executes an operation with a guard.
   *
   * If the guard fails, then FAIL is written to the destination node.
   */
  template<BuiltinOp Op> struct GuardedExecute
  {
    GuardedExecute() {}

    template<typename T>
    void operator()(Node & out, T const & lhs, T const & rhs) const
    {
      static typename GuardOf<Op>::type const guard;
      static UnguardedExecute<Op> const exec;

      if(guard(lhs,rhs))
        { rewrite<meta::TagValueOf<Op>::value>()(out, exec(lhs,rhs)); }
      else
        { rewrite_fail(out); }
    }
  };

  // ====== BuiltinImpl ======

  /// Implements the built in operation Op.
  template<BuiltinOp Op> struct BuiltinImpl : static_visitor<void>
  {
    BuiltinImpl(Node & node) : m_out(node) {}
  private:
    Node & m_out;

    /// Determine the node type for this Op.
    typedef typename meta::TagValueOf<Op>::type TagType;
    typedef typename meta::NodeOf<TagType::value>::type NodeType;
  public:
    /// Handles valid cases.
    void operator()(NodeType const & lhs, NodeType const & rhs) const
    {
      static GuardedExecute<Op> const exec;
      exec(m_out, lhs.payload.value, rhs.payload.value);
    }

    /// Handles cases where the argument nodes do not have the expected type.
    template<typename Lhs, typename Rhs>
    void operator()(Lhs const &, Rhs const &) const
    {
      throw RuntimeError(
          "type error while executing " BOOST_PP_STRINGIZE(op)
        );
    }
  };

  // ====== Dispatch ======

  /**
   * @brief Dispatches a built-in operation.
   *
   * Evaluates the operation and rewrites the node with the result.
   */
  template<BuiltinOp Op, size_t Arity=meta::ArityOf<Op>::value>
    struct Dispatch;

  /// Dispatches a unary built-in operation.
  template<BuiltinOp Op> struct Dispatch<Op,1>
  {
    void operator()(Node & node)
    {
      assert(node.arity() == 1);
      return visit(BuiltinImpl<Op>(node), *node[0]);
    }
  };

  /// Dispatches a binary built-in operation.
  template<BuiltinOp Op> struct Dispatch<Op,2>
  {
    void operator()(Node & node)
    {
      assert(node.arity() == 2);
      return visit(BuiltinImpl<Op>(node), *node[0], *node[1]);
    }
  };
}

namespace sprite
{
  // ====== h_func ======

  /// Implements the H function for a built in operation.
  template<BuiltinOp Op> void h_func(Node & node)
  {
    // H.4
    // Q. can this just check against CTOR?
    // Q. how can this be needed?  The only call is from head_normalize.
    // if(is_ctor(node.tag())) return;
  
    BOOST_FOREACH(NodePtr & child, node.iter())
    {
      switch(child->tag())
      {
        // H.1
        case CHOICE: return pull_tab(node, child);
        // H.5
        case FAIL: return rewrite_fail(node);
        // H.2
        case OPER: return head_normalize(*child);
        default:;
      }
    }
  
    #ifndef NDEBUG
    BOOST_FOREACH(NodePtr const & child, node.iter())
      { assert(is_builtin(child->tag())); }
    #endif
  
    // H.3
    // Compute the result and rewrite the node.
    Dispatch<Op>()(node);
  }

  /// The table of built-in H functions.
  h_func_type builtin_h[OP_END] =
  {
      &h_func<OP_INT_ADD>
    , &h_func<OP_INT_SUB>
    , &h_func<OP_INT_MUL>
    , &h_func<OP_INT_DIV>
    , &h_func<OP_FLOAT_ADD>
    , &h_func<OP_FLOAT_SUB>
    , &h_func<OP_FLOAT_MUL>
    , &h_func<OP_FLOAT_DIV>
  };

  std::string builtin_ctor[C_END] = { "Cons", "Nil" };
  std::string builtin_oper[OP_END] = { "+", "-", "*", "/", "+", "-", "*", "/" };
}
