#include "cyrt/builtins.hpp"
#include "cyrt/graph/walk.hpp"
#include "cyrt/inspect.hpp"
#include "cyrt/state/configuration.hpp"
#include "cyrt/state/rts.hpp"

namespace cyrt
{
  bool _constrain_equal_rec(RuntimeState *, Configuration *, xid_type, xid_type);

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
        write(C->strict_constraints).unite(i, j);
        this->update_binding(C, i);
        this->update_binding(C, j);
        if(inspect::isa_freevar(x) || inspect::isa_freevar(y))
          return _constrain_equal_rec(this, C, i, j);
      }
      else
        return this->add_binding(C, i, y);
    }
    return true;
  }

  bool _constrain_equal_rec(
      RuntimeState * rts, Configuration * C, xid_type i, xid_type j
    )
  {
    Node * x = rts->get_freevar(i);
    if(!x) return true;
    Node * y = rts->get_freevar(j);
    if(!y) return true;

    if(rts->is_narrowed(C, x) && has_generator(x))
      {}
    else if(rts->is_narrowed(C, y) && has_generator(y))
      std::swap(x, y);
    else
      return true;

    Node * u = rts->get_generator(C, x);
    if(!has_generator(y))
      rts->clone_generator(x, y);
    Node * v = rts->get_generator(C, y);
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
