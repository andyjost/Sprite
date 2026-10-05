#pragma once
#include "cyrt/builtins.hpp"
#include "cyrt/graph/indexing.hpp"
#include "cyrt/graph/node.hpp"

// The indexer of Variable.  A step reads every argument through it, so it is
// inline: the common case, a plain successor, is a few loads and one store
// into the inline path.  Only a forward chain of more than one link leaves
// the step function (compress_fwd_chain).

namespace cyrt
{
  // Steps over forward nodes and set guards at the target.  A forward node
  // found in a slot is shortened: the slot gets the end of the chain and the
  // path does not grow.  The root of an indexing operation has no slot, so a
  // forward node there goes on the path, as a set guard does everywhere.
  inline void Variable::skip(Node *& parent, bool update_fwd_nodes)
  {
    Cursor & cur = this->target;
    while(true)
    {
      // Stop at an unboxed value or at a null successor.  A null successor
      // exists between the creation of a recursive let and its patch
      // (INodeAssign).
      if(cur.kind != 'p' || !cur.arg->node)
        return;
      Node * node = cur.arg->node;
      switch(node->info->tag)
      {
        case T_FWD:
          if(update_fwd_nodes && parent)
          {
            // The slot is successor realpath.back() of the parent.
            Node * end = NodeU{node}.fwd->target;
            if(end->info->tag == T_FWD)
              compress_fwd_chain(cur);
            else
              *cur = end;
          }
          else
          {
            parent = node;
            this->realpath.push_back(0);
            cur = Cursor(NodeU{node}.fwd->target);
          }
          break;
        case T_SETGRD:
          this->guards.push_back(NodeU{node}.setgrd->set);
          parent = node;
          this->realpath.push_back(1);
          cur = Cursor(NodeU{node}.setgrd->value);
          break;
        default:
          return;
      }
    }
  }

  inline void Variable::index(Node * root, index_type pos, bool update_fwd_nodes)
  {
    Node * parent = nullptr;
    this->target = Cursor(root); // the local, until the first step
    this->skip(parent, update_fwd_nodes);
    Node * node = this->target;
    this->target = node->successor(pos);
    parent = node;
    this->realpath.push_back(pos);
    this->skip(parent, update_fwd_nodes);
  }

  inline Variable::Variable(Node * root, index_type pos, bool update_fwd_nodes)
  {
    this->index(root, pos, update_fwd_nodes);
  }

  // The successor of a variable.  The realpath runs from the root of the
  // step, so the path of this variable comes first: Scan::push walks it from
  // the root when the successor is head-normalized.  The guards crossed on
  // the way to the successor come before those of this variable.
  inline Variable Variable::operator[](index_type pos) const
  {
    Variable tmp;
    tmp.realpath = this->realpath;
    tmp.index(this->target, pos, true);
    tmp.guards.append(this->guards.begin(), this->guards.end());
    return tmp;
  }

  inline Variable Cursor::operator[](index_type pos) const
    { return Variable(*this, pos); }

  // A successor of a variable that a step only passes on (a pattern variable
  // of a case).  When this variable crossed no set guard and its target is a
  // constructor (the case head-normalized it), the successor slot holds the
  // whole value, and it is read as Node::successor_node reads a slot of the
  // redex.  Otherwise the indexer runs as before: it crosses a forward node
  // or a guard at the target, and rvalue wraps the successor in the guards
  // crossed.  The generated code cannot tell the two cases apart, so the
  // check is made here, at run time.
  inline Node * Variable::successor_node(index_type pos) const
  {
    if(this->guards.empty())
    {
      assert(this->target.kind == 'p');
      Node * node = *this->target;
      if(node && node->info->tag >= T_CTOR)
        return node->successor_node(pos);
    }
    return (*this)[pos].rvalue();
  }
}
