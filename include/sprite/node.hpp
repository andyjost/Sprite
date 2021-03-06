/**

 * @file
 * @brief Defines the Node type.
 */
#pragma once
#include "sprite/common.hpp"
#include "sprite/payloads.hpp"
#include "sprite/pointer.hpp"
#include <boost/utility.hpp>
#include <boost/range/iterator_range.hpp>

namespace sprite
{
  // =============
  // Forward defs.
  // =============
  template<TagValue> struct rewrite;
  template<typename Payload> struct Node_;
  namespace visitors { struct Clone; }

  /**
   * @brief An expression node.
   *
   * The subject of computations in this system.  Expressions are graphs made
   * up of Node instances, and computations are changes to the graph that come
   * about by rewriting nodes.
   *
   * Every node has a fixed region consisting of its refcount, tag, id, arity
   * and flags, plus a variable region called the payload.  This class defines
   * only the fixed region.  A complete node is an instance of Node_<Payload>
   * for some Payload type.  The node is a discriminated union, where the tag
   * member determines the type of the payload contents.  In certain cases, the
   * arity is also used to determine the payload type.  The possible payload
   * types are defined in the payloads namespace.
   *
   * For constructor nodes, the tag member encodes the identity of the
   * constructor.  The constructors for any given type are numbered
   * sequentially beginning at OPER.
   *
   * For operation nodes, the id member identifies which operation is used.
   * The id is an index into a corresponding table in the program, which can be
   * used to get information about the program entity, such as its name (label)
   * or implementation (H) function.  For choice nodes, the id is the choice
   * identifier.
   *
   * The arity is stored within a node simply as an optimization.  This
   * prevents us having to repeatedly look up the arity in the program
   * description.
   *
   * The flags are used for optimization (e.g., to indicate when a node is
   * known to be in CNF, due to a previous test).
   *
   * Data members that are either unused or that can have only one possible
   * value for a given tag are not updated during a rewrite.  For instance, a
   * node with the tag FAIL (representing a failed computation) will not have
   * meaningful values for id or arity.  Less obvious, perhaps, is that a node
   * with the tag CHOICE, will have no meaningful value for arity, even though
   * it always has exactly two children.  In general, it should be obvious from
   * the tag and the above characterization which data members have meaningful
   * values.
   *
   * Nodes are managed through intrusive reference counting.  The smart pointer
   * type NodePtr is used throughout this program to refer to nodes.  It
   * manages the refcount member and, when the count drops to zero, deletes the
   * Node instance.  All memory allocation for nodes is pooled.
   */
  struct Node
  {
    // ====== Data Accessors. ======

    /// Returns the reference count.
    uint32 refcount() const { return this->m_refcount; }

    /// Returns the tag member.
    TagValue tag() const { return this->m_tag; }

    /// Returns the id member. 
    uint32 id() const { return this->m_id; }

    /// Returns the arity member.
    uint16 arity() const { return this->m_arity; }

    // ====== Attribute Accessors ======

    /// Returns true if the node is in CNF.
    bool is_cnf() const
    {
      if(this->m_cnf) return true;
      if(!is_ctor(this->tag())) return false;

      BOOST_FOREACH(NodePtr const & child, this->iter())
        { if(!child->is_cnf()) return false; }

      this->m_cnf = 1;
      return true;
    }


    // ====== Abstract Object Management. ======

    /**
     * @brief Clone this node, including its payload.
     *
     * This will produce a complete node, i.e., an instance of Node_<Payload>.
     */
    NodePtr clone();

    /// Create a new complete node.
    #define F(z,n,_)                                                         \
        template<TagValue Value BOOST_PP_ENUM_TRAILING_PARAMS(n,typename T)> \
        static NodePtr create(BOOST_PP_ENUM_BINARY_PARAMS(n,T,const & t));   \
        /**/
    // Increment by 3, because rewrite_* takes up to 3 arguments before the
    // child nodes.
    BOOST_PP_REPEAT(BOOST_PP_ADD(3,SPRITE_REWRITE_ARG_BOUND),F,)
    #undef F

    /// Gets the raw address of the payload region.
    void * _payload() { return this + 1; }
    void const * _payload() const { return this + 1; }

