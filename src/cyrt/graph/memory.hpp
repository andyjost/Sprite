#pragma once
#include "cyrt/fwd.hpp"
#include <string>
#include <utility>
#include <vector>

namespace cyrt
{
  // The node heap.  A node lives in a block of its size class: blocks of
  // BLOCK_BYTES (gc/blockheap.cpp) hold slots of one size each, from
  // MIN_SLOT_BYTES to MAX_SMALL_BYTES in steps of SLOT_GRAIN; a larger node
  // gets a span of its own.  The size of a node is rounded up to the grain.
  // The allocator hands out runs of free slots: node_reserve, the fast path
  // below, takes the next slot of the run of the size class (a load, a
  // compare, an add, and a store); node_refill finds the next run.  The run
  // array is a global of the runtime library, which generated code reaches
  // through one indirection.  A collection may run only at a safepoint of
  // the scheduler (run_gc), never inside node_reserve.
  //
  // The runtime of an instrumented build (SPRITE_SCHEDULER_COUNTERS) never
  // publishes a run, so every allocation goes through node_refill, which
  // records the creator of the node (see node_creator).  The fast path is
  // the same in both builds, so a generated module serves both.
  inline constexpr size_t round_up(size_t bytes)
    { return (bytes + 7) & ~size_t(7); }
  static constexpr size_t SLOT_GRAIN      = 8;
  static constexpr size_t MIN_SLOT_BYTES  = 16;
  static constexpr size_t MAX_SMALL_BYTES = 512;
  static constexpr size_t NUM_SIZE_CLASSES
      = (MAX_SMALL_BYTES - MIN_SLOT_BYTES) / SLOT_GRAIN + 1;

  // The run of free slots of one size class: the slots from ``free`` up to
  // ``limit``.  An empty run is two null pointers.
  struct AllocRun
  {
    char * free;
    char * limit;
  };
  extern AllocRun g_alloc_runs[NUM_SIZE_CLASSES];

  // The slow path of node_reserve: finds the next run of free slots of the
  // size class, or takes a block, and returns the first slot.  Throws
  // std::bad_alloc when the system has no memory left.
  Node * node_refill(size_t bytes);

  inline Node * node_reserve(size_t bytes)
  {
    size_t const slot_bytes = round_up(bytes);
    // One unsigned comparison checks both bounds of the size class.
    size_t const c = (slot_bytes - MIN_SLOT_BYTES) / SLOT_GRAIN;
    if(c < NUM_SIZE_CLASSES)
    {
      AllocRun & run = g_alloc_runs[c];
      char * const addr = run.free;
      if(size_t(run.limit - addr) >= slot_bytes)
      {
        run.free = addr + slot_bytes;
        return (Node *) addr;
      }
    }
    return node_refill(bytes);
  }

  // A remnant of the reserve-and-commit protocol of a moving collector.
  // This heap never moves a node, so a reservation always holds.  The MPS
  // back end (gc/mps.cpp, make GC=mps) commits inside node_refill, so this
  // stays true there too.
  inline bool node_commit(void *, size_t) { return true; }

  // The collector of this build: "wdgc", the block heap of gc/blockheap.cpp
  // with the collector of gc/wdgc.cpp, or "mps", the Memory Pool System of
  // gc/mps.cpp (make GC=mps).
  char const * gc_backend_name();

  // Statistics of the collector beyond the counters below, by name.  Empty
  // for wdgc.  The MPS back end reports its barrier faults, the time in
  // them, the time in its allocation slow path, and the sizes of its arena.
  std::vector<std::pair<std::string, double>> gc_backend_stats();

  // The barrier faults the collector handled.  Zero for wdgc.
  size_t gc_fault_count();

  // A region in which no node moves.  An algorithm that keys a table by
  // the address of a node (the graph copier, the equality, show, the unique
  // visitor of walk.hpp) holds one for its lifetime.  The default collector
  // never moves a node, so this does nothing there; the MPS back end clamps
  // its arena.
  struct GcClamp
  {
    GcClamp();
    ~GcClamp();
    GcClamp(GcClamp const &) = delete;
    GcClamp & operator=(GcClamp const &) = delete;
  };

  #ifdef SPRITE_GC_MPS
  // The MPS object format reads the size of a node from its info table.  So
  // a node rewritten in place into a smaller one (Node::rewrite,
  // Node::forward_or_copy, Node::rewrite_from_partial) leaves a pad object
  // of the collector in the slack of its block: a pad of 8 bytes is the
  // table GcPad_Info alone, a larger one records its size in its second
  // word.  See gc/mps.cpp.
  extern InfoTable const GcPad_Info;
  extern InfoTable const GcPadSz_Info;
  inline void gc_pad(void * addr, size_t bytes)
  {
    InfoTable const ** words = (InfoTable const **) addr;
    if(bytes == sizeof(void *))
      words[0] = &GcPad_Info;
    else
    {
      words[0] = &GcPadSz_Info;
      ((size_t *) addr)[1] = bytes;
    }
  }
  inline void gc_pad_slack(Node * node, size_t old_bytes, size_t new_bytes)
  {
    if(new_bytes < old_bytes)
      gc_pad((char *) node + new_bytes, old_bytes - new_bytes);
  }
  #else
  inline void gc_pad_slack(Node *, size_t, size_t) {}
  #endif

