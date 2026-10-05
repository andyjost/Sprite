// Checks Node::successor_node and Variable::successor_node (see
// cyrt/graph/node.hxx and cyrt/graph/indexing.hxx): the plain reads of an
// argument that a step only passes on.  unit_cxx_passthrough.py compiles this
// program against the installed runtime and runs it.  It prints the first
// failed check and exits with status 1; it prints "ok" and exits with status
// 0 when every check passes.
#include "cyrt/cyrt.hpp"
#include <cstdio>
#include <cstdlib>

using namespace cyrt;

#define CHECK(cond) \
    do { if(!(cond)) { std::printf("failed: %s (line %d)\n", #cond, __LINE__); std::exit(1); } } while(0)

int main()
{
  // A plain slot: the node, and the slot is as it was.
  {
    Node * seven = int_(7);
    Node * node = pair(seven, int_(8));
    CHECK(node->successor_node(0) == seven);
    CHECK(node->successors()[0].node == seven);
    CHECK(node->successor_node(1) == int_(8));
  }

  // A forward node of one link: the end of the chain, and the slot is
  // shortened to it.
  {
    Node * seven = int_(7);
    Node * link = fwd(seven);
    Node * node = pair(link, int_(8));
    CHECK(node->successor_node(0) == seven);
    CHECK(node->successors()[0].node == seven);
    CHECK(NodeU{link}.fwd->target == seven);
  }

  // A chain of two links: the slot and the first link point to the end.
  {
    Node * seven = int_(7);
    Node * second = fwd(seven);
    Node * first = fwd(second);
    Node * node = pair(first, int_(8));
    CHECK(node->successor_node(0) == seven);
    CHECK(node->successors()[0].node == seven);
    CHECK(NodeU{first}.fwd->target == seven);
    CHECK(NodeU{second}.fwd->target == seven);
  }

  // A set guard in the slot stays: the guard is part of the argument.
  {
    Set set;
    Node * inner = pair(int_(1), int_(2));
    Node * guarded = guard(&set, inner);
    Node * node = pair(guarded, int_(8));
    CHECK(node->successor_node(0) == guarded);
    CHECK(node->successors()[0].node == guarded);
    CHECK(NodeU{guarded}.setgrd->value == inner);
  }

  // A null slot: a recursive let before its patch.
  {
    Node * node = pair(nullptr, int_(8));
    CHECK(node->successor_node(0) == nullptr);
  }

  // A variable without guards over a constructor: the plain read, with the
  // slot of the constructor shortened.
  {
    Node * seven = int_(7);
    Node * inner = pair(fwd(seven), int_(2));
    Node * node = pair(inner, int_(8));
    Variable var(node, 0);
    CHECK(var.guards.empty());
    CHECK(var.successor_node(0) == seven);
    CHECK(inner->successors()[0].node == seven);
    CHECK(var.successor_node(1) == int_(2));
  }

  // A variable that crossed a guard: the successor is wrapped in the guard
  // again, as the indexer yields it.
  {
    Set set;
    Node * seven = int_(7);
    Node * inner = pair(seven, int_(2));
    Node * guarded = guard(&set, inner);
    Node * node = pair(guarded, int_(8));
    Variable var(node, 0);
    CHECK(var.guards.size() == 1);
    Node * result = var.successor_node(0);
    CHECK(result != guarded);
    CHECK(result->info == &SetGuard_Info);
    CHECK(NodeU{result}.setgrd->set == &set);
    CHECK(NodeU{result}.setgrd->value == seven);
    Node * indexed = var[0].rvalue();
    CHECK(indexed->info == &SetGuard_Info);
    CHECK(NodeU{indexed}.setgrd->value == seven);
  }

  // A variable whose target became a forward node: the indexer crosses it.
  {
    Node * inner = pair(int_(7), int_(2));
    Node * node = pair(inner, int_(8));
    Variable var(node, 0);
    Node * replacement = pair(int_(3), int_(4));
    inner->forward_to(replacement);
    CHECK(var.successor_node(0) == int_(3));
    CHECK(var.successor_node(1) == int_(4));
  }

  std::printf("ok\n");
  return 0;
}
