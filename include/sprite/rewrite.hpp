/**
 * @file
 * @brief Defines the rewrite operation.
 */
#pragma once
#include "sprite/node.hpp"

namespace sprite
{
  /**
   * @brief Rewrites a node to an OPER node.
   *
   * The tag is set to OPER, and @p id is the operation ID.  The @p NodePtr
   * arguments are taken by value, since the root payload is destroyed first
   * and may refer to them.
   */
  template<> struct rewrite<OPER>
  {
    rewrite() {}
    #define F(z,n,_)                                           \
        void operator()(                                       \
            Node & node, size_t id                             \
            BOOST_PP_ENUM_TRAILING_PARAMS(n,NodePtr const arg) \
          ) const                                              \
        {                                                      \
          SPRITE_COUNT(CNT_RW);                                \
          node.destroy_payload();                              \
          new(node._payload()) payloads::InPlace<n>(           \
              BOOST_PP_ENUM_PARAMS(n,arg)                      \
            );                                                 \
          node.m_arity = n;                                    \
          node.m_id = id;                                      \
          node.m_tag = OPER;                                   \
          node.m_cnf = 0;                                      \
        }                                                      \
        /**/
    BOOST_PP_REPEAT(SPRITE_INPLACE_BOUND,F,)
    #undef F

    #ifdef SPRITE_USE_POOLING
      #define SPRITE_INIT_CHILD(z,i,_)                 \
          new(&args[i]) NodePtr(BOOST_PP_CAT(arg, i)); \
        /**/

      #define SPRITE_INIT_CHILDREN(z,n)                      \
          NodePtr * args = (NodePtr *)childpool[n].malloc(); \
          BOOST_PP_REPEAT_ ## z(n,SPRITE_INIT_CHILD,)        \
          /**/
    #else
      #define SPRITE_INIT_CHILDREN(z,n)                       \
          NodePtr args_[n] = { BOOST_PP_ENUM_PARAMS(n,arg) }; \
          NodePtr * args = new NodePtr[n];                    \
          std::copy(&args_[0], &args_[n], &args[0]);          \
        /**/
    #endif

    /**
     * The @p NodePtr arguments are taken by value, since the root payload is
     * destroyed first and may refer to them.
     *
     * @note: ChildList takes ownership of the args pointer.  There's no need
     * to be exception-safe, since all errors are unrecoverable.
     */
    #define F(z,n,_)                                          \
        void operator()(                                      \
            Node & node, size_t id                            \
          , BOOST_PP_ENUM_PARAMS(n, NodePtr const arg)        \
          ) const                                             \
        {                                                     \
          SPRITE_COUNT(CNT_RW);                               \
          node.destroy_payload();                             \
          SPRITE_INIT_CHILDREN(z,n);                          \
          new(node._payload()) payloads::ChildList(args, n);  \
          node.m_arity = n;                                   \
          node.m_tag = OPER;                                  \
          node.m_id = id;                                     \
          node.m_cnf = 0;                                     \
        }                                                     \
    /**/
    BOOST_PP_REPEAT_FROM_TO(SPRITE_INPLACE_BOUND,SPRITE_REWRITE_ARG_BOUND,F,)
    #undef F
  };

  /**
   * @brief Rewrites a node to a CTOR node.
   *
   * The tag member holds the static constructor identifier, which is a value
   * greater than or equal to CTOR.  The tag is set to that.  The id is
   * set to the dynamic constructor identifer (which is assigned at program load
   * time).
   */
  template<> struct rewrite<CTOR>
  {
    rewrite() {}
    #define F(z,n,_)                                           \
        template<typename Enum>                                \
        void operator()(                                       \
            Node & node, Enum tag, size_t id                   \
            BOOST_PP_ENUM_TRAILING_PARAMS(n,NodePtr const arg) \
          ) const                                              \
        {                                                      \
          SPRITE_COUNT(CNT_RW);                                \
          node.destroy_payload();                              \
          new(node._payload()) payloads::InPlace<n>(           \
              BOOST_PP_ENUM_PARAMS(n,arg)                      \
            );                                                 \
          node.m_arity = n;                                    \
          assert((int)tag >= (int)CTOR);                       \
          node.m_tag = make_ctor_tag(tag);                     \
          node.m_id = id;                                      \
          node.m_cnf = 0;                                      \
        }                                                      \
        /**/
    BOOST_PP_REPEAT(SPRITE_INPLACE_BOUND,F,)
    #undef F

    /**
     * The @p NodePtr arguments are taken by value, since the root payload is
     * destroyed first and may refer to them.
     *
     * @note: ChildList takes ownership of the args pointer.  There's no need
     * to be exception-safe, since all errors are unrecoverable.
     */
    #define F(z,n,_)                                          \
        template<typename Enum>                               \
        void operator()(                                      \
            Node & node, Enum tag, size_t id                  \
          , BOOST_PP_ENUM_PARAMS(n, NodePtr const arg)        \
          ) const                                             \
        {                                                     \
          SPRITE_COUNT(CNT_RW);                               \
          node.destroy_payload();                             \
          SPRITE_INIT_CHILDREN(z,n);                          \
          new(node._payload()) payloads::ChildList(args, n);  \
          node.m_arity = n;                                   \
          assert((int)tag >= (int)CTOR);                      \
          node.m_tag = make_ctor_tag(tag);                    \
          node.m_id = id;                                     \
          node.m_cnf = 0;                                     \
        }                                                     \
    /**/
    BOOST_PP_REPEAT_FROM_TO(SPRITE_INPLACE_BOUND,SPRITE_REWRITE_ARG_BOUND,F,)
    #undef F
  };

