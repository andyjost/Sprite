#include <cassert>
#include "sprite/builtins.hpp"
#include "sprite/exceptions.hpp"
#include "sprite/graph/equality.hpp"
#include "sprite/graph/indexing.hpp"
#include "sprite/graph/node.hpp"
#include "sprite/graph/memory.hpp"

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

  // std::string str(Node *);
  // std::string repr(Node *);
  // Node * copy(Node *);
  // Node * deepcopy(Node *);

  Cursor Node::getitem(Node * root, index_type i)
  {
    index_type path[] = {i, NOINDEX};
    return logical_subexpr(root, path);
  }

  Arg * Node::successors()
    { return NodeU{this}.nodeN->data; }

  Cursor Node::successor(index_type i)
  {
    return Cursor{
        this->successors()[i]
      , this->info->format[i]
      };
  }
}