    /// Gets the target of a FWD node without checking the tag.
    NodePtr & _fwdtarget();

  private:

    // ====== Object management. ======

    // Everything in this section is private.  Use the abstract interface (above)
    // to manage nodes.

    friend struct visitors::Clone; // Needs constructors.
    template<typename> friend struct Node_; // Needs ~Node.
    template<TagValue> friend struct rewrite; // Needs destroy_payload.

    /// The constructor only initializes the refcount.
    Node() : m_refcount(0) {}

    /// Copy construction (resets the refcount).
    Node(Node const & x)
      : m_refcount(0), m_tag(x.m_tag), m_id(x.m_id), m_arity(x.m_arity)
      , m_cnf(x.m_cnf)
    {}

    /// Assignment (inherits the previous refcount).
    Node & operator=(Node const & x)
    {
      this->m_tag = x.m_tag;
      this->m_id = x.m_id;
      this->m_arity = x.m_arity;
      this->m_cnf = x.m_cnf;
      return *this;
    }

    /// Uses the tag to determine the payload type and destroy it.
    void destroy_payload();

    /// Destruction.
    ~Node() { this->destroy_payload(); }

    /// Specialized new that uses the memory pool.
    void * operator new(size_t bytes);

    /// Specialized delete that uses the memory pool.
    void operator delete(void *);

  public:

    // ====== Child access. ======

    /// A range of child pointers; somewhat analogous to pair(Node**,Node**).
    typedef boost::iterator_range<NodePtr *> range_type;

    /// A non-mutable range of children.
    typedef boost::iterator_range<NodePtr const *> const_range_type;

    /// Returns a mutable range containing the children of this node.
    range_type iter();

    /// Returns a constant range containing the children of this node.
    const_range_type iter() const;

    /// Returns the child at position i.  The first child is at index 0.
    NodePtr & operator[](size_t i);

    /// Returns the child at position i.  The first child is at index 0.
    NodePtr const & operator[](size_t i) const;

    /** 
     * @brief Returns the position of the given child.
     *
     * Precondition: child is node[i] (not a copy) for some i.
     */
    size_t position(NodePtr const & child) const;

  private:

    // ====== Smart pointer support. ======

    /// Increment the refcount.  Do not call this directly.
    friend void intrusive_ptr_add_ref(Node * node)
      { ++node->m_refcount; }

    /// Decrement the refcount.  Do not call this directly.
    friend void intrusive_ptr_release(Node * node)
      { if(--node->m_refcount == 0) { delete node; } }

  private:

    // ====== Data members. ======

    uint32 m_refcount;
    TagValue m_tag : 32;
    uint32 m_id;
    uint16 m_arity;
    mutable uint16 m_cnf;
  };

  // Implementation of NodePtr::operator[] (relies on definition of Node).
  inline NodePtr & NodePtr::operator[](size_t i) const { return (**this)[i]; }

  // Implementation of NodePtr::operator= (relies on definition of Node).
  inline NodePtr & NodePtr::operator=(Node & node)
  {
    if(this->base_type::get() != &node) { *this = NodePtr(&node); }
    return *this;
  }

  /**
   * @brief A complete node.  The payload contains tag-specific data.
   */
  template<typename Payload> struct Node_ : Node
  {
    typedef Payload payload_type;
    Payload payload;
  };

  /**
   * @brief The size of a complete node.
   *
   * Constrining every complete node type to have the same size simplifies
   * memory pooling and rewriting.
   */
  size_t const NODE_BYTES = 32;

  // Aliases for the complete node types.

  /// A complete node where the payload is unknown.
  typedef Node_<payloads::Unused<> > AbstractNode;
  BOOST_STATIC_ASSERT(sizeof(AbstractNode) == NODE_BYTES);

  /// A complete node with exactly zero children.
  typedef Node_<payloads::InPlace<0> > InPlaceNode0;
  BOOST_STATIC_ASSERT(sizeof(InPlaceNode0) == NODE_BYTES);

  /// A complete node with exactly one child.
  typedef Node_<payloads::InPlace<1> > InPlaceNode1;
  BOOST_STATIC_ASSERT(sizeof(InPlaceNode1) == NODE_BYTES);

