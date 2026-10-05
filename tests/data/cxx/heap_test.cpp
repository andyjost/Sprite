// Checks the block heap of the runtime (cyrt/graph/gc/blockheap.cpp and the
// inline fast path in cyrt/graph/memory.hpp): the runs of slots, the exact
// counts, the lazy sweep that reuses freed slots, the spans of large nodes,
// the rule for nested evaluations, the generator finalizer, and the
// verifier.  unit_cxx_heap.py compiles this program against the installed
// runtime and runs it.  It prints the first failed check and exits with
// status 1; it prints "ok" and exits with status 0 when every check passes.
#include "cyrt/cyrt.hpp"
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

using namespace cyrt;

#define CHECK(cond) \
    do { if(!(cond)) { std::printf("failed: %s (line %d)\n", #cond, __LINE__); std::exit(1); } } while(0)

// A function of 71 arguments: its node takes 576 bytes, more than the
// largest size class, so it lives in a span of its own.
static std::string const big_format(71, 'p');
static InfoTable const big_Info{
    /*tag*/        T_FUNC
  , /*arity*/      71
  , /*alloc_size*/ (index_type) (sizeof(Head) + 71 * sizeof(Arg))
  , /*flags*/      NO_FLAGS
  , /*name*/       "big"
  , /*format*/     big_format.c_str()
  , /*step*/       nullptr
  , /*type*/       nullptr
  };

static Node * make_big(Node * arg)
{
  std::vector<Arg> args(71, Arg(arg));
  return Node::create(&big_Info, args.data());
}

// A node of the heap: an integer outside the shared table.
static Node * heap_int(unboxed_int_type value)
{
  return int_(SMALL_INT_MAX + 1 + value);
}

// The generator hooks: counts of the acquisitions and releases per object.
static int g_acquired = 0;
static int g_released = 0;
static void * g_last_released = nullptr;
static Node * next_item(void *) { return nullptr; }
static void acquire(void *) { ++g_acquired; }
static void release(void * data) { ++g_released; g_last_released = data; }

int main()
{
  CHECK(MIN_SLOT_BYTES == 16 && MAX_SMALL_BYTES == 512);
  CHECK(NUM_SIZE_CLASSES == 63);

  // A fresh heap: a collection leaves nothing, and the counts are exact.
  run_gc();
  CHECK(gc_num_nodes() == 0);
  size_t const heap0 = gc_heap_bytes();
  size_t const blocks0 = gc_num_blocks();

  // Slots of one class come from one run: consecutive addresses, the slot
  // size apart, each aligned to the grain.  A node of another class comes
  // from another block.
  {
    size_t const allocations = gc_num_allocations();
    Node * a = cons(heap_int(1), Nil);
    Node * b = cons(heap_int(2), Nil);
    Node * c = cons(heap_int(3), Nil);
    CHECK(gc_num_allocations() == allocations + 6);
    CHECK(gc_num_nodes() == 6);
    CHECK((uintptr_t) a % 8 == 0 && (uintptr_t) b % 8 == 0);
    CHECK((char *) b - (char *) a == sizeof(ConsNode));
    CHECK((char *) c - (char *) b == sizeof(ConsNode));
    Node * i1 = NodeU{a}.cons->head;
    Node * i2 = NodeU{b}.cons->head;
    CHECK((char *) i2 - (char *) i1 == sizeof(IntNode));
    CHECK(((uintptr_t) a >> 16) != ((uintptr_t) i1 >> 16)); // another block
    CHECK(gc_heap_bytes() == heap0 + (heap0 ? 0 : size_t(1) << 20));
    CHECK(gc_num_blocks() == blocks0 + 2);
  }

  // A collection keeps a rooted node with its successors and reclaims the
  // rest.  gc_add_root is the root registry (the nodes Python holds).
  Node * kept = cons(heap_int(10), cons(heap_int(11), Nil));
  gc_add_root(kept);
  run_gc();
  CHECK(gc_num_nodes() == 4);
  CHECK(NodeU{kept}.cons->head->info == &Int_Info);
  CHECK(NodeU{NodeU{kept}.cons->head}.int_->value == SMALL_INT_MAX + 11);
  CHECK(gc_verify().empty());
  CHECK(gc_num_nodes() == 4);

  // The lazy sweep: the slots of the dead nodes are handed out again, in
  // address order, before the heap takes new memory.
  {
    std::vector<Node *> live, dead;
    for(int i = 0; i < 1000; ++i)
    {
      Node * node = cons(Nil, Nil);
      if(i % 3 == 0)
      {
        gc_add_root(node);
        live.push_back(node);
      }
      else
        dead.push_back(node);
    }
    size_t const heap1 = gc_heap_bytes();
    run_gc();
    CHECK(gc_num_nodes() == 4 + live.size());
    CHECK(gc_heap_bytes() == heap1);
    std::vector<Node *> reused;
    for(size_t i = 0; i < dead.size(); ++i)
      reused.push_back(cons(Nil, Nil));
    CHECK(gc_heap_bytes() == heap1);
    std::sort(dead.begin(), dead.end());
    std::vector<Node *> sorted(reused);
    std::sort(sorted.begin(), sorted.end());
    CHECK(sorted == dead);
    CHECK(reused == sorted); // in address order: the first free run first
    for(Node * node: live)
      gc_remove_root(node);
    run_gc();
    CHECK(gc_num_nodes() == 4);
  }

  // Many short-lived nodes cycle through the same memory: the heap stays
  // the size of one cycle.
  {
    for(int round = 0; round < 3; ++round)
    {
      for(int i = 0; i < 200000; ++i)
        cons(Nil, Nil);
      run_gc();
    }
    size_t const heap2 = gc_heap_bytes();
    for(int i = 0; i < 200000; ++i)
      cons(Nil, Nil);
    run_gc();
    CHECK(gc_heap_bytes() == heap2);
    CHECK(gc_num_nodes() == 4);
  }

  // A large node: a span of its own, kept while rooted, with its successors,
  // and given back to the system when it dies.
  {
    size_t const heap3 = gc_heap_bytes();
    size_t const blocks3 = gc_num_blocks();
    Node * big = make_big(heap_int(77));
    CHECK(big->info == &big_Info);
    CHECK(gc_num_blocks() == blocks3 + 1);
    CHECK(gc_heap_bytes() == heap3 + (size_t(64) << 10));
    gc_add_root(big);
    run_gc();
    CHECK(gc_num_nodes() == 6);
    for(index_type i = 0; i < 71; ++i)
      CHECK(NodeU{big->successors()[i].node}.int_->value == SMALL_INT_MAX + 78);
    CHECK(gc_verify().empty());
    gc_remove_root(big);
    run_gc();
    CHECK(gc_num_nodes() == 4);
    CHECK(gc_num_blocks() == blocks3);
    CHECK(gc_heap_bytes() == heap3);
  }

  // Nested evaluations.  Inside a nested evaluation, every node of a block
  // taken before it began is a root: an unrooted older node and the newer
  // node it points to survive a nested collection, and a newer node that
  // nothing holds does not.  Both older nodes go at the next outermost
  // collection.
  {
    EvaluationScope outer;
    CHECK(gc_eval_depth() == 1);
    Node * older = cons(heap_int(20), Nil);
    size_t const before = gc_num_nodes();
    {
      EvaluationScope nested;
      CHECK(gc_eval_depth() == 2);
      Node * newer = cons(heap_int(21), Nil);
      NodeU{older}.cons->tail = newer;
      // A size class used here for the first time takes a new block, so
      // this node is in a newer block.
      Node * garbage = make_node<ChoiceNode>(xid_type(1), Nil, Nil);
      CHECK(garbage->info == &Choice_Info);
      run_gc();
      CHECK(gc_num_nodes() == before + 2);
      CHECK(NodeU{NodeU{older}.cons->tail}.cons->head->info == &Int_Info);
      CHECK(NodeU{NodeU{NodeU{older}.cons->tail}.cons->head}.int_->value
            == SMALL_INT_MAX + 22);
    }
    CHECK(gc_eval_depth() == 1);
    run_gc();
    CHECK(gc_num_nodes() == 4);
  }
  CHECK(gc_eval_depth() == 0);

  // The generator finalizer: a generator node that dies unstepped gives its
  // object back once, at the collection; a rooted one keeps it; a copy owns
  // a reference of its own.
  {
    register_generator_funcs(next_item, acquire, release);
    int object = 0;
    Node * gen = generator(&object);
    gc_add_root(gen);
    run_gc();
    CHECK(g_released == 0);
    Node * copy = copy_node(gen);
    CHECK(g_acquired == 1);
    run_gc(); // the copy is not rooted
    CHECK(g_released == 1 && g_last_released == &object);
    gc_remove_root(gen);
    run_gc();
    CHECK(g_released == 2);
    (void) copy;
  }

  // The verifier: a live node whose successor is a freed slot is found.  The
  // collection of gc_verify makes that slot a node again, so the heap is
  // consistent afterwards.
  {
    Node * dropped = cons(heap_int(30), Nil);
    run_gc();
    NodeU{kept}.cons->tail = dropped;
    std::string const problem = gc_verify();
    CHECK(problem.find("a mark on a free slot") != std::string::npos);
    CHECK(gc_verify().empty());
    NodeU{kept}.cons->tail = Nil;
    run_gc();
    CHECK(gc_num_nodes() == 2);
  }

  // A pinned constructor has one node, the static object: a copy of it is
  // the node itself, and the heap does not grow.  A heap copy with its info
  // table, made here by hand, is never marked; the verifier finds it among
  // the roots and among the successors before the sweep frees it.
  {
    CHECK(copy_node(Nil) == Nil);
    CHECK(copy_node(Unit) == Unit);
    CHECK(copy_node(True) == True);
    CHECK(gc_num_nodes() == 2);
    Node * bogus = node_reserve(MIN_SLOT_BYTES);
    bogus->info = &Nil_Info;
    CHECK(node_commit(bogus, MIN_SLOT_BYTES));
    gc_add_root(bogus);
    std::string problem = gc_verify();
    CHECK(problem.find("a root is a heap copy of a pinned constructor")
          != std::string::npos);
    gc_remove_root(bogus); // the collection of gc_verify freed its slot
    CHECK(gc_verify().empty());
    bogus = node_reserve(MIN_SLOT_BYTES);
    bogus->info = &Nil_Info;
    CHECK(node_commit(bogus, MIN_SLOT_BYTES));
    NodeU{kept}.cons->tail = bogus;
    problem = gc_verify();
    CHECK(problem.find("a successor is a heap copy of a pinned constructor")
          != std::string::npos);
    NodeU{kept}.cons->tail = Nil;
    CHECK(gc_verify().empty());
    CHECK(gc_num_nodes() == 2);
  }

  gc_remove_root(kept);
  run_gc();
  CHECK(gc_num_nodes() == 0);
  CHECK(gc_verify().empty());

  std::printf("ok\n");
  return 0;
}
