/**
 * @file
 * @brief Defines the payload types.  See documentation of Node.
 */
#pragma once
#include "sprite/common.hpp"
#include "sprite/pointer.hpp"

namespace sprite
{
  static size_t const PAYLOAD_BYTES = 16;

  namespace payloads
  {
    /// The unused payload; for abstract and failure nodes.
    template<size_t Bytes = PAYLOAD_BYTES>  
      struct Unused { char unused[Bytes]; };
   
    /// A payload of zero, one or two children for an OPER or CTOR node.
    template<size_t N> struct InPlace;

    /// Zero children.
    template<> struct InPlace<0> : Unused<> {};
    BOOST_STATIC_ASSERT(sizeof(InPlace<0>) == PAYLOAD_BYTES);

    /// One child, in place.
    template<> struct InPlace<1> : Unused<PAYLOAD_BYTES-1*sizeof(NodePtr*)>
    {
      NodePtr arg;
      InPlace(NodePtr const & arg_) : arg(arg_) {}
    };
    BOOST_STATIC_ASSERT(sizeof(InPlace<1>) == PAYLOAD_BYTES);

    /// Two children, in place.
    template<> struct InPlace<2> : Unused<PAYLOAD_BYTES-2*sizeof(NodePtr*)>
    {
      NodePtr arg0, arg1;
      InPlace(NodePtr const & arg0_, NodePtr const & arg1_)
        : arg0(arg0_), arg1(arg1_)
      {}
    };
    BOOST_STATIC_ASSERT(sizeof(InPlace<2>) == PAYLOAD_BYTES);

    /// A payload containing an arbitrary-length list of children.
    struct ChildList : Unused<PAYLOAD_BYTES - sizeof(size_t) - sizeof(NodePtr*)>
    {
      // TODO copy, construct
      size_t n;
      NodePtr * children;
      ChildList(size_t n_) : n(n_), children(new NodePtr[n])
        { assert(n>2); }
      ~ChildList() { delete[] children; }
    };
    BOOST_STATIC_ASSERT(sizeof(ChildList) == PAYLOAD_BYTES);

    /// A payload containing exactly two children for choice nodes.
    struct Choice : Unused<PAYLOAD_BYTES-2*sizeof(NodePtr)>
    {
      NodePtr lhs, rhs;
      Choice(NodePtr const & lhs_, NodePtr const & rhs_)
        : lhs(lhs_), rhs(rhs_)
      {}
    };
    BOOST_STATIC_ASSERT(sizeof(Choice) == PAYLOAD_BYTES);

    /**
     * @brief A payload for forward reference nodes.
     *
     * Contains a single pointer to a destination node.
     */
    struct Fwd : Unused<PAYLOAD_BYTES-sizeof(NodePtr*)>
    {
      NodePtr dest;
      Fwd(NodePtr const & dest_) : dest(dest_) {}
    };
    BOOST_STATIC_ASSERT(sizeof(Fwd) == PAYLOAD_BYTES);

    /// An integer payload (64 bit) for the built in Int type.
    struct Int : Unused<PAYLOAD_BYTES - sizeof(meta::ValueType<INT>::type)>
    { 
      typedef meta::ValueType<INT>::type value_type;
      value_type value;
      Int(meta::ValueType<INT>::type value_) : value(value_) {}
    };
    BOOST_STATIC_ASSERT(sizeof(Int) == PAYLOAD_BYTES);

    /// A floating-point payload for the built in Float type.
    struct Float : Unused<PAYLOAD_BYTES - sizeof(meta::ValueType<FLOAT>::type)>
    { 
      typedef meta::ValueType<FLOAT>::type value_type;
      value_type value;
      Float(meta::ValueType<FLOAT>::type value_) : value(value_) {}
    };
    BOOST_STATIC_ASSERT(sizeof(Float) == PAYLOAD_BYTES);
  }
}