  /// A complete node with exactly two children.
  typedef Node_<payloads::InPlace<2> > InPlaceNode2;
  BOOST_STATIC_ASSERT(sizeof(InPlaceNode2) == NODE_BYTES);

  /// A complete node with more than two children.
  typedef Node_<payloads::ChildList> ChildListNode;
  BOOST_STATIC_ASSERT(sizeof(ChildListNode) == NODE_BYTES);

  /// A complete node representing a choice.
  typedef Node_<payloads::Choice> ChoiceNode;
  BOOST_STATIC_ASSERT(sizeof(ChoiceNode) == NODE_BYTES);

  /**
   * @brief A complete node representing a forward reference.
   *
   * This is simply a node that refers to another, which sometimes comes up
   * during rewriting.
   */
  typedef Node_<payloads::Fwd> FwdNode;
  BOOST_STATIC_ASSERT(sizeof(FwdNode) == NODE_BYTES);

  /// A complete node representing an integer.
  typedef Node_<payloads::Int> IntNode;
  BOOST_STATIC_ASSERT(sizeof(IntNode) == NODE_BYTES);

  /// A complete node representing a floating-point value.
  typedef Node_<payloads::Float> FloatNode;
  BOOST_STATIC_ASSERT(sizeof(FloatNode) == NODE_BYTES);

  /// A complete node representing an integer.
  typedef Node_<payloads::Char> CharNode;
  BOOST_STATIC_ASSERT(sizeof(CharNode) == NODE_BYTES);

  // Documented above.
  inline NodePtr & Node::_fwdtarget()
    { return static_cast<FwdNode *>(this)->payload.dest; }

  /// Tells NodePtr how to skip FWD nodes.
  inline bool skip_fwd_ref(NodePtr & ptr, Node & ref)
  {
    if(ref.tag() == FWD)
    {
      ptr = static_cast<FwdNode &>(ref).payload.dest;
      return true;
    }
    return false;
  }

  namespace meta
  {
    /**
     * @brief Metafunction to get the node type for a given TagValue and arity.
     *
     * A metafunction is a compile-time function that returns a type.  The
     * value -1 for arity indicates either the arity is not applicable, or has
     * a value equal to or larger than SPRITE_INPLACE_BOUND.  Since size_t is
     * an unsigned int, the actual value in that case is a large
     * implementation-defined integer, but that detail is irrelevant to the
     * usage.
     *
     * All constructor types should use the value CTOR to query this function,
     * even though many have tag values strictly greater than CTOR.
     */
    template<sprite::TagValue,size_t Arity=-1> struct NodeOf;
    template<> struct NodeOf<FAIL,-1> : mpl::identity<AbstractNode> {};
    template<> struct NodeOf<OPER,-1> : mpl::identity<ChildListNode> {};
    template<> struct NodeOf<OPER,0> : mpl::identity<InPlaceNode0> {};
    template<> struct NodeOf<OPER,1> : mpl::identity<InPlaceNode1> {};
    template<> struct NodeOf<OPER,2> : mpl::identity<InPlaceNode2> {};
    template<size_t N> struct NodeOf<OPER,N> : NodeOf<OPER,-1> {};
    template<> struct NodeOf<CHOICE,-1> : mpl::identity<ChoiceNode> {};
    template<> struct NodeOf<FWD,-1> : mpl::identity<FwdNode> {};
    template<> struct NodeOf<INT,-1> : mpl::identity<IntNode> {};
    template<> struct NodeOf<FLOAT,-1> : mpl::identity<FloatNode> {};
    template<> struct NodeOf<CHAR,-1> : mpl::identity<CharNode> {};
    template<> struct NodeOf<CTOR,-1> : mpl::identity<ChildListNode> {};
    template<> struct NodeOf<CTOR,0> : mpl::identity<InPlaceNode0> {};
    template<> struct NodeOf<CTOR,1> : mpl::identity<InPlaceNode1> {};
    template<> struct NodeOf<CTOR,2> : mpl::identity<InPlaceNode2> {};
    template<size_t N> struct NodeOf<CTOR,N> : NodeOf<CTOR,-1> {};
  }
}

#include "sprite/detail/node_impl.hpp"

