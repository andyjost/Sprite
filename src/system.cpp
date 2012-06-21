#include "sprite/system.hpp"
#include "sprite/builtins.hpp"
#include "sprite/exec.hpp"
#include "sprite/currylib/SpritePrelude.hpp"

// ====== Guards ======

// The type of the Prelude module.
typedef sprite::user::m_13SpritePrelude::Module Prelude;

namespace
{
  using namespace sprite;

  // Rewrite a node to Prelude.True.
  inline void rewrite_true(Prelude const & prelude, Node & node)
  {
    return rewrite_ctor(
        node, user::m_13SpritePrelude::c_4True, prelude.cl_4True
      );
  }

  // Rewrite a node to Prelude.False.
  inline void rewrite_false(Prelude const & prelude, Node & node)
  {
    return rewrite_ctor(
        node, user::m_13SpritePrelude::c_5False, prelude.cl_5False
      );
  }

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
  template<> struct GuardOf<OP_INT_MOD> : mpl::identity<DivGuard> {};
  template<> struct GuardOf<OP_FLOAT_DIV> : mpl::identity<DivGuard> {};

  // ====== UnguardedExecute ======

  /// Executes an operation without any guard.
  template<BuiltinOp Op> struct UnguardedExecute;
  #define SPRITE_DEFINE_OP(builtin_op, rv, op)            \
      template<> struct UnguardedExecute<builtin_op>      \
      {                                                   \
        UnguardedExecute() {}                             \
                                                          \
        template<typename T>                              \
        rv operator()(T const & lhs, T const & rhs) const \
          { return (lhs op rhs); }                        \
      };                                                  \
      /**/

  SPRITE_DEFINE_OP(OP_INT_ADD, T, +)
  SPRITE_DEFINE_OP(OP_INT_SUB, T, -)
  SPRITE_DEFINE_OP(OP_INT_MUL, T, *)
  SPRITE_DEFINE_OP(OP_INT_DIV, T, /)
  SPRITE_DEFINE_OP(OP_INT_MOD, T, %)
  SPRITE_DEFINE_OP(OP_LT, bool, <)
  SPRITE_DEFINE_OP(OP_LE, bool, <=)
  SPRITE_DEFINE_OP(OP_EQ, bool, ==)
  SPRITE_DEFINE_OP(OP_NE, bool, !=)
  SPRITE_DEFINE_OP(OP_GE, bool, >=)
  SPRITE_DEFINE_OP(OP_GT, bool, >)
  SPRITE_DEFINE_OP(OP_FLOAT_ADD, T, +)
  SPRITE_DEFINE_OP(OP_FLOAT_SUB, T, -)
  SPRITE_DEFINE_OP(OP_FLOAT_MUL, T, *)
  SPRITE_DEFINE_OP(OP_FLOAT_DIV, T, /)

  #undef SPRITE_DEFINE_OP

  // ====== GuardedExecute ======

  template<BuiltinOp Op, bool Comparison=meta::IsComparison<Op>::value>
      struct GuardedExecute;

  /**
   * @brief Executes an built-in operation with a guard.
   *
   * If the guard fails, then FAIL is written to the destination node.  This
   * specialization handles operations whose result is a built-in type, e.g.,
   * Int + Int -> Int.
   */
  template<BuiltinOp Op> struct GuardedExecute<Op, false>
  {
    GuardedExecute() {}

    template<typename T>
    void operator()(
        Prelude const &, Node & out, T const & lhs, T const & rhs
      ) const
    {
      static typename GuardOf<Op>::type const guard;
      static UnguardedExecute<Op> const exec;

      if(guard(lhs,rhs))
        { rewrite<meta::TagValueOf<Op>::value>()(out, exec(lhs,rhs)); }
      else
        { rewrite_fail(out); }
    }
  };

