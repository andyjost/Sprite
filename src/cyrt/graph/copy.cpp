#include <cstring>
#include "cyrt/builtins.hpp"
#include "cyrt/graph/copy.hpp"
#include "cyrt/graph/memory.hpp"
#include "cyrt/graph/node.hpp"
#include <vector>

namespace cyrt
{
  Expr copy_node(Cursor expr)
  {
    if(expr.kind != 'p')
      return expr;
    return Expr{copy_node(*expr), 'p'};
  }

  Node * copy_node(Node * node)
  {
    auto const alloc_size = node->info->alloc_size;
    Node * copy;
    do
    {
      copy = node_reserve(alloc_size);
      std::memcpy(copy, node, alloc_size);
    } while(!node_commit(copy, alloc_size));
    return copy;
  }

  namespace
  {
    struct SkipNothing
    {
      Node ** operator()(Node *, Set *) { return nullptr; }
    };

    struct SkipFwd
    {
      Node ** operator()(Node * expr, Set *)
      {
        return expr->info->tag == T_FWD ? &NodeU{expr}.fwd->target : nullptr;
      }
    };

    struct SkipGrd
    {
      Node ** operator()(Node * expr, Set * skipgrd)
      {
        if(expr->info->tag == T_SETGRD)
          if(skipgrd == NodeU{expr}.setgrd->set)
            return &NodeU{expr}.setgrd->value;
        return nullptr;
      }
    };

    struct SkipBoth : SkipGrd
    {
      Node ** operator()(Node * expr, Set * skipgrd)
      {
        NodeU u{expr};
        switch(expr->info->tag)
        {
          case T_FWD:
            return &u.fwd->target;
          case T_SETGRD:
            if(skipgrd == u.setgrd->set)
              return &u.setgrd->value;
            break;
        }
        return nullptr;
      }
    };

    template<typename Skipper>
    struct GraphCopier
    {
      GraphCopier(memo_type & memo, Set * skipgrd=nullptr)
        : memo(memo), skipgrd(skipgrd), skip()
      {}

      memo_type & memo;
      Set *       skipgrd;
      Skipper     skip;
      // The number of free variables copied.
      size_t      freevars = 0;

      // A node whose copy is under construction.  ``copy`` starts as a
      // shallow copy of ``node``.  The copies of the successors replace the
      // originals one by one.  ``next`` is the index of the successor copied
      // next.
      struct Frame
      {
        Node *     node;
        Node *     copy;
        index_type next;
      };

      // Copies the graph at ``expr``.  The traversal keeps its own stack, so
      // a deep graph such as a long list cannot overflow the C stack.  The
      // copy of a node is allocated, and recorded in ``memo``, before its
      // successors are copied.  So a node reached by several paths is copied
      // once, the copy keeps the sharing, and a cycle in the graph becomes a
      // cycle in the copy.
      Arg operator()(Cursor expr)
      {
        std::vector<Frame> stack;
        Cursor cur = expr;
        Arg value;
        while(true)
        {
          // Descend from ``cur`` until a value is at hand.
          while(true)
          {
            if(cur.kind != 'p' || !cur)
            {
              value = cur ? *cur.arg : Arg();
              break;
            }
            auto p = this->memo.find(cur.id());
            if(p != this->memo.end())
            {
              value = p->second;
              break;
            }
            if(Node ** target = this->skip(cur, this->skipgrd))
            {
              cur = Cursor(*target);
              continue;
            }
            Node * node = cur;
            index_type const arity = node->info->arity;
            Node * copy = Node::create(
                node->info, arity ? node->successors() : nullptr
              );
            if(node->info->tag == T_FREE)
              ++this->freevars;
            this->memo[node] = copy;
            if(arity == 0)
            {
              value = copy;
              break;
            }
            stack.push_back(Frame{node, copy, 0});
            cur = node->successor(0);
          }
          // Deliver ``value`` to the innermost frame.  Finished frames
          // produce the value for their parent.
          while(true)
          {
            if(stack.empty())
              return value;
            Frame & frame = stack.back();
            frame.copy->successors()[frame.next] = value;
            if(++frame.next < frame.node->info->arity)
            {
              cur = frame.node->successor(frame.next);
              break;
            }
            value = frame.copy;
            stack.pop_back();
          }
        }
      }
    };
  }

  namespace
  {
    template<typename Skipper>
    Expr copy_with(
        Cursor expr, memo_type & memo, Set * skipgrd, size_t * freevars
      )
    {
      GraphCopier<Skipper> copier(memo, skipgrd);
      Expr value{copier(expr), expr.kind};
      if(freevars)
        *freevars += copier.freevars;
      return value;
    }
  }

  Expr copy_graph(
      Cursor expr, SkipOpt skipfwd, Set * skipgrd, memo_type * memo
    , size_t * freevars
    )
  {
    if(!memo)
    {
      memo_type memo_;
      return copy_graph(expr, skipfwd, skipgrd, &memo_, freevars);
    }
    switch((skipfwd ? 2 : 0) + (skipgrd ? 1 : 0))
    {
      case 2 | 1: return copy_with<SkipBoth>(expr, *memo, skipgrd, freevars);
      case 2 | 0: return copy_with<SkipFwd>(expr, *memo, nullptr, freevars);
      case 0 | 1: return copy_with<SkipGrd>(expr, *memo, skipgrd, freevars);
      case 0 | 0: return copy_with<SkipNothing>(expr, *memo, nullptr, freevars);
      default: __builtin_unreachable();
    }
  }
}
