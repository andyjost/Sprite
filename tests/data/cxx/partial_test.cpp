// Checks the flat partial applications of the runtime: the info-table
// family (partapplic_info, partials_info), Node::create_partial,
// Node::extend_partial, Node::from_partial, Node::rewrite_from_partial,
// partial_node, the copier, the equality, and the collector on them (see
// PartApplicNode in cyrt/builtins.hpp).  unit_cxx_partial.py compiles this
// program against the installed runtime and runs it.  It prints the first
// failed check and exits with status 1; it prints "ok" and exits with
// status 0 when every check passes.
#include "cyrt/cyrt.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>

using namespace cyrt;

#define CHECK(cond) \
    do { if(!(cond)) { std::printf("failed: %s (line %d)\n", #cond, __LINE__); std::exit(1); } } while(0)

static PartApplicNode * partial(Node * node)
{
  CHECK(is_partial(*node->info));
  return NodeU{node}.partapplic;
}

static unboxed_int_type int_value(Node * node)
{
  CHECK(node->info == &Int_Info);
  return NodeU{node}.int_->value;
}

// A heap node that only this program holds.
static Node * heap_int(unboxed_int_type value)
{
  Node * node = int_(value);
  CHECK(!gc_is_literal(node));
  return node;
}

int main()
{
  // The family: one table per number of arguments, made on demand, the
  // same on a second call, inside and outside the cached range.
  CHECK(partapplic_info(0) == &PartApplic_Info);
  CHECK(PartApplic_Info.arity == 2);
  CHECK(std::strcmp(PartApplic_Info.format, "ix") == 0);
  CHECK(PartApplic_Info.alloc_size == sizeof(PartApplicNode));
  CHECK(sizeof(PartApplicNode) == sizeof(Head) + 2 * sizeof(Arg));
  for(index_type n: {1, 2, 3, 31, 32, 33, 40, 100})
  {
    InfoTable const * info = partapplic_info(n);
    CHECK(info == partapplic_info(n));
    CHECK(info->arity == n + 2);
    CHECK(info->alloc_size == sizeof(Head) + (n + 2) * sizeof(Arg));
    CHECK(std::strlen(info->format) == n + 2u);
    CHECK(info->format[0] == 'i' && info->format[1] == 'x');
    for(index_type i=2; i<n+2; ++i)
      CHECK(info->format[i] == 'p');
    CHECK(is_partial(*info));
    CHECK(info->tag == T_CTOR);
    CHECK(info->type == &PartApplic_Type);
    CHECK(std::strcmp(info->name, "_PartApplic") == 0);
    CHECK(info != partials_info(n));
  }
  CHECK(partials_info(0) == &PartialS_Info);
  CHECK(partials_info(2)->type == &PartialS_Type);
  CHECK(partials_info(2)->arity == 4);
  CHECK(std::strcmp(partials_info(2)->name, "PartialS") == 0);

  // create_partial: the missing count, the head, the arguments in order.
  Node * a = heap_int(5000);
  Node * b = heap_int(5001);
  Node * c = heap_int(5002);
  Node * d = heap_int(5003);
  {
    Node * p = Node::create_partial(&set3_Info);
    CHECK(p->info == &PartApplic_Info);
    CHECK(partial(p)->missing == 4);
    CHECK(partial(p)->head_info == &set3_Info);
    CHECK(partial(p)->nargs() == 0);
    CHECK(!partial(p)->complete());
    CHECK(!partial(p)->is_encapsulated());
  }
  {
    Node * p = Node::create_partial(&set3_Info, a, b);
    CHECK(p->info == partapplic_info(2));
    CHECK(partial(p)->missing == 2);
    CHECK(partial(p)->nargs() == 2);
    CHECK(partial(p)->args()[0] == a);
    CHECK(partial(p)->args()[1] == b);
    CHECK(p->successors()[2].node == a);
    CHECK(p->successor(2).kind == 'p');
    CHECK(p->successor(0).kind == 'i');
    CHECK(p->successor(1).kind == 'x');
  }
  {
    // The array form, as the bindings call it.  The pointer and the count
    // must have the exact types, or the variadic template is chosen.
    Arg const args[] = {a, b, c};
    Node * p = Node::create_partial(&set3_Info, (Arg const *) args, size_t(3));
    CHECK(p->info == partapplic_info(3));
    CHECK(partial(p)->missing == 1);
    CHECK(partial(p)->args()[2] == c);
    CHECK(!partial(p)->complete());
    CHECK(partial(p)->complete(d));
  }

  // extend_partial: one more argument, in the same family.
  {
    Node * p = Node::create_partial(&set3_Info, a);
    Node * q = Node::extend_partial(partial(p), b);
    CHECK(q != p);
    CHECK(q->info == partapplic_info(2));
    CHECK(partial(q)->missing == 2);
    CHECK(partial(q)->head_info == &set3_Info);
    CHECK(partial(q)->args()[0] == a);
    CHECK(partial(q)->args()[1] == b);
    CHECK(partial(p)->nargs() == 1); // the original is unchanged
    CHECK(!gc_is_literal(q));
    Node * s = Node::create(partials_info(1), Arg(3), Arg(&set3_Info), a);
    Node * t = Node::extend_partial(partial(s), b);
    CHECK(t->info == partials_info(2));
    CHECK(t->info->type == &PartialS_Type);
    CHECK(partial(t)->missing == 2);
    CHECK(partial(t)->args()[1] == b);
  }

  // from_partial: the function node, arguments first, the final one last.
  {
    Node * p = Node::create_partial(&set3_Info, a, b, c);
    Node * f = Node::from_partial(partial(p), d);
    CHECK(f->info == &set3_Info);
    CHECK(f->successors()[0].node == a);
    CHECK(f->successors()[1].node == b);
    CHECK(f->successors()[2].node == c);
    CHECK(f->successors()[3].node == d);
  }
  {
    // A complete partial application (as the set functions keep one).
    Node * q = Node::create(
        partials_info(4), Arg(0), Arg(&set3_Info), a, b, c, d
      );
    CHECK(partial(q)->complete());
    Node * f = partial(q)->materialize();
    CHECK(f->info == &set3_Info);
    CHECK(f->successors()[3].node == d);
    // An encapsulated expression: its one argument.
    Node * e = Node::create(
        partials_info(1), Arg(ENCAPSULATED_EXPR), Arg((InfoTable const *) nullptr), a
      );
    CHECK(partial(e)->is_encapsulated());
    CHECK(partial(e)->complete());
    CHECK(partial(e)->materialize() == a);
  }

  // rewrite_from_partial: a Cons written into the block of an apply node.
  {
    Node * p = Node::create_partial(&Cons_Info, a);
    Node * redex = Node::create(&apply_Info, p, nil());
    CHECK(Cons_Info.alloc_size <= redex->info->alloc_size);
    tag_type tag = redex->rewrite_from_partial(partial(p), nil());
    CHECK(tag == T_CONS);
    CHECK(redex->info == &Cons_Info);
    CHECK(NodeU{redex}.cons->head == a);
    CHECK(NodeU{redex}.cons->tail == Nil);
  }

  // The copier and the equality.
  {
    Node * p = Node::create_partial(&set3_Info, a, cons(b, nil()));
    Node * q = Node::create_partial(&set3_Info, a, cons(b, nil()));
    Node * r = Node::create_partial(&set3_Info, a, cons(c, nil()));
    Node * s = Node::create_partial(&set3_Info, a);
    Node * t = Node::create_partial(&set2_Info, a, cons(b, nil()));
    CHECK(*p == *q);
    CHECK(*p != *r);
    CHECK(*p != *s);
    CHECK(*p != *t);
    Node * shallow = p->copy();
    CHECK(shallow != p && shallow->info == p->info);
    CHECK(partial(shallow)->args()[0] == a);
    CHECK(partial(shallow)->args()[1] == partial(p)->args()[1]);
    Node * deep = p->deepcopy();
    CHECK(deep != p && deep->info == p->info);
    CHECK(*deep == *p);
    CHECK(partial(deep)->args()[1] != partial(p)->args()[1]);
    CHECK(partial(deep)->head_info == &set3_Info);
    CHECK(partial(deep)->missing == 2);
  }

  // partial_node: a shared node of the arena.
  {
    Node * p = partial_node(&set3_Info, 4);
    CHECK(gc_is_literal(p));
    CHECK(p->info == &PartApplic_Info);
    CHECK(partial(p)->missing == 4);
    CHECK(partial(p)->head_info == &set3_Info);
    CHECK(partial(p)->nargs() == 0);
    Node * q = Node::extend_partial(partial(p), a);
    CHECK(!gc_is_literal(q));
    CHECK(partial(q)->missing == 3);
    CHECK(partial(q)->args()[0] == a);
    CHECK(partial(p)->nargs() == 0);
  }

  // The collector marks through the argument slots: a rooted partial
  // application keeps its arguments; an unrooted one is reclaimed with
  // them.  The shared node of the arena stays.
  {
    Node * shared = partial_node(&set2_Info, 3);
    Node * kept = Node::create_partial(&set3_Info, heap_int(7000), heap_int(7001));
    Node * dropped = Node::create_partial(&set3_Info, heap_int(7002));
    gc_add_root(kept);
    size_t const before = gc_num_nodes();
    run_gc();
    CHECK(gc_num_nodes() < before); // dropped and its argument went
    CHECK(kept->info == partapplic_info(2));
    CHECK(int_value(partial(kept)->args()[0]) == 7000);
    CHECK(int_value(partial(kept)->args()[1]) == 7001);
    CHECK(partial(shared)->missing == 3);
    CHECK(partial(shared)->head_info == &set2_Info);
    gc_remove_root(kept);
    (void) dropped;
  }

  std::printf("ok\n");
  return 0;
}