  /**
   * @brief Specialization of GuardedExecute for comparison operations.
   * 
   * This specialization handles operations whose result is a Bool, e.g., Int <
   * Int -> Bool.  The Bool type is defined in the prelude.
   */
  template<BuiltinOp Op> struct GuardedExecute<Op, true>
  {
    GuardedExecute() {}

    template<typename T>
    void operator()(
        Prelude const & prelude, Node & out, T const & lhs, T const & rhs
      ) const
    {
      static typename GuardOf<Op>::type const guard;
      static UnguardedExecute<Op> const exec;

      if(guard(lhs,rhs))
      {
        if(exec(lhs,rhs))
          { rewrite_true(prelude, out); }
        else
          { rewrite_false(prelude, out); }
      }
      else
        { rewrite_fail(out); }
    }
  };

  // ====== BuiltinImpl ======

  template<BuiltinOp Op, bool Comparison=meta::IsComparison<Op>::value>
      struct BuiltinImpl;
      
  /**
   * @brief Implements a non-comparison built-in operation.
   *
   * These operations are valid for only the type designated by TagValueOf.
   */
  template<BuiltinOp Op> struct BuiltinImpl<Op,false> : static_visitor<void>
  {
    BuiltinImpl(Prelude const & prelude, Node & node)
      : m_prelude(prelude), m_out(node)
    {}
  private:
    Prelude const & m_prelude;
    Node & m_out;

    /// Determine the node type for this Op.
    typedef typename meta::TagValueOf<Op>::type TagType;
    typedef typename meta::NodeOf<TagType::value>::type NodeType;
  public:
    /// Handles valid cases.
    void operator()(NodeType const & lhs, NodeType const & rhs) const
    {
      static GuardedExecute<Op> const exec;
      exec(m_prelude, m_out, lhs.payload.value, rhs.payload.value);
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

  /**
   * @brief Implements a built-in comparison operation.
   *
   * Comparisons are valid for all built-in types.
   */
  template<BuiltinOp Op> struct BuiltinImpl<Op,true> : static_visitor<void>
  {
    BuiltinImpl(Prelude const & prelude, Node & node)
      : m_prelude(prelude), m_out(node)
    {}
  private:
    Prelude const & m_prelude;
    Node & m_out;
  public:
    /// Handles valid cases.
    template<typename Payload>
    typename enable_if<meta::IsBuiltinPayload<Payload>, void>::type
    operator()(Node_<Payload> const & lhs, Node_<Payload> const & rhs) const
    {
      static GuardedExecute<Op> const exec;
      exec(m_prelude, m_out, lhs.payload.value, rhs.payload.value);
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
    void operator()(Prelude const & prelude, Node & node)
    {
      assert(node.arity() == 1);
      return visit(BuiltinImpl<Op>(prelude, node), *node[0]);
    }
  };

  /// Dispatches a binary built-in operation.
  template<BuiltinOp Op> struct Dispatch<Op,2>
  {
    void operator()(Prelude const & prelude, Node & node)
    {
      assert(node.arity() == 2);
      return visit(BuiltinImpl<Op>(prelude, node), *node[0], *node[1]);
    }
  };
}

namespace sprite
{
  // ====== h_func ======

  /// Implements the H function for a built in operation.
  template<BuiltinOp Op> void h_func(Prelude const & prelude, Node & node)
  {
    // H.4 TODO
    // Q. can this just check against CTOR?
    // Q. how can this be needed?  The only call is from head_normalize.
    if(is_ctor(node.tag())) return;
  
    BOOST_FOREACH(NodePtr & child, node.iter())
    {
      switch(child->tag())
      {
        // H.1 TODO
        case CHOICE: return pull_tab(node, child);
        // H.5 TODO
        case FAIL: return rewrite_fail(node);
        // H.2 TODO
        case OPER: return head_normalize(*child);
        default:;
      }
    }
  
    #ifndef NDEBUG
    BOOST_FOREACH(NodePtr const & child, node.iter())
      { assert(is_builtin(child->tag())); }
    #endif
  
    // H.3 TODO
    // Compute the result and rewrite the node.
    Dispatch<Op>()(prelude, node);
  }
}
namespace sprite
{
  Program::Program() : oper(), ctor_label(), oper_label()
  {
    // Program Initialization.

    // Create placeholders for all of the built-in operations.  This is so that
    // their indices are known and can be accessed through the corresponding
    // enum values.  The order here must match the declaration order in enum
    // BuiltinOp.
    this->insert_oper("<", 0);   // Comparison
    this->insert_oper("<=", 0);
    this->insert_oper("==", 0);
    this->insert_oper("/=", 0);
    this->insert_oper(">=", 0);
    this->insert_oper(">", 0);
    this->insert_oper("+", 0);   // Integer
    this->insert_oper("-", 0);
    this->insert_oper("*", 0);
    this->insert_oper("div", 0);
    this->insert_oper("mod", 0);
    this->insert_oper("+", 0);   // Float
    this->insert_oper("-", 0);
    this->insert_oper("*", 0);
    this->insert_oper("/", 0);

    // Import the prelude.  It is given the name SpritePrelude.
    shared_ptr<Prelude const> prelude = this->import<Prelude>();

    // Add an alias for the Prelude (with the proper name).
    m_imported["Prelude"] = prelude;

    // Now, update the built-in H functions, which require the prelude.
    oper[OP_LT] = tr1::bind(&h_func<OP_LT>, *prelude, _1);
    oper[OP_LE] = tr1::bind(&h_func<OP_LE>, *prelude, _1);
    oper[OP_EQ] = tr1::bind(&h_func<OP_EQ>, *prelude, _1);
    oper[OP_NE] = tr1::bind(&h_func<OP_NE>, *prelude, _1);
    oper[OP_GE] = tr1::bind(&h_func<OP_GE>, *prelude, _1);
    oper[OP_GT] = tr1::bind(&h_func<OP_GT>, *prelude, _1);
    oper[OP_INT_ADD] = tr1::bind(&h_func<OP_INT_ADD>, *prelude, _1);
    oper[OP_INT_SUB] = tr1::bind(&h_func<OP_INT_SUB>, *prelude, _1);
    oper[OP_INT_MUL] = tr1::bind(&h_func<OP_INT_MUL>, *prelude, _1);
    oper[OP_INT_DIV] = tr1::bind(&h_func<OP_INT_DIV>, *prelude, _1);
    oper[OP_INT_MOD] = tr1::bind(&h_func<OP_INT_MOD>, *prelude, _1);
    oper[OP_FLOAT_ADD] = tr1::bind(&h_func<OP_FLOAT_ADD>, *prelude, _1);
    oper[OP_FLOAT_SUB] = tr1::bind(&h_func<OP_FLOAT_SUB>, *prelude, _1);
    oper[OP_FLOAT_MUL] = tr1::bind(&h_func<OP_FLOAT_MUL>, *prelude, _1);
    oper[OP_FLOAT_DIV] = tr1::bind(&h_func<OP_FLOAT_DIV>, *prelude, _1);
  }

  size_t Program::insert_ctor(std::string const & name)
  {
    // TODO: find name collisions?
    ctor_label.push_back(name);
    return ctor_label.size() - 1;
  }

  size_t Program::insert_oper(std::string const & name, h_func_type h)
  {
    // TODO: find name collisions?
    assert(oper.size() == oper_label.size());

    oper.push_back(h);
    oper_label.push_back(name);
    return oper_label.size() - 1;
  }

  size_t Module::install_oper(std::string const & label, h_func_type const & h)
  {
    // Register the operation with the program.
    size_t const id = m_pgm.insert_oper(label, h);
  
    // Install the label and ID in the symbol table for this module.
    boost::assign::insert(this->m_opers.left)(label,id);
  
    // Return the ID.
    return id;
  }
  
  size_t Module::install_ctor(std::string const & label)
  {
    // Register the constructor with the program.
    size_t const id = m_pgm.insert_ctor(label);
  
    // Install the label and ID in the symbol table for this module.
    boost::assign::insert(this->m_ctors.left)(label,id);
  
    // Return the ID.
    return id;
  }

  size_t Module::_lookup(std::string const & label, map_type const & map) const
  {
    typedef map_type::left_map::const_iterator iterator;
    iterator const p = map.left.find(label);
    if(p == map.left.end())
      { throw RuntimeError("Failed constructor or operation lookup."); }
    return p->second;
  }
}
