#include "cyrt/builtins.hpp"
#include "cyrt/checker.hpp"
#include "cyrt/currylib/prelude.hpp"
#include "cyrt/exceptions.hpp"
#include "cyrt/graph/walk.hpp"
#include "cyrt/inspect.hpp"
#include "cyrt/state/configuration.hpp"
#include "cyrt/state/rts.hpp"
#include <unordered_set>
#include <vector>

namespace cyrt
{
  // The pairs of binding cells a constraint step merged (decision D26 of
  // 2026-10-12): the binding dropped and the binding kept, one pair per
  // union of two bound classes.  The step puts their strict equalities
  // above its result (RuntimeState::constrain_equal).
  using MergeGuards = std::vector<std::pair<Node *, Node *>>;

  bool _constrain_equal_rec(
      RuntimeState *, Configuration *, xid_type, xid_type, MergeGuards *
    );
  static bool constrain_equal_impl(
      RuntimeState *, Configuration *, Node *, Node *, ConstraintType
    , bool fresh, MergeGuards * guards
    );

  // Moves the binding of ``old``, a root of a class before a union, to
  // ``root``, the root after it: a class keeps one binding, under its root
  // (issue #128).  When the two roots hold distinct binding cells, the
  // class keeps the binding of ``root`` and the pair goes into ``guards``
  // (decision D26 of 2026-10-12): the two classes were bound to two terms,
  // and the strict equality of the two terms, as a guard above the result
  // of the step, decides the merge.  An equality of the two terms that
  // fails drops the configuration, as the inconsistent merge did before
  // the decision; one that succeeds keeps the value the failure lost (two
  // equal terms not yet evaluated: eqShapeG18 of unit_constraints.py).
  // One cell under both roots is one binding: nothing to guard.  Without a
  // list (a caller outside the constraint step at the root: the fork, the
  // pairing of get_generator) such a merge fails the step, as before the
  // decision.  No program is known to reach it, so the checker counts it
  // (unguarded_merges) and the tests pin the count at zero.  The Python
  // backend has the same step (update_binding in rts_bindings.py).
  static bool merge_binding(
      RuntimeState * rts, Configuration * C, xid_type old, xid_type root
    , MergeGuards * guards
    )
  {
    if(old == root)
      return true;
    auto p = C->bindings->find(old);
    if(p == C->bindings->end())
      return true;
    Node * value = p->second;
    auto q = C->bindings->find(root);
    if(q == C->bindings->end())
      write(C->bindings)[root] = value;
    else if(q->second != value)
    {
      if(!guards)
      {
        if(rts->checker)
          rts->checker->unguarded_merge(C);
        return false;
      }
      guards->emplace_back(value, q->second);
      if(rts->checker)
        rts->checker->merge_guard(C, value, q->second);
    }
    write(C->bindings).erase(old);
    return true;
  }

  // The unchecked form.  Nothing calls it since the merge tests the result
  // (merge_binding); a Boolean signature in state/rts.hpp moves the ABI
  // stamp, so the declaration stays as it is.
  void RuntimeState::update_binding(Configuration * C, xid_type vid)
  {
    merge_binding(this, C, vid, C->grp_id(vid), nullptr);
  }

  // The generator of variable ``vid``, or of ``root``, the root of its
  // class, or nullptr.  A decided class has one at its root (E5).
  static Node * class_generator(
      RuntimeState * rts, xid_type vid, xid_type root
    )
  {
    for(xid_type k: {vid, root})
    {
      Node * x = rts->get_freevar(k);
      if(x && x->info->tag == T_FREE)
        if(Node * gen = has_generator(x))
          return gen;
    }
    return nullptr;
  }

