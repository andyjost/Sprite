/** 
 * @file
 * @brief Defines NodePtr, the smart pointer that manages nodes.
 */
#pragma once
#include <boost/intrusive_ptr.hpp>

namespace sprite
{
  struct Node;
  struct NodePtr;
  bool skip_fwd_ref(NodePtr & ptr, Node & ref);

  /**
   * @brief A reference-counting pointer for Node objects.
   *
   * This is based on boost::intrusive_ptr, so the reference count is stored
   * within the Node object itself (to maximize performance).  All
   * dereferencing operations skip over FWD nodes, which are nodes that simply
   * forward their reference to a new target.  Those may occur when a node with
   * multiple external references is rewritten.
   */
  struct NodePtr : private boost::intrusive_ptr<Node>
  {
  private:
    typedef boost::intrusive_ptr<Node> base_type;
  public:
    typedef Node element_type;

    NodePtr() {}
    NodePtr(Node * p, bool add_ref = true) : base_type(p,add_ref) {}
    NodePtr(NodePtr const & r) : base_type(r) {}

    using base_type::operator=;
    using base_type::reset;
    using base_type::swap;
    using base_type::operator unspecified_bool_type;
    using base_type::operator!;

    /// Removes any FWD references.
    NodePtr & remove_fwd()
    {
      // Skip FWD nodes.  The implementation is supplied externally by the function
      // skip_fwd_ref.
      Node * ref = this->base_type::get();
      if(!ref) return *this;

      while(true)
      {
        if(!skip_fwd_ref(*this, *ref)) break;
        ref = this->base_type::get();
        assert(ref);
      }
      return *this;
    }

    /// Gets the pointer value, after skipping any FWD nodes.
    using base_type::get;
    using base_type::operator*;
    using base_type::operator->;

    /**
     * @brief Dereferences a node pointer and then indexes the node.
     *
     * This function provides a simplified syntax for indexing.
     *
     * Precondition: the point is not NULL, and the index is in-bounds.
     */
    NodePtr & operator[](size_t i) const;

    /**
     * @brief Enables assignment from a Node (simplifies some parts of the
     * implementation).
     */
    NodePtr & operator=(Node &);
  };

  // Define operators ==, != and < for NodePtr.
  #define SPRITE_BINARY_OP_DECL(op)                               \
    inline bool operator op(NodePtr const & a, NodePtr const & b) \
      { return a.get() op b.get(); }                              \
    /**/
  SPRITE_BINARY_OP_DECL(==)
  SPRITE_BINARY_OP_DECL(!=)
  SPRITE_BINARY_OP_DECL(<)
  #undef SPRITE_BINARY_OP_DECL
}