  extern bool g_gc_collect;
  void gc_register_rts(RuntimeState *);
  void gc_unregister_rts(RuntimeState *);

  // The interpreter states (see state/rts.hpp).  Each holds a free-variable
  // table, which the collector sweeps: an entry whose node is unreachable
  // is dropped.  A state registers itself when it is made and unregisters
  // itself when it is destroyed.
  void gc_register_istate(InterpreterState *);
  void gc_unregister_istate(InterpreterState *);
  size_t gc_num_freevars(); // entries of the free-variable tables

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

  // Literal nodes.  A node of a primitive value that lives as long as the
  // process: the shared nodes of the small integers and the ASCII characters
  // (see int_ and char_ in builtins.hpp), and the literal nodes of the
  // generated modules, made once when a module loads (literal_node).  They
  // come from an arena of their own, outside the heap of the collector.  The
  // collector never marks, sweeps, or frees them; its mark phase tells them
  // apart by their address.  So a collection costs nothing for them, which
  // matters in the stress mode, where every step collects.  The arena is
  // one block of LITERAL_ARENA_BYTES; literal_reserve throws when it is
  // full.  No literal node is ever written: see Node::rewrite.
  static constexpr size_t LITERAL_ARENA_BYTES = size_t(16) << 20;
  Node * literal_reserve(size_t bytes);
  bool gc_is_literal(Node const *); // allocated by literal_reserve
  size_t gc_num_literals();         // nodes allocated by literal_reserve

  // The objects of the scheduler.  A Queue and a Set register themselves
  // when they are made and unregister themselves when they are destroyed.
  // The collector destroys a queue that no runtime state and no SetEval node
  // reaches, and a set that no queue, no SetEval node, and no SetGuard node
  // reaches, at the end of a collection.  See gc/wdgc.cpp.
  void gc_register_queue(Queue *);
  void gc_unregister_queue(Queue *);
  void gc_register_set(Set *);
  void gc_unregister_set(Set *);

  // Live objects of the scheduler, for leak checks.  A configuration counts
  // from its construction (gc_configuration_created, which also requests a
  // collection when the count reaches the threshold of the collector) to
  // its destruction.  At a safepoint of the scheduler, every live
  // configuration is in a registered queue, so gc_num_configurations() is
  // at most the sum of gc_queue_lengths(); it is less when the split of a
  // set function's queue left a configuration in two queues.
  void gc_configuration_created();
  void gc_configuration_destroyed();
  size_t gc_num_configurations();
  size_t gc_num_queues();
  size_t gc_num_sets();
  std::vector<size_t> gc_queue_lengths();

  // Statistics and the threshold.  See gc/wdgc.cpp for the policy.
  size_t gc_num_nodes();        // nodes allocated and not yet reclaimed
  size_t gc_num_allocations();  // nodes allocated since the start
  size_t gc_num_collections();
  double gc_seconds();          // time spent in collections
  size_t gc_threshold();
  void gc_set_threshold(size_t);
  size_t gc_growth();           // the growth factor of the adaptive policy
  // True when the collector runs at every safepoint (SPRITE_GC_STRESS=1 in
  // the environment).  A test suite run in this mode finds a missing root
  // at once, and the verifier checks the heap at every collection.  See
  // gc/wdgc.cpp.
  bool gc_stress();
  // The heap (gc/blockheap.cpp): the blocks that hold nodes, the spans of
  // large nodes included, and the bytes the heap holds from the system, in
  // use or pooled.
  size_t gc_num_blocks();
  size_t gc_heap_bytes();
  // Runs a collection with the heap verifier (see gc/blockheap.cpp) and
  // returns the first problem found, or the empty string.  Between
  // evaluations only, like run_gc.
  std::string gc_verify();

  // Generator nodes (biGeneratorNode in builtins.hpp) own a Python object,
  // which the collector releases when the node dies unstepped.  Every
  // creator of such a node registers it, so the sweep finds the dead ones
  // without a walk over the heap.
  void gc_register_generator(Node *);

  // SetEval nodes (currylib/setfunctions.hpp) refer to the queue of a set
  // function.  Every creator of such a node registers it.  The default
  // collector reaches the queue through the node and needs no registration
  // (the function does nothing); the MPS back end finalizes the node and
  // destroys the queue when the last node that refers to it has died.
  void gc_register_seteval(Node *);

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

  #ifdef SPRITE_SCHEDULER_COUNTERS
  // The scheduler counters (state/counters.hpp) need the creator of a node.
  // The scheduler sets the serial number of the configuration it steps, and
  // node_refill records it for every node it hands out, in a table beside
  // the block of the node (see gc/blockheap.cpp).  Zero means no
  // configuration: a node built outside the scheduler, or a literal node.
  extern size_t g_creator_serial;
  size_t node_creator(Node const *);
  #endif

  // Pack arguments according to the format string.  Returns the position of
  // the first argument not processed.
  Arg const * pack(char * out, char const * format, Arg const * args);

  // Compute the number of bytes needed to hold the given format string, up to
  // the specified number of arguments.
  size_t packed_size(char const * format, size_t limit=NOLIMIT);
}