  // Whether the generator instance ``gen`` contains a variable of the class
  // with root ``root``.  ``seen`` holds the roots of the classes whose
  // generators were entered.  The walk allocates no node.
  static bool instance_reaches(
      RuntimeState * rts, Configuration * C, Node * gen, xid_type root
    , std::unordered_set<xid_type> & seen
    )
  {
    std::vector<Node *> stack{gen};
    while(!stack.empty())
    {
      Node * node = stack.back();
      stack.pop_back();
      while(node && node->info->tag == T_FWD)
        node = NodeU{node}.fwd->target;
      if(!node)
        continue;
      tag_type const tag = node->info->tag;
      if(tag == T_CHOICE)
      {
        ChoiceNode * choice = NodeU{node}.choice;
        ChoiceState const lr = rts->read_fp(C, choice->cid);
        if(lr == LEFT)
          stack.push_back(choice->lhs);
        else if(lr == RIGHT)
          stack.push_back(choice->rhs);
      }
      else if(tag == T_FREE)
      {
        xid_type const vid = NodeU{node}.free->vid;
        xid_type const r = C->grp_id(vid);
        if(r == root)
          return true;
        if(!seen.insert(r).second)
          continue;
        if(Node * inner = class_generator(rts, vid, r))
          stack.push_back(inner);
      }
      else if(tag >= T_CTOR)
      {
        InfoTable const * info = node->info;
        Arg const * args = node->successors();
        for(index_type k = 0; k < info->arity; ++k)
          if(info->format[k] == 'p')
            stack.push_back(args[k].node);
      }
    }
    return false;
  }

  // The occurs check at the union of two classes of free variables (the
  // decision of 2026-10-12 on the Fair Scheme).  ``i`` and ``j`` are the
  // two variables of the constraint, just united; ``ri`` and ``rj`` are
  // the roots of their classes before the union.  True when the merged
  // class has a cycle: a member whose generator instance, as created so
  // far, contains another member of the class.  Such a class has no finite
  // instance (x = S x has no term), so the step fails.
  //
  // The test is local to the union.  It walks the generator instance of
  // each side (the generator of the variable or of its old root; a side
  // without one, undecided or fresh, has no instance): the choice nodes
  // along the decided path, the constructor cells, through forward cells,
  // down to the inner free variables.  An inner variable of the merged
  // class is the cycle.  An inner variable of another decided class is
  // bound through that class (Def 2.74), so the walk continues into the
  // generator of that class, once per class.  A choice the configuration
  // has not decided ends the walk there: the variable is not narrowed
  // here, and its generator is no instance of it.  The Python backend has
  // the same test (occurs in rts_constraints.py), and the checker verifies
  // the invariant (D15 (occurs check)).
  static bool occurs(
      RuntimeState * rts, Configuration * C
    , xid_type i, xid_type j, xid_type ri, xid_type rj
    )
  {
    xid_type const root = C->grp_id(i);
    std::unordered_set<xid_type> seen;
    xid_type const sides[2][2] = {{i, ri}, {j, rj}};
    for(auto const & side: sides)
      if(Node * gen = class_generator(rts, side[0], side[1]))
        if(instance_reaches(rts, C, gen, root, seen))
          return true;
    return false;
  }

  // The constraint step at the root of the configuration (procD, rule
  // D.beta): ``cur`` is the root slot, which holds the constraint cell.
  // When the step merged two bound classes (decision D26 of 2026-10-12),
  // the guards of the merges go above the result of the cell: the slot
  // gets a copy of the cell whose result is (b1 =:= b2) &> ... &> result,
  // one guard per pair, the first union outermost, and the scheduler then
  // writes that result in place of the cell as it does without a guard.
  // The slot is private to the configuration (the lift copied the spine
  // of the configuration to bring the constraint there), and the shared
  // cell, which other configurations with other stores hold, is left as
  // it is: the copy is the one lift_constraint makes.  The guard is an
  // ordinary strict equality of the program: its failure drops the
  // configuration, its success yields True in its place, and its own
  // pairings proceed as usual.
  bool RuntimeState::constrain_equal(Configuration * C, Cursor cur)
  {
    ConstrNode * constr = NodeU{cur}.constr;
    MergeGuards guards;
    if(this->checker)
      this->checker->constrain_begin(C);
    if(!constrain_equal_impl(
        this, C, constr->lhs(), constr->rhs(), constraint_type(cur), false
      , &guards
      ))
      return false;
    if(!guards.empty())
    {
      Node * value = constr->value;
      for(auto g = guards.rbegin(); g != guards.rend(); ++g)
        value = Node::create(
            &CyI7Prelude12BindingGuard
          , Node::create(&constrEq_Info, g->first, g->second)
          , value
          );
      *cur = Node::create(constr->info, value, constr->pair);
    }
    return true;
  }

