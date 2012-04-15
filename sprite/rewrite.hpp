/**
 * @file
 * @brief Defines the rewrite operation.
 */
#pragma once
#include "sprite/node.hpp"

namespace sprite
{
  /// Rewrite a node to a CTOR or OPER node.
  template<TagValue CtorOrOper> struct rewrite
  {
    rewrite() {}
    BOOST_STATIC_ASSERT(CtorOrOper==CTOR || CtorOrOper==OPER);
    #define F(z,n,_)                                             \
        void operator()(                                         \
            Node & node, size_t id                               \
            BOOST_PP_ENUM_TRAILING_PARAMS(n,NodePtr const & arg) \
          ) const                                                \
        {                                                        \
          node.destroy_payload();                                \
          new(node._payload()) payloads::InPlace<n>(             \
              BOOST_PP_ENUM_PARAMS(n,arg)                        \
            );                                                   \
          node.m_id = id;                                        \
          node.m_arity = n;                                      \
          node.m_tag = CtorOrOper;                               \
        }                                                        \
        /**/
    BOOST_PP_REPEAT(SPRITE_INPLACE_BOUND,F,)
    #undef F

    #if 0
    // TODO
    void operator()(
        Node & node, size_t id, NodePtr const & arg0, NodePtr const & arg1
      ) const
    {
      node.destroy_payload();
      // new(node._payload()) payloads::ChildList(arg0,arg1);
      node.m_id = id;
      node.m_tag = CHOICE;
    }
    #endif
  };

  /// Rewrite a node to a FAIL.
  template<> struct rewrite<FAIL>
  {
    rewrite() {}
    void operator()(Node & node) const
    {
      node.destroy_payload();
      node.m_tag = FAIL;
    }
  };

  /// Rewrite a node to a CHOICE.
  template<> struct rewrite<CHOICE>
  {
    rewrite() {}
    void operator()(
        Node & node, size_t id, NodePtr const & lhs, NodePtr const & rhs
      ) const
    {
      node.destroy_payload();
      new(node._payload()) payloads::Choice(lhs,rhs);
      node.m_id = id;
      node.m_tag = CHOICE;
    }
  };

  /// Rewrite a node to a FWD.
  template<> struct rewrite<FWD>
  {
    rewrite() {}
    void operator()(Node & node, NodePtr const & dest) const
    {
      node.destroy_payload();
      new(node._payload()) payloads::Fwd(dest);
      node.m_tag = FWD;
    }
  };

  /// Rewrite a node to an INT.
  template<> struct rewrite<INT>
  {
    rewrite() {}
    void operator()(Node & node, meta::ValueType<INT>::type value) const
    {
      node.destroy_payload();
      new(node._payload()) payloads::Int(value);
      node.m_tag = INT;
    }
  };

  /// Rewrite a node to a FLOAT.
  template<> struct rewrite<FLOAT>
  {
    rewrite() {}
    void operator()(Node & node, meta::ValueType<FLOAT>::type value) const
    {
      node.destroy_payload();
      new(node._payload()) payloads::Float(value);
      node.m_tag = FLOAT;
    }
  };

  // A minor convenience, perhaps.  These aliases prevent having to construct
  // an instance of rewrite<Tag> to perform a rewrite step when the Tag is
  // not a variable.

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
}