  /// Rewrites a node to FAIL.
  template<> struct rewrite<FAIL>
  {
    rewrite() {}
    void operator()(Node & node) const
    {
      SPRITE_COUNT(CNT_RW);
      node.destroy_payload();
      node.m_tag = FAIL;
      node.m_cnf = 0;
    }
  };

  /// Rewrites a node to CHOICE.
  template<> struct rewrite<CHOICE>
  {
    rewrite() {}
    void operator()(
        Node & node, size_t id, NodePtr const lhs, NodePtr const rhs
      ) const
    {
      SPRITE_COUNT(CNT_RW);
      node.destroy_payload();
      new(node._payload()) payloads::Choice(lhs,rhs);
      node.m_id = id;
      node.m_tag = CHOICE;
      node.m_cnf = 0;
    }
  };

  /// Rewrites a node to FWD.
  template<> struct rewrite<FWD>
  {
    rewrite() {}
    void operator()(Node & node, NodePtr const dest) const
    {
      SPRITE_COUNT(CNT_RW);
      node.destroy_payload();
      new(node._payload()) payloads::Fwd(dest);
      node.m_tag = FWD;
      node.m_cnf = dest->m_cnf;
    }
  };

  /// Rewrites a node to INT.
  template<> struct rewrite<INT>
  {
    rewrite() {}
    void operator()(Node & node, meta::ValueType<INT>::type value) const
    {
      SPRITE_COUNT(CNT_RW);
      node.destroy_payload();
      new(node._payload()) payloads::Int(value);
      node.m_tag = INT;
      node.m_cnf = 1;
    }
  };

  /// Rewrites a node to FLOAT.
  template<> struct rewrite<FLOAT>
  {
    rewrite() {}
    void operator()(Node & node, meta::ValueType<FLOAT>::type value) const
    {
      SPRITE_COUNT(CNT_RW);
      node.destroy_payload();
      new(node._payload()) payloads::Float(value);
      node.m_tag = FLOAT;
      node.m_cnf = 1;
    }
  };

  /// Rewrites a node to CHAR.
  template<> struct rewrite<CHAR>
  {
    rewrite() {}
    void operator()(Node & node, meta::ValueType<CHAR>::type value) const
    {
      SPRITE_COUNT(CNT_RW);
      node.destroy_payload();
      new(node._payload()) payloads::Char(value);
      node.m_tag = CHAR;
      node.m_cnf = 1;
    }
  };

  // A minor convenience, perhaps.  These aliases prevent having to construct
  // an instance of rewrite<Tag> to perform a rewrite step when Tag is not a
  // variable (i.e., a template parameter).

  /// Rewrites a node to type CTOR.
  rewrite<CTOR> const rewrite_ctor = rewrite<CTOR>();

  /// Rewrites a node to type OPER.
  rewrite<OPER> const rewrite_oper = rewrite<OPER>();

  /// Rewrites a node to type FAIL.
  rewrite<FAIL> const rewrite_fail = rewrite<FAIL>();

  /// Rewrites a node to type CHOICE.
  rewrite<CHOICE> const rewrite_choice = rewrite<CHOICE>();

  /// Rewrites a node to type FWD.
  rewrite<FWD> const rewrite_fwd = rewrite<FWD>();

  /// Rewrites a node to type INT.
  rewrite<INT> const rewrite_int = rewrite<INT>();

  /// Rewrites a node to type FLOAT.
  rewrite<FLOAT> const rewrite_float = rewrite<FLOAT>();

  /// Rewrites a node to type CHAR.
  rewrite<CHAR> const rewrite_char = rewrite<CHAR>();
}
