#include "sprite/graph/indexing.hpp"
#include "sprite/graph/node.hpp"
#include "sprite/inspect.hpp"

namespace sprite
{
  Cursor compress_fwd_chain(Cursor cur)
  {
    return cur.kind == 'p'
        ? Cursor(*compress_fwd_chain(&cur->node))
        : cur;
  }

  Node ** compress_fwd_chain(Node ** begin)
  {
    Node * end = *begin;
    while(end->info->tag == T_FWD)
      end = NodeU{end}.fwd->target;
    while(*begin != end)
    {
      NodeU u{*begin};
      Node ** next = &u.fwd->target;
      u.fwd->target = end;
      begin = next;
    }
    return begin;
  }

  Cursor logical_subexpr(
      Node * root
    , index_type const * path
    , bool update_fwd_nodes
    )
  {
    auto && rv = realpath(root, path, update_fwd_nodes);
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

    RealPathIndexer(Node *& root, bool update_fwd_nodes)
      : update_fwd_nodes(update_fwd_nodes)
    {
      this->result.target = root;
      this->skip();
    }

    void skip()
    {
      while(true)
      {
        auto tag = this->result.target->node->info->tag;
        switch(tag)
        {
          case T_FWD:
            if(update_fwd_nodes && !this->result.realpath.empty())
            {
              Cursor end = compress_fwd_chain(this->result.target);
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

  Cursor subexpr(Node * root, index_type i)
    { return root->successor(i); }

  Cursor subexpr(Cursor root, index_type i)
  {
    assert(root.kind == 'p');
    return root->node->successor(i);
  }

  Cursor subexpr(Cursor root, index_type const * path)
  {
    if(path)
      while(*path != NOINDEX)
        root = subexpr(root, *path++);
    return root;
  }
}
