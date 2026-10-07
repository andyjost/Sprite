#include <cassert>
#include "cyrt/state/rts.hpp"
#include "cyrt/currylib/prelude.hpp"

namespace cyrt
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

  // Applies the binding of variable ``id`` to configuration C, whose root is
  // an alternative of the generator of the variable (fork): the root e
  // becomes (generator =:<= binding) &> e, so the side of the generator
  // agrees with the binding.  The binding is consumed.  The constraint
  // carries it into the variables of the generator, and a configuration
  // that forks on the generator again applies nothing.  Applied at every
  // fork, the constraint pull-tabbed the same generator to the root, the
  // fork applied the binding once more, and so on without end (issue #97).
  // The Python backend has the same step (rts_bindings.apply_binding).
  void RuntimeState::apply_binding(Configuration * C, xid_type id)
  {
    if(C->has_binding(id))
    {
      Node * genexpr = this->get_generator(C, id);
      Node * binding = C->bindings->at(id);
      Node * eq = Node::create(&nonstrictEq_Info, genexpr, binding);
      *C->root = Node::create(&seq_Info, eq, C->root);
      write(C->bindings).erase(id);
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
        // The halves together hold every value: a split of size/2 and size/2
        // dropped one value of an odd-sized set.
        xid_type const cid = rts->istate.xidfactory++;
        size_t const half = size / 2;
        Node * left = this->make(data, half);
        Node * right = this->make(data + half, size - half);
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
