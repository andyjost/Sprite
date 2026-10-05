// Checks Node::rewrite, Node::forward_or_copy, and Node::rewrite_from_partial
// (see cyrt/graph/node.hxx).  unit_cxx_rewrite.py compiles this program
// against the installed runtime and runs it.  It prints the first failed
// check and exits with status 1; it prints "ok" and exits with status 0 when
// every check passes.
#include "cyrt/cyrt.hpp"
#include <cstdio>
#include <cstdlib>

using namespace cyrt;

#define CHECK(cond) \
    do { if(!(cond)) { std::printf("failed: %s (line %d)\n", #cond, __LINE__); std::exit(1); } } while(0)

static unboxed_int_type value_of(Node * node)
{
  CHECK(node->info == &Int_Info);
  return NodeU{node}.int_->value;
}

int main()
{
  // The arguments change places: both are read before a slot is written.
  {
    Node * one = int_(1);
    Node * two = int_(2);
    Node * node = pair(one, two);
    Variable a(node, 0);
    Variable b(node, 1);
    tag_type const tag = node->rewrite(&Pair_Info, b, a);
    CHECK(tag == Pair_Info.tag);
    CHECK(node->info == &Pair_Info);
    CHECK(node->successors()[0].node == two);
    CHECK(node->successors()[1].node == one);
  }

  // A nullary result: the info table alone is written.
  {
    Node * node = pair(int_(1), int_(2));
    tag_type const tag = node->rewrite(&failed_Info);
    CHECK(tag == T_FUNC);
    CHECK(node->info == &failed_Info);
  }

  // A smaller result in a larger block: a boxed value in the block of a
  // choice.  A copy of the node takes the size of the new info table.
  {
    Node * node = choice(0, int_(1), int_(2));
    tag_type const tag = node->rewrite(&Int_Info, unboxed_int_type(42));
    CHECK(tag == Int_Info.tag);
    CHECK(value_of(node) == 42);
    Node * copy = node->copy();
    CHECK(copy != node);
    CHECK(value_of(copy) == 42);
  }

  // A reference result that is a primitive value is copied.  The value's own
  // node is unchanged.
  {
    Node * seven = int_(7);
    Node * node = Node::create(&failed_Info);
    tag_type const tag = node->forward_or_copy(seven);
    CHECK(tag == Int_Info.tag);
    CHECK(node->info == &Int_Info);
    CHECK(node != seven);
    CHECK(value_of(node) == 7);
    CHECK(value_of(seven) == 7);
  }

  // A reference result that is a pinned constructor, or a function node,
  // keeps the forward node.
  {
    Node * node = Node::create(&failed_Info);
    CHECK(node->forward_or_copy(Nil) == T_FWD);
    CHECK(node->info->tag == T_FWD);
    CHECK(NodeU{node}.fwd->target == Nil);
    Node * other = Node::create(&failed_Info);
    Node * target = Node::create(&failed_Info);
    CHECK(other->forward_or_copy(target) == T_FWD);
    CHECK(NodeU{other}.fwd->target == target);
  }

  // A reference result through a Variable: the value of the variable.
  {
    Node * seven = int_(7);
    Node * list = cons(seven, Nil);
    Node * node = Node::create(&failed_Info);
    Variable head(list, 0);
    CHECK(node->forward_or_copy(head) == Int_Info.tag);
    CHECK(value_of(node) == 7);
  }

  // A completed partial application is written into the redex.
  {
    Node * one = int_(1);
    Node * two = int_(2);
    Node * partial = Node::create_partial(&Pair_Info, one);
    Node * node = Node::create(&apply_Info, partial, two);
    PartApplicNode * p = NodeU{partial}.partapplic;
    CHECK(p->complete(two));
    CHECK(Pair_Info.alloc_size <= node->info->alloc_size);
    tag_type const tag = node->rewrite_from_partial(p, two);
    CHECK(tag == Pair_Info.tag);
    CHECK(node->info == &Pair_Info);
    CHECK(node->successors()[0].node == one);
    CHECK(node->successors()[1].node == two);
  }

  std::printf("ok\n");
  return 0;
}
