// A "garbage collector" that just leaks everything.  Every allocation goes
// through node_refill (no run is ever published), which takes the node from
// malloc.  Not selected; see graph/memory.cpp.

#ifdef SPRITE_SCHEDULER_COUNTERS
#error "the scheduler counters need the creator table of gc/blockheap.cpp"
#endif

namespace cyrt
{
  AllocRun g_alloc_runs[NUM_SIZE_CLASSES];

  Node * node_refill(size_t bytes)
  {
    void * addr = std::malloc(round_up(bytes));
    if(!addr)
      throw std::bad_alloc();
    return (Node *) addr;
  }

  void run_gc() {}
  size_t gc_num_nodes() { return 0; }
  size_t gc_num_allocations() { return 0; }
  size_t gc_num_collections() { return 0; }
  double gc_seconds() { return 0.0; }
  size_t gc_threshold() { return NOLIMIT; }
  void gc_set_threshold(size_t) {}
  size_t gc_growth() { return 0; }
  bool gc_stress() { return false; }
  size_t gc_num_blocks() { return 0; }
  size_t gc_heap_bytes() { return 0; }
  std::string gc_verify() { return std::string(); }
  void gc_register_generator(Node *) {}
  size_t gc_enter_evaluation() { ++g_eval_depth; return 0; }
  void gc_leave_evaluation(size_t) { --g_eval_depth; }
}
