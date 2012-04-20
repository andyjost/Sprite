/**
 * @file
 * @brief Implements visitation for nodes.
 */
#pragma once
#include "sprite/node.hpp"

namespace sprite
{
  /**
   * @brief Unary visitation; calls visitor((Type)(node)).
   *
   * Determines the type of the node, based on its tag and arity, then calls
   * the visitor with the node cast to that type.
   */
  template<typename Visitor>
  inline typename Visitor::result_type
  visit(Visitor const & visitor, Node const & node)
  {
    switch(node.tag())
    {
      #define SPRITE_visit(tag,arity) \
          visitor(static_cast<meta::NodeOf<tag,arity>::type const &>(node));

      case FAIL:   return SPRITE_visit(FAIL,-1);
      case CHOICE: return SPRITE_visit(CHOICE,-1);
      case INT:    return SPRITE_visit(INT,-1);
      case FLOAT:  return SPRITE_visit(FLOAT,-1);
      case CTOR:
      {
        switch(node.arity())
        {
          case 0:  return SPRITE_visit(CTOR,0);
          case 1:  return SPRITE_visit(CTOR,1);
          case 2:  return SPRITE_visit(CTOR,2);
          default: return SPRITE_visit(CTOR,-1);
        }
      }
      case OPER:
      {
        switch(node.arity())
        {
          case 0:  return SPRITE_visit(OPER,0);
          case 1:  return SPRITE_visit(OPER,1);
          case 2:  return SPRITE_visit(OPER,2);
          default: return SPRITE_visit(OPER,-1);
        }
      }
      case FWD: return SPRITE_visit(FWD,-1);
      default: throw RuntimeError("a corrupted node was encountered");

      #undef SPRITE_visit
    }
  }

  namespace detail
  {
    // Wraps a visitor object; removes const qualifiers from the node argument
    // before the visitor is called (safe, as used below).
    template<typename Visitor> struct UnwrapConst
    {
      typedef typename Visitor::result_type result_type;
      explicit UnwrapConst(Visitor const & visitor) : m_visitor(visitor) {}
    private:
      Visitor const & m_visitor;
    public:
      // Unary visitation.
      template<typename Payload>
      result_type operator()(Node_<Payload> const & node) const
        { return m_visitor(const_cast<Node_<Payload> &>(node)); }

      // Binary visitation.
      template<typename Payload0, typename Payload1>
      result_type operator()(
          Node_<Payload0> const & node0, Node_<Payload1> const & node1
        ) const
      {
        return m_visitor(
            const_cast<Node_<Payload0> &>(node0)
          , const_cast<Node_<Payload1> &>(node1)
          );
      }
    };
  }

  /// Non-const form of visitation.
  template<typename Visitor>
  inline typename Visitor::result_type
  visit(Visitor const & visitor, Node & node)
  {
    detail::UnwrapConst<Visitor> const unwrapper(visitor);
    return visit(unwrapper, static_cast<Node const &>(node));
  }

  namespace detail
  {
    // A helper for implementing the binary form of the visit function.  This
    // uses the unary visit to resolve each abstract Node argument
    // step-by-step.
    template<typename Visitor> struct BinaryVisitor
    {
      typedef typename Visitor::result_type result_type;

      // Two abstract args.
      result_type operator()(
          Visitor const & visitor, Node const & lhs, Node const & rhs
        ) const
      {
        return visit(
            tr1::bind<result_type>(*this, visitor, _1, tr1::ref(rhs))
          , lhs
          );
      }

      // One abstract arg.
      template<typename Lhs>
      result_type operator()(
          Visitor const & visitor, Lhs const & lhs, Node const & rhs
        ) const
      { return visit(tr1::bind<result_type>(*this, visitor, lhs, _1), rhs); }

      // Zero abstract args.
      template<typename Lhs, typename Rhs>
      result_type operator()(
          Visitor const & visitor, Lhs const & lhs, Rhs const & rhs
        ) const
      { return visitor(lhs, rhs); }
    };
  }

  /**
   * @brief Binary visitation; calls visitor((TypeLhs)(lhs), (TypeRhs)(rhs))
   *
   * Determines the type of each node, then calls the visitor with both nodes
   * cast to those types.
   *
   * Rather than support all four possible overloads related to the const
   * qualifier on Node arguments, just support the cases where both are
   * qualified or neither one is.
   */
  template<typename Visitor>
  inline typename Visitor::result_type
  visit(Visitor const & visitor, Node const & lhs, Node const & rhs)
    { return detail::BinaryVisitor<Visitor>()(visitor, lhs, rhs); }

  /// Non-const form of binary visitation.
  template<typename Visitor>
  inline typename Visitor::result_type
  visit(Visitor const & visitor, Node & lhs, Node & rhs)
  {
    detail::UnwrapConst<Visitor> const unwrapper(visitor);
    return visit(unwrapper
      , static_cast<Node const &>(lhs), static_cast<Node const &>(rhs)
      );
  }
}

