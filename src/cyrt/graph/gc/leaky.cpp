// A "garbage collector" that just leaks everything.

namespace cyrt
{
  Node * node_reserve(size_t bytes)
  {
    return (Node *) std::malloc(bytes);
  }

  bool node_commit(void * addr, size_t bytes)
  {
    return true;
  }

  void run_gc() {}
  size_t gc_num_nodes() { return 0; }
  size_t gc_num_collections() { return 0; }
  double gc_seconds() { return 0.0; }
  size_t gc_threshold() { return NOLIMIT; }
  void gc_set_threshold(size_t) {}
  size_t gc_enter_evaluation() { ++g_eval_depth; return 0; }
  void gc_leave_evaluation(size_t) { --g_eval_depth; }
}
