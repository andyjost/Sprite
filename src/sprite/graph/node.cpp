#include <cassert>
#include "sprite/builtins.hpp"
#include "sprite/exceptions.hpp"
#include "sprite/graph/copy.hpp"
#include "sprite/graph/equality.hpp"
#include "sprite/graph/indexing.hpp"
#include "sprite/graph/memory.hpp"
#include "sprite/graph/node.hpp"
#include "sprite/graph/show.hpp"
#include <sstream>

namespace sprite
{
  Node * Node::create(
      InfoTable const * info, Arg * args, Node * target
    )
  {
    if(!target)
      target = (Node *) node_alloc(info->alloc_size);
    assert(target);

    RawNodeMemory mem{target};
    *mem.info++ = info;
    pack(mem, info->format, args);
    return target;
  }

  Node * Node::rewrite(Node * node, InfoTable const * info, Arg * args)
  {
    assert(node);
    return create(info, args, node);
  }

  std::string Node::str()
  {
    std::stringstream ss;
    this->str(ss);
    return ss.str();
  }

  void Node::str(std::ostream & os)
  {
    Node * self = this;
    show(os, self, SHOW_STR);
  }

  std::string Node::repr()
  {
    std::stringstream ss;
    this->repr(ss);
    return ss.str();
  }

  void Node::repr(std::ostream & os)
  {
    Node * self = this;
    show(os, self, SHOW_REPR);
  }

  Node * Node::copy()
  {
    Node * self = this;
    return copynode(self).node;
  }

  Node * Node::deepcopy()
  {
    Node * self = this;
    return copygraph(self).node;
  }

  Cursor Node::getitem(Node * root, index_type i)
  {
    index_type path[] = {i, NOINDEX};
    return logical_subexpr(root, path);
  }

  Arg * Node::successors()
    { return NodeU{this}.nodeN->data; }

  Cursor const Node::successor(index_type i)
  {
    return Cursor{
        this->successors()[i]
      , this->info->format[i]
      };
  }
}

