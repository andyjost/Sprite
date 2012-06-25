/** 
 * @file
 * @brief Implements Node members.
 */
#include "sprite/visit.hpp"

#ifdef SPRITE_USE_POOLING
#include <boost/pool/object_pool.hpp>
#else
#include <cstdlib>
#endif

//==============================================
// Implementation of Node::new and Node::delete.
//==============================================
namespace sprite
{
  // This memory pool calls the node object destructors upon destruction.
  #ifdef SPRITE_USE_POOLING
  extern boost::object_pool<AbstractNode> node_allocator;
  #endif

  inline void * Node::operator new(size_t bytes)
  {
    // Bare Node objects should not be allocated directly.  Instead, a concrete
    // instance of Node_<Payload> should be allocated.
    assert(NODE_BYTES == bytes);
    #ifdef SPRITE_USE_POOLING
    void * px = reinterpret_cast<void *>(node_allocator.malloc());
    #else
    void * px = std::malloc(NODE_BYTES);
    #endif

    // Note: a custom raw memory allocator would need to be specified to
    // object_pool to meet this requirement.

    #if 0
    // We're aiming for exactly 2 nodes per cache line (on modern x86_64
    // hardware).  Verify the alignment to ensure that nodes don't span cache
    // line boundaries.
    assert(reinterpret_cast<size_t>(px) % NODE_BYTES == 0);
    #endif
    return px;

  }
  inline void Node::operator delete(void * p)
  #ifdef SPRITE_USE_POOLING
    // Does not call p's destructor
    { node_allocator.free(reinterpret_cast<AbstractNode*>(p)); }
  #else
    { std::free(p); }
  #endif
}

//==============================
// Implementation of Node::iter.
//==============================
namespace sprite
{
  namespace visitors
  {
    /// Implements Node::iter.
    struct Iter : static_visitor<Node::range_type>
    {
      // Handle node types with children.
      result_type operator()(InPlaceNode1 & node) const
      {
        return result_type(
            &node.payload.arg, &node.payload.arg + 1
          );
      }
      result_type operator()(InPlaceNode2 & node) const
      {
        return result_type(
            &node.payload.arg0, &node.payload.arg1 + 1
          );
      }
      result_type operator()(ChildListNode & node) const
      { 
        payloads::ChildList const & list = node.payload;
        return result_type(&list.args()[0], &list.args()[node.arity()]);
      }

      // Handle node types without children.
      template<typename NodeType>
      result_type operator()(NodeType &) const
      {
        // Build an empty range without using singular pointers.
        static NodePtr tmp;
        return result_type(&tmp,&tmp);
      }
    };
  }

  // Normally, the const implementation would be shared by using const_cast to
  // cast the result back, but in this case there's no suitable const_cast for
  // const_range_type to range_type.  Instead, the non-const implementation is
  // shared, so the above visitor really shouldn't modify anything.

  inline Node::range_type Node::iter()
  {
    static visitors::Iter const visitor;
    return visit(visitor, *this);
  }
  inline Node::const_range_type Node::iter() const
  {
    static visitors::Iter const visitor;
    return visit(visitor, const_cast<Node &>(*this));
  }
}

//====================================
// Implementation of Node::operator[].
//====================================
namespace sprite
{
  namespace visitors
  {
    /// Implements Node::operator[].
    struct At : static_visitor<NodePtr const &>
    {
      // A forwarding node should never be obtained for use here.
      result_type operator()(FwdNode const &, size_t) const
        { throw RuntimeError("Unexpected forward node."); }

      // Handle node types with children.
      result_type operator()(InPlaceNode1 const & node, size_t i) const
      {
        assert(i<1);
        return node.payload.arg;
      }
      result_type operator()(InPlaceNode2 const & node, size_t i) const
      {
        switch(i)
        {
          case 0: return node.payload.arg0;
          case 1: return node.payload.arg1;
          default: throw RuntimeError("Child index is out of range.");
        }
      }
      result_type operator()(ChildListNode const & node, size_t i) const
      { 
        assert(i<node.arity());
        return node.payload.args()[i];
      }

      // Handle node types without children.
      template<typename NodeType>
      result_type operator()(NodeType const &, size_t) const
        { throw RuntimeError("Child index is out of range."); }
    };
  }

  inline NodePtr & Node::operator[](size_t i)
  {
    return const_cast<NodePtr &>(
        static_cast<Node const *>(this)->operator[](i)
      );
  }
  inline NodePtr const & Node::operator[](size_t i) const
  {
    static visitors::At const visitor;
    return visit(tr1::bind<NodePtr const &>(visitor, _1, i), *this);
  }
}

//==================================
// Implementation of Node::position.
//==================================
namespace sprite
{
  namespace visitors
  {
    /// Implements Node::position.
    struct Position : static_visitor<size_t>
    {
      // Handle node types with children.
      result_type operator()(
          InPlaceNode1 const & node, NodePtr const & child
        ) const
      {
        assert(&node.payload.arg == &child);
        return 0;
      }
      result_type operator()(
          InPlaceNode2 const & node, NodePtr const & child
        ) const
      {
        size_t const i = &child - &node.payload.arg0;
        assert(i<2);
        return i;
      }
      result_type operator()(
          ChildListNode const & node, NodePtr const & child
        ) const
      { 
        size_t const i = &child - &node.payload.args()[0];
        assert(i<node.arity());
        return i;
      }

      // Handle node types without children.
      template<typename NodeType>
      result_type operator()(NodeType const &, NodePtr const &) const
        { throw RuntimeError("Invalid parent node."); }
    };
  }

  inline size_t Node::position(NodePtr const & child) const
  {
    static visitors::Position const visitor;
    return visit(tr1::bind<size_t>(visitor, _1, tr1::cref(child)), *this);
  }
}

//===============================
// Implementation of Node::clone.
//===============================
namespace sprite
{
  namespace visitors
  {
    /// Implements Node::clone.
    struct Clone : static_visitor<NodePtr>
    {
      template<typename NodeType>
      result_type operator()(NodeType const & node) const
      {
        NodePtr p(new NodeType(node));
        return p;
      }
    };
  }

  inline NodePtr Node::clone()
  {
    static visitors::Clone const visitor;
    return visit(visitor, *this);
  }
}

//=========================================
// Implementation of Node::destroy_payload.
//=========================================
namespace sprite
{
  namespace visitors
  {
    /// Implements Node::destroy_payload.
    struct DestroyPayload : static_visitor<void>
    {
      template<typename Payload>
      result_type operator()(Node_<Payload> & node) const
        { node.payload.~Payload(); }
    };
  }

  inline void Node::destroy_payload()
  {
    static visitors::DestroyPayload const visitor;
    return visit(visitor, *this);
  }
}
