#include "sprite/graph/indexing.hpp"
#include "sprite/graph/node.hpp"
#include "sprite/inspect.hpp"

namespace sprite
{
  Cursor compress_fwd_chain(Cursor cur)
  {
    if(cur.kind == 'p')
      *cur = *compress_fwd_chain(&cur.arg->node);
    return cur;
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
}

namespace
{
  using namespace sprite;

  struct RealPathIndexer
  {
    Variable var;
    Node * parent = nullptr;
    bool update_fwd_nodes;

    RealPathIndexer(Node *& root, bool update_fwd_nodes)
      : update_fwd_nodes(update_fwd_nodes)
    {
      this->var.target = root;
      this->skip();
    }

    Variable & getresult()
    {
      this->var.realpath.push_back(NOINDEX);
      return this->var;
    }

    void skip()
    {
      while(true)
      {
        auto tag = this->var.target->info->tag;
        switch(tag)
        {
          case T_FWD:
            if(update_fwd_nodes && !this->var.realpath.empty())
            {
              Cursor end = compress_fwd_chain(this->var.target);
              *this->parent->successor(this->var.realpath.back()) = end;
              this->var.target = end;
            }
            else
            {
              this->parent = this->var.target;
              this->var.realpath.push_back(0);
              this->var.target = inspect::fwd_target(this->var.target);
            }
            break;
          case T_SETGRD:
            this->var.guards.push_back(inspect::get_set(this->var.target));
            this->parent = this->var.target;
            this->var.realpath.push_back(1);
            this->var.target = inspect::get_setguard_value(this->var.target);
            break;
          default:
            return;
        }
      }
    }

    void advance(index_type i)
    {
      Node * parent_ = this->var.target;
      this->var.target = parent_->successor(i);
      this->parent = parent_;
      this->var.realpath.push_back(i);
      this->skip();
    }
  };
}

namespace sprite
{
  Variable variable(Node * root, index_type pos, bool update_fwd_nodes)
  {
    RealPathIndexer indexer{root, update_fwd_nodes};
    indexer.advance(pos);
    return std::move(indexer.getresult());
  }

  Cursor subexpr(Node * root, index_type i)
    { return root->successor(i); }
}
