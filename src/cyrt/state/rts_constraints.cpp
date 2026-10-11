#include "cyrt/builtins.hpp"
#include "cyrt/graph/walk.hpp"
#include "cyrt/inspect.hpp"
#include "cyrt/state/configuration.hpp"
#include "cyrt/state/rts.hpp"

namespace cyrt
{
  bool _constrain_equal_rec(RuntimeState *, Configuration *, xid_type, xid_type);

  // Moves the binding of ``old``, a root of a class before a union, to
  // ``root``, the root after it: a class keeps one binding, under its root.
  // False when the two roots held different bindings: the two classes were
  // bound to different terms, so the merge is inconsistent and the step
  // fails (the equality has no instance; issue #128).  The Python backend
  // has the same step (update_binding in rts_bindings.py).
  static bool merge_binding(
      RuntimeState * rts, Configuration * C, xid_type old, xid_type root
    )
  {
    if(old == root)
      return true;
    auto p = C->bindings->find(old);
    if(p == C->bindings->end())
      return true;
    Node * value = p->second;
    if(!rts->add_binding(C, root, value))
      return false;
    write(C->bindings).erase(old);
    return true;
  }

  // The unchecked form.  Nothing calls it since the merge tests the result
  // (merge_binding); a Boolean signature in state/rts.hpp moves the ABI
  // stamp, so the declaration stays as it is.
  void RuntimeState::update_binding(Configuration * C, xid_type vid)
  {
    merge_binding(this, C, vid, C->grp_id(vid));
  }

  bool RuntimeState::constrain_equal(Configuration * C, Cursor cur)
  {
    ConstrNode * constr = NodeU{cur}.constr;
    return this->constrain_equal(
        C, constr->lhs(), constr->rhs(), constraint_type(cur)
      );
  }

  bool RuntimeState::constrain_equal(
      Configuration * C, Node * x, Node * y, ConstraintType ctype
    )
  {
    assert(inspect::is_nondet(x));
    xid_type const i = obj_id(x);
    xid_type const j = inspect::is_nondet(y) ? obj_id(y) : NOXID;
    if(i != j)
    {
      if(ctype == STRICT_CONSTRAINT)
      {
        if(!this->equate_fp(C, i, j))
          return false;
        // The bindings of a class sit under its root: the roots before the
        // union hand theirs to the root after it.
        xid_type const ri = C->grp_id(i);
        xid_type const rj = C->grp_id(j);
        write(C->strict_constraints).unite(i, j);
        xid_type const r = C->grp_id(i);
        if(!merge_binding(this, C, ri, r) || !merge_binding(this, C, rj, r))
          return false;
        if(inspect::isa_freevar(x) || inspect::isa_freevar(y))
          return _constrain_equal_rec(this, C, i, j);
      }
      else
        return this->add_binding(C, i, y);
    }
    return true;
  }

  // Pairs the generators of two variables leaf by leaf (Def 2.67 of the
  // note on the Fair Scheme): a sub-variable of one is constrained equal to
  // the sub-variable of the other at the same position.
  static bool pair_generators(
      RuntimeState * rts, Configuration * C, Node * u, Node * v
    )
  {
    for(Walk p(u), q(v); p && q; ++p, ++q)
    {
      if(inspect::is_nondet(p.cursor()))
        if(!rts->constrain_equal(C, p.cursor(), q.cursor(), STRICT_CONSTRAINT))
          return false;
      if(!inspect::isa_freevar(p.cursor()))
        { p.extend(); q.extend(); }
    }
    return true;
  }

  // The generators of a decided class.  ``i`` and ``j`` are two variables
  // of one class (after the union, or a variable and its root).  Nothing
  // happens while the class is undecided.  Otherwise the pivot is a member
  // with a generator: one of the two, the root, or any member of the class
  // (the union by size can make a member without a generator the root: the
  // class {a, b} with b narrowed, united into {c, d, e}, has the root c, and
  // the constraint a =:= c names neither b nor a generator; issue #127).
  // The root and the two variables get a clone of the pivot's generator
  // when they have none, paired with it, so a read at the root finds one
  // (get_generator), and the decided class has a generator at its root.
  bool _constrain_equal_rec(
      RuntimeState * rts, Configuration * C, xid_type i, xid_type j
    )
  {
    Node * x = rts->get_freevar(i);
    if(!x) return true;
    Node * y = rts->get_freevar(j);
    if(!y) return true;
    if(!rts->is_narrowed(C, x))
      return true;

    xid_type const gid = C->grp_id(i);
    Node * root = rts->get_freevar(gid);
    Node * pivot = has_generator(x) ? x
                 : has_generator(y) ? y
                 : root && has_generator(root) ? root
                 : nullptr;
    if(!pivot)
      for(xid_type k: C->strict_constraints->united)
      {
        Node * z = C->grp_id(k) == gid ? rts->get_freevar(k) : nullptr;
        if(z && has_generator(z))
          { pivot = z; break; }
      }
    if(!pivot)
      return true;

    Node * u = rts->get_generator(C, pivot);
    Node * const others[3] = {root, x, y};
    for(size_t k = 0; k < 3; ++k)
    {
      Node * other = others[k];
      if(!other || other == pivot)
        continue;
      bool seen = false;
      for(size_t m = 0; m < k; ++m)
        seen = seen || others[m] == other;
      if(seen)
        continue;
      if(!has_generator(other))
        rts->clone_generator(pivot, other);
      if(!pair_generators(rts, C, u, rts->get_generator(C, other)))
        return false;
    }
    return true;
  }

  Node * RuntimeState::lift_constraint(Configuration * C, Node * source, Node * target)
  {
    assert(source != target);
    assert(target->info->tag == T_CONSTR);
    ConstrNode * constr = NodeU{target}.constr;
    Node * value = C->scan.copy_spine(source, constr->value);
    return Node::create(constr->info, value, constr->pair);
  }

  Node * RuntimeState::lift_constraint(Configuration * C, Variable * inductive)
  {
    assert(inductive->target->info->tag == T_CONSTR);
    Node * source = C->cursor();
    C->scan.push(inductive);
    auto result = lift_constraint(C, source, inductive->target);
    C->scan.pop();
    return result;
  }
}
