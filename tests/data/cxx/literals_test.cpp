// Checks the shared literal nodes of the runtime: the tables of the small
// integers and the ASCII characters that int_ and char_ return, and
// literal_node (see cyrt/builtins.hpp and literal_reserve in
// cyrt/graph/memory.hpp).  unit_cxx_literals.py compiles this program
// against the installed runtime and runs it.  It prints the first failed
// check and exits with status 1; it prints "ok" and exits with status 0 when
// every check passes.
#include "cyrt/cyrt.hpp"
#include "cyrt/currylib/prelude.hpp"
#include <cstdio>
#include <cstdlib>

using namespace cyrt;

#define CHECK(cond) \
    do { if(!(cond)) { std::printf("failed: %s (line %d)\n", #cond, __LINE__); std::exit(1); } } while(0)

static unboxed_int_type int_value(Node * node)
{
  CHECK(node->info == &Int_Info);
  return NodeU{node}.int_->value;
}

static unboxed_char_type char_value(Node * node)
{
  CHECK(node->info == &Char_Info);
  return NodeU{node}.char_->value;
}

int main()
{
  // The tables are full when the library has loaded.
  CHECK(gc_num_literals() >= size_t(SMALL_INT_MAX - SMALL_INT_MIN + 1)
                           + size_t(SMALL_CHAR_MAX + 1));
  size_t const literals = gc_num_literals();

  // A small integer is one node, whatever the number of calls, and the
  // calls allocate nothing.
  {
    size_t const allocations = gc_num_allocations();
    Node * one = int_(1);
    CHECK(one == int_(1));
    CHECK(int_value(one) == 1);
    CHECK(int_(SMALL_INT_MIN) == int_(SMALL_INT_MIN));
    CHECK(int_value(int_(SMALL_INT_MIN)) == SMALL_INT_MIN);
    CHECK(int_(SMALL_INT_MAX) == int_(SMALL_INT_MAX));
    CHECK(int_value(int_(SMALL_INT_MAX)) == SMALL_INT_MAX);
    CHECK(int_(0) != int_(1));
    CHECK(int_(-1) != int_(1));
    CHECK(int_value(int_(-1)) == -1);
    CHECK(gc_num_allocations() == allocations);
  }

  // An integer outside the table is a new node each time.
  {
    size_t const allocations = gc_num_allocations();
    Node * a = int_(SMALL_INT_MAX + 1);
    Node * b = int_(SMALL_INT_MAX + 1);
    CHECK(a != b);
    CHECK(int_value(a) == SMALL_INT_MAX + 1);
    CHECK(int_(SMALL_INT_MIN - 1) != int_(SMALL_INT_MIN - 1));
    CHECK(int_value(int_(SMALL_INT_MIN - 1)) == SMALL_INT_MIN - 1);
    CHECK(gc_num_allocations() == allocations + 5);
  }

  // The same for the characters: ASCII is shared, the rest is not.
  {
    size_t const allocations = gc_num_allocations();
    CHECK(char_(U'a') == char_(U'a'));
    CHECK(char_value(char_(U'a')) == U'a');
    CHECK(char_(0) == char_(0));
    CHECK(char_(SMALL_CHAR_MAX) == char_(SMALL_CHAR_MAX));
    CHECK(char_(U'a') != char_(U'b'));
    CHECK(gc_num_allocations() == allocations);
    Node * lambda = char_(0x3bb);
    CHECK(lambda != char_(0x3bb));
    CHECK(char_value(lambda) == 0x3bb);
    CHECK(gc_num_allocations() == allocations + 2);
  }

  // A float is never shared.
  {
    Node * a = float_(1.5);
    Node * b = float_(1.5);
    CHECK(a != b);
    CHECK(a->info == &Float_Info);
    CHECK(NodeU{a}.float_->value == 1.5);
  }

  // A Curry string built by the runtime shares the nodes of its ASCII
  // characters.
  {
    Node * str = build_curry_string("ab");
    CHECK(str->info->tag == T_CONS);
    CHECK(NodeU{str}.cons->head == char_(U'a'));
    Node * rest = NodeU{str}.cons->tail;
    CHECK(NodeU{rest}.cons->head == char_(U'b'));
  }

  // literal_node makes a node of any primitive value outside the heap of
  // the collector.  It survives a collection; a plain node that nothing
  // reaches does not.
  {
    Node * pi = literal_node(&Float_Info, Arg(3.25));
    CHECK(gc_num_literals() == literals + 1);
    CHECK(gc_is_literal(pi));
    CHECK(gc_is_literal(int_(1)));
    CHECK(gc_is_literal(char_(U'a')));
    Node * big = literal_node(&Int_Info, Arg(unboxed_int_type(1) << 40));
    CHECK(gc_num_literals() == literals + 2);
    Node * plain = float_(2.75);
    CHECK(!gc_is_literal(plain));
    CHECK(!gc_is_literal(int_(SMALL_INT_MAX + 1)));
    size_t const nodes = gc_num_nodes();
    run_gc();
    CHECK(gc_num_nodes() < nodes);
    CHECK(pi->info == &Float_Info);
    CHECK(NodeU{pi}.float_->value == 3.25);
    CHECK(int_value(big) == (unboxed_int_type(1) << 40));
    // The tables are intact as well.
    CHECK(int_value(int_(1)) == 1);
    CHECK(int_value(int_(SMALL_INT_MAX)) == SMALL_INT_MAX);
    CHECK(char_value(char_(U'z')) == U'z');
    CHECK(gc_num_literals() == literals + 2);
  }

  // A reference result that is a shared node is copied into the redex; the
  // shared node is unchanged.
  {
    Node * seven = int_(7);
    Node * node = Node::create(&failed_Info);
    CHECK(node->forward_or_copy(seven) == Int_Info.tag);
    CHECK(node != seven);
    CHECK(int_value(node) == 7);
    CHECK(int_value(seven) == 7);
    CHECK(seven == int_(7));
  }

  std::printf("ok\n");
  return 0;
}
