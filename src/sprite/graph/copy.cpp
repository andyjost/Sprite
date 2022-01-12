#include <cstring>
#include "sprite/builtins.hpp"
#include "sprite/graph/copy.hpp"
#include "sprite/graph/memory.hpp"
#include "sprite/graph/node.hpp"
#include <vector>

namespace sprite
{
  Expr copynode(Cursor expr)
  {
    if(expr.kind != 'p')
      return Expr{*expr.arg, expr.kind};
    auto const alloc_size = expr.info()->alloc_size;
    char * copy = node_alloc(alloc_size);
    std::memcpy(copy, expr.arg->node, alloc_size);
    return Expr{(Node *) copy, expr.kind};
  }

  namespace
  {
    struct SkipNothing
    {
      Node ** operator()(Node *, sid_type) { return nullptr; }
    };

    struct SkipFwd
    {
      Node ** operator()(Node * expr, sid_type)
      {
        return expr->info->tag == T_FWD ? &NodeU{expr}.fwd->target : nullptr;
      }
    };

    struct SkipGrd
    {
      Node ** operator()(Node * expr, sid_type skipgrd)
      {
        if(expr->info->tag == T_SETGRD)
          if(skipgrd == NodeU{expr}.setgrd->sid)
            return &NodeU{expr}.setgrd->value;
        return nullptr;
      }
    };

    struct SkipBoth : SkipGrd
    {
      Node ** operator()(Node * expr, sid_type skipgrd)
      {
        NodeU u{expr};
        switch(expr->info->tag)
        {
          case T_FWD:
            return &u.fwd->target;
          case T_SETGRD:
            if(skipgrd == u.setgrd->sid)
              return &u.setgrd->value;
            break;
        }
        return nullptr;
      }
    };

    template<typename Skipper>
    struct GraphCopier
    {
      GraphCopier(memo_type & memo, sid_type skipgrd=NOSID)
        : expr(), memo(memo), skipgrd(skipgrd), skip()
      {}

      Cursor expr;
      memo_type & memo;
      sid_type skipgrd;
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
            Node ** target = this->skip(this->expr, this->skipgrd);
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

  Expr copygraph(
      Cursor expr, SkipOpt skipfwd, sid_type const * skipgrd, memo_type * memo
    )
  {
    if(!memo)
    {
      memo_type memo_;
      return copygraph(expr, skipfwd, skipgrd, &memo_);
    }
    switch((skipfwd ? 2 : 0) + (skipgrd ? 1 : 0))
    {
      case 2 | 1:
      {
        GraphCopier<SkipBoth> copier(*memo, *skipgrd);
        return Expr{copier(expr), expr.kind};
      }
      case 2 | 0:
      {
        GraphCopier<SkipFwd> copier(*memo);
        return Expr{copier(expr), expr.kind};
      }
      case 0 | 1:
      {
        GraphCopier<SkipGrd> copier(*memo, *skipgrd);
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
