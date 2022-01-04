#include "sprite/graph/indexing.hpp"
#include "sprite/graph/node.hpp"
#include "sprite/inspect.hpp"

namespace sprite
{
  Node * compress_fwd_chain(Node * end)
  {
    Node * start = end;
    while(end->info->tag == T_FWD)
    {
      NodeU u{end};
      end = u.fwd->target;
    }
    while(start != end)
    {
      NodeU u{start};
      Node * next = u.fwd->target;
      u.fwd->target = end;
      start = next;
    }
    return end;
  }

  Arg logical_subexpr(
      Node * root
    , index_type const * path
    , char * kind
    , bool update_fwd_nodes
    )
  {
    auto && rv = realpath(root, path, update_fwd_nodes);
    if(kind)
      *kind = rv.kind;
    return rv.target;
  }
}

namespace
{
  using namespace sprite;

  struct RealPathIndexer
  {
    RealpathResult result;
    Node * parent = nullptr;
    bool update_fwd_nodes;

    RealPathIndexer(Node * root, bool update_fwd_nodes)
      : update_fwd_nodes(update_fwd_nodes)
    {
      this->result.target = root;
      this->skip();
    }

    void skip()
    {
      while(true)
      {
        auto tag = this->result.target->info->tag;
        switch(tag)
        {
          case T_FWD:
            if(update_fwd_nodes && !this->result.realpath.empty())
            {
              Node * end = compress_fwd_chain(this->result.target);
              this->parent->successor(this->result.realpath.back()) = end;
              this->result.target = end;
            }
            else
            {
              this->parent = this->result.target;
              this->result.realpath.push_back(0);
              this->result.target = inspect::fwd_target(this->result.target);
            }
            break;
          case T_SETGRD:
            this->result.guards.push_back(inspect::get_set_id(this->result.target));
            this->parent = this->result.target;
            this->result.realpath.push_back(1);
            this->result.target = inspect::get_setguard_value(this->result.target);
            break;
          default:
            return;
        }
      }
    }

    void advance(index_type i)
    {
      Node * parent_ = this->result.target;
      this->result.target = this->parent->successor(i);
      this->parent = parent_;
      this->result.realpath.push_back(i);
      this->skip();
    }

    void advance(index_type const * path)
    {
      while(*path != NOINDEX)
        advance(*path++);
    }
  };
}

namespace sprite
{
  RealpathResult realpath(Node * root, index_type const * path, bool update_fwd_nodes)
  {
    RealPathIndexer indexer{root, update_fwd_nodes};
    indexer.advance(path);
    return indexer.result;
  }

  Arg subexpr(Node * root, index_type i, char * kind_out)
    { return root->successor(i, kind_out); }

  Arg subexpr(Node * root, index_type const * path, char * kind_out)
  {
    Node * target = root;
    if(path)
      while(*path != NOINDEX)
        target = subexpr(target, *path++, kind_out);
    return target;
  }
}
