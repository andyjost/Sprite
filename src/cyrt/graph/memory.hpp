#pragma once
#include "cyrt/fwd.hpp"

namespace cyrt
{
  Node * node_reserve(size_t bytes);
  bool node_commit(void *, size_t bytes);

  extern bool g_gc_collect;
  void gc_register_rts(RuntimeState *);
  void gc_unregister_rts(RuntimeState *);

  // Runs a collection.  The caller must hold no node outside the roots: the
  // scheduler calls this at the top of its loop, and Python between
  // evaluations (gc_eval_depth() == 0).
  void run_gc();

  // Roots outside the graph.  A node that Python holds (a value handed to
  // Python, an expression built with curry.expr, a successor read from
  // Python) is registered when its wrapper is created and removed when the
  // wrapper is destroyed.  A node may be registered more than once.  It
  // stays a root until every registration is removed.
  void gc_add_root(Node *);
  void gc_remove_root(Node *);
  size_t gc_root_count(Node *); // registrations of one node
  size_t gc_num_roots();        // nodes registered

  // Statistics and the threshold.  See gc/wdgc.cpp for the policy.
  size_t gc_num_nodes();        // nodes allocated and not yet reclaimed
  size_t gc_num_collections();
  double gc_seconds();          // time spent in collections
  size_t gc_threshold();
  void gc_set_threshold(size_t);

  // Evaluation nesting.  procD and the direct step entry from Python bracket
  // their work with EvaluationScope.  gc_eval_depth() is the number of
  // evaluations on the C stack.  A collection in a nested evaluation
  // reclaims only the nodes allocated since that evaluation began.  The
  // steps of the enclosing evaluation may hold older nodes in C++ locals, so
  // every older node counts as a root.
  size_t gc_eval_depth();
  size_t gc_enter_evaluation(); // returns a token for gc_leave_evaluation
  void gc_leave_evaluation(size_t token);

  struct EvaluationScope
  {
    EvaluationScope() : token(gc_enter_evaluation()) {}
    ~EvaluationScope() { gc_leave_evaluation(this->token); }
    EvaluationScope(EvaluationScope const &) = delete;
    EvaluationScope & operator=(EvaluationScope const &) = delete;
    size_t token;
  };

  union RawNodeMemory
  {
    InfoTable const   ** info;
    Node              ** boxed;
    unboxed_int_type   * ub_int;
    unboxed_float_type * ub_float;
    unboxed_char_type  * ub_char;
    void              ** ub_ptr;
    char               * pos;

    RawNodeMemory(Node * mem) : pos((char *) mem) {}
    RawNodeMemory(char * mem) : pos(mem) {}
    operator char*() const { return pos; }
  };

  // Pack arguments according to the format string.  Returns the position of
  // the first argument not processed.
  Arg const * pack(char * out, char const * format, Arg const * args);

  // Compute the number of bytes needed to hold the given format string, up to
  // the specified number of arguments.
  size_t packed_size(char const * format, size_t limit=NOLIMIT);
}
