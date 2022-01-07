#include <cstring>
#include "sprite/builtins.hpp"
#include "sprite/graph/copy.hpp"
#include "sprite/graph/memory.hpp"
#include <vector>

namespace sprite
{
  Arg copynode(Cursor expr)
  {
    if(expr.kind != 'p')
      return *expr.arg;
    auto const alloc_size = expr.info()->alloc_size;
    char * copy = node_alloc(alloc_size);
    std::memcpy(copy, expr.arg->node, alloc_size);
    return (Node *) copy;
  }

  namespace
  {
    struct SkipNothing
    {
      Node ** operator()(Node *, sid_set_type *) { return nullptr; }
    };

    struct SkipFwd
    {
      Node ** operator()(Node * expr, sid_set_type *)
      {
        return expr->info->tag == T_FWD ? &NodeU{expr}.fwd->target : nullptr;
      }
    };

    struct SkipGrd
    {
      Node ** operator()(Node * expr, sid_set_type * sid_set)
      {
        if(expr->info->tag == T_SETGRD)
          if(sid_set->count(NodeU{expr}.setgrd->sid))
            return &NodeU{expr}.setgrd->value;
        return nullptr;
      }
    };

    struct SkipBoth : SkipGrd
    {
      Node ** operator()(Node * expr, sid_set_type * sid_set)
      {
        NodeU u{expr};
        switch(expr->info->tag)
        {
          case T_FWD:
            return &u.fwd->target;
          case T_SETGRD:
            if(sid_set->count(u.setgrd->sid))
              return &u.setgrd->value;
            break;
        }
        return nullptr;
      }
    };

    template<typename Skipper>
    struct GraphCopier
    {
      GraphCopier(memo_type & memo, sid_set_type * sid_set = nullptr)
        : expr(), memo(memo), sid_set(sid_set), skip()
      {}

      Cursor expr;
      memo_type & memo;
      sid_set_type * sid_set;
      Skipper skip;

      Arg operator()(Cursor expr)
      {
        this->expr = expr;
        return this->deepcopy();
      }

      Arg deepcopy()
      {
        if(this->expr.kind != 'p' || !this->expr->node)
          return *this->expr.arg;
        else
        {
          auto p = this->memo.find(expr.id());
          if(p != this->memo.end())
            return p->second;
          else
          {
            Node ** target = this->skip(this->expr, this->sid_set);
            if(target)
              return (*this)(*target);
            else
            {
              index_type const arity = this->expr.info()->arity;
              std::vector<Arg> args;
              args.reserve(arity);
              Node * parent = this->expr->node;
              for(auto i=0; i<arity; ++i)
                args.push_back((*this)(parent->successor(i)));
              return Node::create(parent->info, args.data());
            }
          }
        }
      }
    };
  }

  Arg copygraph(
      Cursor expr
    , memo_type * memo
    , bool skipfwd
    , sid_set_type * sid_set
    )
  {
    if(!memo)
    {
      memo_type memo_;
      return copygraph(expr, &memo_, skipfwd, sid_set);
    }
    switch((skipfwd ? 2 : 0) + (sid_set ? 1 : 0))
    {
      case 2 | 1:
      {
        GraphCopier<SkipBoth> copier(*memo, sid_set);
        return copier(expr);
      }
      case 2 | 0:
      {
        GraphCopier<SkipFwd> copier(*memo);
        return copier(expr);
      }
      case 0 | 1:
      {
        GraphCopier<SkipGrd> copier(*memo, sid_set);
        return copier(expr);
      }
      case 0 | 0:
      {
        GraphCopier<SkipNothing> copier(*memo);
        return copier(expr);
      }
      default: __builtin_unreachable();
    }
  }
}
