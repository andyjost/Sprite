/**
 * @file
 * @brief Implements Node::create through preprocessor magic.
 */

// No include guards by design.

#ifndef BOOST_PP_IS_ITERATING
  #error "Do not include this file directly"
#else
  // N is the number of parameters.  The create function is overloaded for
  // various numbers of parameters (which are all forwarded to rewrite).
  #define N BOOST_PP_ITERATION()
  
  // Documented in struct Node.
  template<TagValue Value BOOST_PP_ENUM_TRAILING_PARAMS(N,typename T)>
  inline NodePtr Node::create(
      BOOST_PP_ENUM_BINARY_PARAMS(N,T,const & t)
    )
  {
    // Initializes the refcount, leaves the tag and other members
    // uninitialized.
    Node * p = new AbstractNode();
  
    // TODO -- if rewrite were made nothrow, then this try block could be
    // eliminated.

    // Initializes the tag, payload and other members.  The tag is used to
    // destroy the payload, so it must be initialized before p can be deleted
    // with a normal call to delete.
    try
      { rewrite<Value>()(*p BOOST_PP_ENUM_TRAILING_PARAMS(N,t)); }
    catch(...)
    {
      // Node::delete, i.e., not the same as "delete p".  This does not call
      // ~Node, so the Node constructor must not have claimed resources.
      operator delete(p);
      throw;
    }
    NodePtr q = NodePtr(p);
    return q;
  }

  #undef N
#endif
