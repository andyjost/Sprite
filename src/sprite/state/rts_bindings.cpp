#include <cassert>
#include "sprite/state/rts.hpp"
#include "sprite/currylib/prelude.hpp"

namespace sprite
{
  bool RuntimeState::add_binding(Configuration * C, xid_type vid, Node * value)
  {
    if(C->has_binding(vid))
    {
      Node * current = this->get_binding(C, vid);
      // assert(current->info->typedef in rts->builtin_types);
      return current->info == value->info && obj_id(current) == obj_id(value);
    }
    else
    {
      xid_type gid = C->grp_id(vid);
      write(C->bindings)[gid] = value;
      return true;
    }
  }

  void RuntimeState::apply_binding(Configuration * C, xid_type id)
  {
    if(C->has_binding(id))
    {
      Node * genexpr = this->get_generator(C, id);
      Node * binding = this->get_binding(C, id);
      Node * eq = Node::create(&nonstrictEq_Info, genexpr, binding);
      *C->root = Node::create(&seq_Info, eq, C->root);
    }
  }

  void RuntimeState::update_binding(Configuration * C, xid_type vid)
  {
    xid_type gid = C->grp_id(vid);
    if(vid != gid)
      if(C->bindings->count(vid))
        this->add_binding(C, gid, this->get_binding(C, vid));
  }

  struct ValueBindingsMaker
  {
    ValueBindingsMaker(RuntimeState * rts, Node * freevar, InfoTable const * info)
      : rts(rts), freevar(freevar), info(info)
    {}

    RuntimeState *    rts;
    Node *            freevar;
    InfoTable const * info;

    Node * make(Arg * data, size_t size) const
    {
      assert(size);
      if(size==1)
      {
        Node * value = Node::create(this->info, data[0]);
        Node * binding = pair(freevar, value);
        return Node::create(&ValueBinding_Info, value, binding);
      }
      else
      {
        xid_type const cid = rts->istate.xidfactory++;
        Node * left = this->make(data, size/2);
        Node * right = this->make(data+size/2, size/2);
        return choice(cid, left, right);
      }
    }
  };

  Node * RuntimeState::make_value_bindings(Node * freevar, ValueSet const * values)
  {
    ValueBindingsMaker maker(this, freevar, builtin_info(values->kind));
    return maker.make(values->args, values->size);
  }
}
