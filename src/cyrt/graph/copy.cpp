#include <cstring>
#include "cyrt/builtins.hpp"
#include "cyrt/currylib/setfunctions.hpp"
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

  // A free variable is shared, not copied: one node stands for one id, the
  // one in the free-variable table (see state/rts.hpp).  A copy with the
  // same id would narrow apart from the variable, and a value handed to
  // Python would hold a node the runtime cannot find by its id.  So is a
  // pinned constructor ([], (), True, False, failed): its one node is the
  // static object.  The collector tells that object by the flag of its info
  // table and neither marks nor sweeps it, so a heap copy with the same
  // table would be freed under its holder (see gc/wdgc.cpp).
  static inline bool is_shared(Node * node)
  {
    return node->info->tag == T_FREE || is_pinned(*node->info);
  }

  // A copy of a generator node owns a reference of its own (see
  // biGeneratorNode in builtins.hpp).
  static inline void acquire_resource(Node * copy)
  {
    if(copy->info == &_biGenerator_Info)
      generator_acquire(NodeU{copy}.generator->data);
  }

  Node * copy_node(Node * node)
  {
    if(is_shared(node))
      return node;
    auto const alloc_size = node->info->alloc_size;
    Node * copy;
    do
    {
      copy = node_reserve(alloc_size);
      std::memcpy(copy, node, alloc_size);
    } while(!node_commit(copy, alloc_size));
    acquire_resource(copy);
    // The copy is a new node of the heap: the collector must know a
    // generator node to release its iterator, and a SetEval node to free
    // its queue (the graph copier below makes its copies through
    // Node::create, which registers them).
    if(copy->info == &_biGenerator_Info)
      gc_register_generator(copy);
    else if(copy->info == &SetEval_Info)
      gc_register_seteval(copy);
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
      // The memo is keyed by the addresses of the nodes: no node may move
      // while the copier lives.
      GcClamp     gc_clamp;

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
            if(is_shared(node))
            {
              value = node;
              break;
            }
            index_type const arity = node->info->arity;
            Node * copy = Node::create(
                node->info, arity ? node->successors() : nullptr
              );
            this->memo[node] = copy;
            acquire_resource(copy);
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

  Expr copy_graph(
      Cursor expr, SkipOpt skipfwd, Set * skipgrd, memo_type * memo
    )
  {
    if(!memo)
    {
      memo_type memo_;
      return copy_graph(expr, skipfwd, skipgrd, &memo_);
    }
    switch((skipfwd ? 2 : 0) + (skipgrd ? 1 : 0))
    {
      case 2 | 1:
      {
        GraphCopier<SkipBoth> copier(*memo, skipgrd);
        return Expr{copier(expr), expr.kind};
      }
      case 2 | 0:
      {
        GraphCopier<SkipFwd> copier(*memo);
        return Expr{copier(expr), expr.kind};
      }
      case 0 | 1:
      {
        GraphCopier<SkipGrd> copier(*memo, skipgrd);
        return Expr{copier(expr), expr.kind};
      }
      case 0 | 0:
      {
        GraphCopier<SkipNothing> copier(*memo);
        return Expr{copier(expr), expr.kind};
      }
      default: __builtin_unreachable();
    }
  }
}
