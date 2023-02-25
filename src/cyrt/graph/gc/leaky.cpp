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
}