  bool RuntimeState::constrain_equal(
      Configuration * C, Node * x, Node * y, ConstraintType ctype
    )
  {
    return constrain_equal_impl(this, C, x, y, ctype, false, nullptr);
  }

  // ``fresh`` is true for the pairs of the pairing of a generator with a
  // clone made in the same call (see pair_generators).  ``guards`` takes
  // the pairs of bindings the unions merge (merge_binding), or is null.
  static bool constrain_equal_impl(
      RuntimeState * rts, Configuration * C, Node * x, Node * y
    , ConstraintType ctype, bool fresh, MergeGuards * guards
    )
  {
    assert(inspect::is_nondet(x));
    xid_type const i = obj_id(x);
    xid_type const j = inspect::is_nondet(y) ? obj_id(y) : NOXID;
    if(i != j)
    {
      if(ctype == STRICT_CONSTRAINT)
      {
        if(!rts->equate_fp(C, i, j))
          return false;
        // The bindings of a class sit under its root: the roots before the
        // union hand theirs to the root after it.
        xid_type const ri = C->grp_id(i);
        xid_type const rj = C->grp_id(j);
        write(C->strict_constraints).unite(i, j);
        xid_type const r = C->grp_id(i);
        if(!merge_binding(rts, C, ri, r, guards)
            || !merge_binding(rts, C, rj, r, guards))
          return false;
        if(inspect::isa_freevar(x) || inspect::isa_freevar(y))
        {
          // The occurs check: a cycle through the merged class has no
          // finite instance, so the step fails as an inconsistent
          // constraint does.  Two variables of one class (the fork's
          // constraint of a variable with its root; the pairing of two
          // paired generators) identify nothing new, and a fresh leaf of
          // a clone has no instance and lies in no instance outside the
          // class the enclosing union tested: neither needs the test.
          if(ri != rj && !fresh && occurs(rts, C, i, j, ri, rj))
            return false;
          return _constrain_equal_rec(rts, C, i, j, guards);
        }
      }
      else
        return rts->add_binding(C, i, y);
    }
    return true;
  }

  // Pairs the generators of two variables leaf by leaf (Def 2.67 of the
  // note on the Fair Scheme): a sub-variable of one is constrained equal to
  // the sub-variable of the other at the same position.
  // ``fresh`` says that ``v`` is a clone made for this pairing: its leaves
  // are fresh variables (constrain_equal_impl).
  static bool pair_generators(
      RuntimeState * rts, Configuration * C, Node * u, Node * v, bool fresh
    , MergeGuards * guards
    )
  {
    for(Walk p(u), q(v); p && q; ++p, ++q)
    {
      if(inspect::is_nondet(p.cursor()))
        if(!constrain_equal_impl(
            rts, C, p.cursor(), q.cursor(), STRICT_CONSTRAINT, fresh, guards
          ))
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
  // ``guards`` takes the pairs of bindings the unions of the pairing merge
  // (merge_binding); the form without it (get_generator) passes none.
  bool _constrain_equal_rec(
      RuntimeState * rts, Configuration * C, xid_type i, xid_type j
    )
  {
    return _constrain_equal_rec(rts, C, i, j, nullptr);
  }

  bool _constrain_equal_rec(
      RuntimeState * rts, Configuration * C, xid_type i, xid_type j
    , MergeGuards * guards
    )
  {
    // The pairing recurses once per level of the instances, outside the
    // steps where the stack guard unwinds (issue #131).  A pairing deeper
    // than the stack limit ends the evaluation with the error of the
    // guard instead of a segmentation fault.
    if(rts->stack_exhausted())
      throw EvaluationError(
          "stack limit of " + std::to_string(rts->stack_room)
          + " bytes exceeded (flag stack_limit)", ErrorKind::stack
        );
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
      bool const fresh = !has_generator(other);
      if(fresh)
        rts->clone_generator(pivot, other);
      if(!pair_generators(
          rts, C, u, rts->get_generator(C, other), fresh, guards
        ))
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
