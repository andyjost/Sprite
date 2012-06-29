/**
 * @file
 * @brief Defines the payload types.  See documentation of Node.
 */
#pragma once
#include "sprite/common.hpp"
#include "sprite/pointer.hpp"
#include <boost/pool/pool.hpp>

namespace sprite
{
  static size_t const PAYLOAD_BYTES = 16;

  /// Pools for child lists of length 1,2,...,n.
  extern boost::pool<> * childpool;

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

    /**
     * @brief A payload containing a dynamically-sized list of children.
     *
     * @note Storing an extra copy of the arity here simplfies copy and
     * assignment.
     */
    struct ChildList : Unused<PAYLOAD_BYTES - sizeof(size_t) - sizeof(NodePtr*)>
    {
      ChildList(NodePtr * args, size_t size)
        : m_size(size), m_args(args)
      {
        assert(m_size>2);
      }

      ChildList(ChildList const & arg)
        : m_size(arg.m_size), m_args(new NodePtr[arg.m_size])
      {
        try
        {
          std::copy(&arg.m_args[0], &arg.m_args[m_size], &this->m_args[0]);
        }
        catch(...)
        {
          delete_(m_args, m_size);
          throw;
        }
      }

      ChildList & operator=(ChildList const & arg)
      {
        size_t const size = m_size;
        NodePtr * const args = m_args;

        try
          { new(this) ChildList(arg); }
        catch(...)
        {
          this->m_size = size;
          this->m_args = args;
          throw;
        }

        delete_(args, size);
        return *this;
      }
      ~ChildList()
      {
        delete_(m_args, m_size);
      }

      size_t size() const { return m_size; }
      NodePtr * args() const { return m_args; }

    private:
      void delete_(NodePtr * p, size_t size)
      {
        assert(size < SPRITE_REWRITE_ARG_BOUND);
        for(size_t i=0; i<size; ++i) { p[i].~NodePtr(); }
        childpool[size].free(p);
      }
      size_t m_size;
      NodePtr * m_args;
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

    /// An char payload for the built in Char type.
    struct Char : Unused<PAYLOAD_BYTES - sizeof(meta::ValueType<CHAR>::type)>
    { 
      typedef meta::ValueType<CHAR>::type value_type;
      value_type value;
      Char(meta::ValueType<CHAR>::type value_) : value(value_) {}
    };
    BOOST_STATIC_ASSERT(sizeof(Char) == PAYLOAD_BYTES);
  }

  namespace meta
  {
    template<typename Payload> struct IsBuiltinPayload : mpl::false_ {};
    template<> struct IsBuiltinPayload<payloads::Int> : mpl::true_ {};
    template<> struct IsBuiltinPayload<payloads::Float> : mpl::true_ {};
    template<> struct IsBuiltinPayload<payloads::Char> : mpl::true_ {};
  }
}

