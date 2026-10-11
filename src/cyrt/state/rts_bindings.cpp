#include <cassert>
#include "cyrt/builtins.hpp"
#include "cyrt/state/rts.hpp"
#include "cyrt/currylib/prelude.hpp"
#include <utility>
#include <vector>

namespace cyrt
{
  // The number of cells the comparison of two bindings reads.
  static constexpr size_t SAME_BINDING_BUDGET = 1024;

  static Node * skip_fwd(Node * node)
  {
    while(node && node->info->tag == T_FWD)
      node = NodeU{node}.fwd->target;
    return node;
  }

  // Two bindings of one class are the same term when they are one cell, or
  // the same constructor or literal over the same successors through
  // forward cells, read within the budget.  Two distinct cells that are not
  // constructor terms (operations, choices, variables, failures) count as
  // different, and so does a pair beyond the budget: the merge of two
  // classes bound to different terms fails the step (issue #128), where
  // the equality of two unevaluated terms is not decided here (Remark 2.70
  // of the note on the Fair Scheme leaves the merge of two bound classes
  // open: the rule is the owner's).  The Python backend has the same
  // comparison (_same_binding in rts_bindings.py).
  static bool same_binding(Node * a, Node * b)
  {
    std::vector<std::pair<Node *, Node *>> stack{{a, b}};
    size_t cells = 0;
    while(!stack.empty())
    {
      Node * p = skip_fwd(stack.back().first);
      Node * q = skip_fwd(stack.back().second);
      stack.pop_back();
      if(p == q)
        continue;
      if(!p || !q || p->info != q->info || p->info->tag < T_CTOR)
        return false;
      if(++cells > SAME_BINDING_BUDGET)
        return false;
      InfoTable const * info = p->info;
      Arg const * pa = p->successors();
      Arg const * qa = q->successors();
      for(index_type i = 0; i < info->arity; ++i)
        switch(info->format[i])
        {
          case 'p': stack.emplace_back(pa[i].node, qa[i].node); break;
          case 'i': if(pa[i].ub_int != qa[i].ub_int) return false; break;
          case 'f': if(pa[i].ub_float != qa[i].ub_float) return false; break;
          case 'c': if(pa[i].ub_char != qa[i].ub_char) return false; break;
          // An unboxed pointer: the head of a partial application, or the
          // set of a set guard (graph/equality.cpp compares it the same way).
          case 'x': if(pa[i].blob != qa[i].blob) return false; break;
          default : return false;
        }
    }
    return true;
  }

  // Binds the class of ``vid`` to ``value``.  The bindings sit under the
  // root of the class (the merge keeps them there, rts_constraints.cpp).
  // False when the class holds a different binding.
  bool RuntimeState::add_binding(Configuration * C, xid_type vid, Node * value)
  {
    xid_type gid = C->grp_id(vid);
    auto p = C->bindings->find(gid);
    if(p != C->bindings->end())
      return same_binding(p->second, value);
    write(C->bindings)[gid] = value;
    return true;
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
      *C->root = Node::create(&CyI7Prelude12BindingGuard, eq, C->root);
      write(C->bindings).erase(id);
    }
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
