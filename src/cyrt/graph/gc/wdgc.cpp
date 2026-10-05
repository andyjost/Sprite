// The collector: mark and sweep over the block heap of gc/blockheap.cpp.
// There are no generations and nothing is moved.
//
// Allocation.  Nodes live in blocks of one size class each (see
// gc/blockheap.cpp).  node_reserve takes the next slot of the run of its
// size class inline; node_refill finds the next run of free slots by the
// ``alloc`` bitmap of a block (a lazy sweep), or takes a block.  The mark
// bit of a node is in the ``mark`` bitmap of its block, so the mark phase
// leaves the info pointer alone, and the sweep visits blocks, not nodes: it
// counts the marks, hands the mark bitmap over as the allocation bitmap,
// and puts an empty block into the pool.  Memory taken from the system is
// kept for the next allocations.
//
// Roots.  The queues of every runtime state (the root, the bindings, and the
// error value of each configuration, and the free variables it names by id,
// see below), the nodes registered with gc_add_root (the nodes Python
// holds), and the queue of every SetEval node reached: a lazy set function
// keeps the alternatives it has not produced yet in that queue, which is
// reachable only through the node.  The literal nodes (the tables of the
// small integers and the ASCII characters, and the literals of the loaded
// modules; see literal_reserve in graph/memory.cpp) are not in the heap of
// this collector: the mark phase skips them by their address, and the sweep
// never sees them.
//
// Free variables.  The free-variable table of an interpreter state
// (InterpreterState::vtable, state/rts.hpp) maps the id of a free variable
// to its node, for the places that name a variable by its id alone.  The
// table is weak: it is not a root, and after the mark phase an entry whose
// node is unmarked is dropped (sweep_freevar_tables).  So a variable and its
// generator die with the expression that held them; before, the table kept
// every variable ever made, with its generator, for the life of the
// evaluation.  The ids a live configuration can still look up are pushed
// with the queue that holds it (push_queue_roots): its residuals (a
// suspended configuration asks for the variable each time it is tried,
// RuntimeState::ready), the keys of its bindings (fork applies the binding
// of a variable through the variable's generator), and the ids in its
// strict constraints (the group of a variable is named by its root, which
// stands for the group at the root of a configuration and receives the
// generator of a narrowed member at the fork).  Every other lookup starts
// from a free variable in the graph, which is marked, or from the choice of
// a generator at the root of a configuration, whose variable the fork asks
// for only to apply a binding or to unify a group.  The copiers share a
// free variable instead of copying it (graph/copy.cpp), so one node stands
// for one id.
//
// Finalizers.  A node that owns a foreign resource gives it back when it
// dies: the queue and the set of a SetEval node through the registries
// (next paragraph), and the Python iterator of a generator node through
// generator_release (see biGeneratorNode in builtins.hpp).  Every creator
// of a generator node registers it (gc_register_generator), and the sweep
// walks that list: a dead node that is still a generator gives its
// iterator back, and a node that was stepped (it is a forward node now, and
// the node of the rest of the list took the iterator over) leaves the list.
// The releases run last, when the heap is consistent again, because the
// release of a Python object may run Python code.
//
// Queues and sets.  A queue owns its configurations (see state/queue.hpp).
// The outermost queue of an evaluation belongs to its runtime state.  The
// queue of a set function is reached through SetEval nodes, of which there
// may be several (a copy of the node shares the queue), so the collector
// frees it: every queue and every set registers itself (graph/memory.cpp),
// the mark phase marks the queues on the stacks of the runtime states and
// the queues of the SetEval nodes it reaches, and the sets of those queues,
// of those nodes, and of the SetGuard nodes it reaches.  The sweep destroys
// the queues and the sets that are not marked.  A set guard built from
// Python may carry a number instead of a pointer (the Python backend names
// a set by a number), so a pointer read from a node counts only when the
// registry knows it.
//
// Nested evaluations.  The scheduler collects at the top of its loop, when
// no step function of its own evaluation is on the C stack.  A set function
// runs a nested scheduler inside a step of the enclosing evaluation, and so
// does an evaluation started from a Python callback.  The steps of the
// enclosing evaluation may hold nodes in C++ locals that no root reaches
// (an expression built before a case, for example).  Those nodes were
// allocated before the nested evaluation began.  So a nested collection
// treats every node of every block taken before the innermost evaluation
// began as a root (an older block; see gc/blockheap.cpp) and sweeps only
// the blocks taken since.  See gc_enter_evaluation.  The price: the mark
// phase pushes and traces every older node, so such a collection costs the
// whole heap and reclaims nothing from before the nested evaluation began.
// The scheduler of a set function therefore hands the request outward
// (E_GC, see procD), and the outermost scheduler of the state collects with
// no step of the state on the C stack.  Only an evaluation started from a
// Python callback collects nested.  The precise fix for that case is to
// make the suspended steps safe for collection, by registering their
// Variable and Cursor locals as roots while a nested evaluation runs, or by
// a conservative scan of the C stack.
//
// Threshold.  A collection runs when the number of nodes reaches the
// threshold.  The default is GC_DEFAULT_THRESHOLD; SPRITE_GC_THRESHOLD in
// the environment overrides it, and gc_set_threshold at run time.  The
// allocator checks the count once per run of slots, not per node, so a
// collection comes within one run of the threshold.  After a collection the
// threshold is the growth factor times the survivors, but not less than the
// configured value.  So the heap stays within the growth factor times the
// live nodes, and the mark cost of a collection is amortized over at least
// growth-1 times that many allocations.  A heap that only grows, as in a
// program that retains everything it computes, is marked once per factor
// of growth in size; the former policy, one doubling of the threshold per
// collection, marked it once per doubling.  The default growth factor is
// GC_DEFAULT_GROWTH; SPRITE_GC_GROWTH in the environment overrides it.
//
// A collection also runs when the live configurations reach the node
// threshold divided by GC_CONFIGURATION_DIVISOR, with the same growth rule.
// A set function consumed only in part (isEmpty, for example) leaves its
// queue, with the alternatives it has not produced yet, to the collector,
// and a configuration with its scan and its fingerprint costs several
// times a node.  Without this rule a program of many short set functions
// filled the memory with dead queues while few nodes were allocated.
//
// Stress mode.  With SPRITE_GC_STRESS=1 in the environment, the request
// flag stays set: it is set when the library loads and again at the end of
// every collection.  check_interrupts then returns E_GC after every rewrite
// step, so the scheduler reaches its safepoint after each step and collects
// there (the outermost scheduler of the state), or hands the request
// outward (a nested one).  A node that no root reaches is reclaimed at the
// next step, so a missing root shows up at once as a wrong value or a
// crash, instead of once per million nodes.  Every collection of the mode
// runs the heap verifier after its mark phase (verify_heap in
// gc/blockheap.cpp) and aborts the process when the heap is inconsistent.
// The mode costs a collection per step and is meant for the test suite (see
// tests/README).  The hot path is unchanged: the flag is the one the
// threshold sets.  gc_stress() reports the mode, and gc_num_collections()
// counts the collections.
//
// Counters.  Every collection records the seconds of its phases (the roots
// pushed, the trace, the block sweep, the registries), the nodes it marked,
// old and young apart (see the ages in gc/blockheap.cpp), the
// configurations it pushed as roots, the queues and the configurations the
// registry sweep destroyed, and the writes into old nodes counted since the
// last collection: the writes of a step into its redex (procS), the other
// pointer writes into an existing node, the distinct old nodes written, and
// the blocks touched.  The write counters cost a test per step and a call
// at the slot sites, a tenth of the instructions of Tak1 (see the TODO
// entry), so they are compiled in only under SPRITE_GC_WRITE_COUNTERS
// (make GC_WRITE_COUNTERS=1), as empty inline functions otherwise
// (memory.hpp); the macro reaches the generated modules through the ABI
// stamp (curry.backends.cxx.toolchain).  The rest of the counters are
// always on.  gc_counters() sums the records over the collections,
// gc_last_collection() holds the last one, and sprite-exec --stats prints
// the sums.  With SPRITE_GC_REPORT=1 in the environment, every collection
// prints its record on the standard error stream, one line of key=value
// pairs.  The timers cost a clock reading per queue pushed and a few per
// collection, on the collector's paths alone.

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <new>
#include <stdexcept>
#include <sstream>
#include <iomanip>
#include <iostream>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#include "cyrt/currylib/setfunctions.hpp"
#include "cyrt/state/queue.hpp"

// The next collection runs when the heap reaches this multiple of the
// survivors of the last one.  Measured on the benchmarks (see TODO): 2 and
// 4 cost time on every program with a large live set, because each
// collection also slows the evaluation that follows it (the dead nodes are
// reused in scattered order); 8 is on a par with the former doubling policy
// on PermSort and faster on QueensSet9, with a smaller bound on the heap.
#define GC_DEFAULT_GROWTH 8

// The live configurations at which a collection runs: the node threshold
// divided by this.  See the header of this file.
#define GC_CONFIGURATION_DIVISOR 8

// The configured threshold.  The adaptive policy never goes below it.  The
// threshold itself, g_threshold, is in gc/blockheap.cpp, where the allocator
// reads it.
static size_t g_threshold_floor = GC_DEFAULT_THRESHOLD;

// The growth factor of the adaptive policy.  See the header of this file.
static size_t g_growth = GC_DEFAULT_GROWTH;

// The stress mode: a collection at every safepoint.  See the header of this
// file.
static bool g_stress = false;

// The block sequence number at the start of the innermost nested
// evaluation: a block taken at or before it is older (see
// gc/blockheap.cpp).  Meaningful when g_eval_depth is above one.
static size_t g_floor_seq = 0;

static size_t g_collections = 0;

// The time spent in collections, in seconds.
static double g_seconds = 0.0;

// The counters of the collections (see the header of this file): the sums
// over the collections, and the record of the last one, which the current
// collection fills.
static cyrt::GcCounters g_totals;
static cyrt::GcCounters g_last;

// The report of every collection on the standard error stream
// (SPRITE_GC_REPORT=1).
static bool g_report = false;

using gc_clock = std::chrono::steady_clock;

static inline double seconds_since(gc_clock::time_point start)
{
  return std::chrono::duration<double>(gc_clock::now() - start).count();
}

// A request to run the verifier at the next collection (gc_verify), and
// the problem it found.
static bool g_verify_requested = false;
static std::string g_verify_problem;

static inline size_t configuration_threshold(size_t node_threshold)
{
  return std::max(size_t(1), node_threshold / GC_CONFIGURATION_DIVISOR);
}

static size_t threshold_from_environment()
{
  char const * text = std::getenv("SPRITE_GC_THRESHOLD");
  if(!text || !*text)
    return GC_DEFAULT_THRESHOLD;
  char * end = nullptr;
  unsigned long long const value = std::strtoull(text, &end, 10);
  if(end != text && *end == '\0' && value > 0)
    return (size_t) value;
  std::cerr << "SPRITE_GC_THRESHOLD=" << text
            << " is not a positive integer; using the default "
            << GC_DEFAULT_THRESHOLD << std::endl;
  return GC_DEFAULT_THRESHOLD;
}

static size_t growth_from_environment()
{
  char const * text = std::getenv("SPRITE_GC_GROWTH");
  if(!text || !*text)
    return GC_DEFAULT_GROWTH;
  char * end = nullptr;
  unsigned long long const value = std::strtoull(text, &end, 10);
  if(end != text && *end == '\0' && value >= 2)
    return (size_t) value;
  std::cerr << "SPRITE_GC_GROWTH=" << text
            << " is not an integer of at least 2; using the default "
            << GC_DEFAULT_GROWTH << std::endl;
  return GC_DEFAULT_GROWTH;
}

// A flag of the environment: 0 or empty is off, 1 is on, and another value
// is off with a warning.
static bool flag_from_environment(char const * name, char const * what)
{
  char const * text = std::getenv(name);
  if(!text || !*text || std::strcmp(text, "0") == 0)
    return false;
  if(std::strcmp(text, "1") == 0)
    return true;
  std::cerr << name << "=" << text << " is not 0 or 1; " << what << " is off"
            << std::endl;
  return false;
}

static struct _Init
{
  _Init()
  {
    cyrt::g_threshold = g_threshold_floor = threshold_from_environment();
    g_growth = growth_from_environment();
    g_stress = flag_from_environment("SPRITE_GC_STRESS", "the stress mode");
    g_report = flag_from_environment("SPRITE_GC_REPORT", "the report");
    // In stress mode the first safepoint collects already.
    g_gc_collect = g_stress;
    cyrt::g_configuration_threshold = configuration_threshold(g_threshold_floor);
  }
} _init;

namespace cyrt
{
  char const * gc_backend_name() { return "wdgc"; }
  std::vector<std::pair<std::string, double>> gc_backend_stats() { return {}; }
  size_t gc_fault_count() { return 0; }
  // This collector never moves a node, and it reaches the queue of a set
  // function through its SetEval nodes.  See graph/memory.hpp.
  GcClamp::GcClamp() {}
  GcClamp::~GcClamp() {}
  void gc_register_seteval(Node *) {}

  size_t gc_num_nodes() { return nodes_in_use(); }
  size_t gc_num_allocations() { return g_allocations - unconsumed(); }
  size_t gc_num_collections() { return g_collections; }
  double gc_seconds() { return g_seconds; }
  GcCounters const & gc_counters() { return g_totals; }
  GcCounters const & gc_last_collection() { return g_last; }
  size_t gc_threshold() { return g_threshold; }
  size_t gc_growth() { return g_growth; }
  bool gc_stress() { return g_stress; }

  void gc_set_threshold(size_t threshold)
  {
    if(threshold == 0)
      throw std::invalid_argument("the collection threshold must be positive");
    g_threshold = g_threshold_floor = threshold;
    g_configuration_threshold = configuration_threshold(threshold);
    if(nodes_in_use() >= g_threshold
        || g_num_configurations >= g_configuration_threshold)
      g_gc_collect = true;
  }

  size_t gc_enter_evaluation()
  {
    size_t const token = g_floor_seq;
    ++g_eval_depth;
    // The blocks taken so far are older than this evaluation.
    g_floor_seq = g_eval_depth == 1 ? 0 : g_heap.block_seq;
    return token;
  }

  void gc_leave_evaluation(size_t token)
  {
    assert(g_eval_depth > 0);
    --g_eval_depth;
    g_floor_seq = token;
  }

  // The generator nodes alive, or dead since the last collection.  See the
  // header of this file.  The list is never destroyed: a collection may
  // run after the static objects of this library are gone.
  static std::vector<Node *> & g_generators = *new std::vector<Node *>();

  void gc_register_generator(Node * node)
  {
    assert(node->info == &_biGenerator_Info);
    g_generators.push_back(node);
  }

  // The strict constraints read in this collection.  The configurations of
  // a fork share them (copy on write), so each table is read once; the
  // last one seen is kept apart, because the configurations of one queue
  // mostly share one table, and the check then costs no load from it.
  static std::unordered_set<void const *> g_visited_tables;
  static UnionFind const * g_last_constraints = nullptr;

  // The ids pushed by push_freevar in this collection, in a direct-mapped
  // cache: the configurations of one queue name the same few variables, so
  // most ids repeat, and a repeated id costs no lookup in the tables.  An
  // entry is valid when its stamp is the number of this collection, so the
  // cache is never cleared (a clear per collection showed in the stress
  // mode, where a collection runs per step).
  static constexpr size_t PUSHED_CACHE = 1024;
  static xid_type g_pushed[PUSHED_CACHE];
  static size_t g_pushed_stamp[PUSHED_CACHE];
  static size_t g_pushed_now = 0;

  static void clear_pushed()
  {
    ++g_pushed_now;
  }

  // Pushes the node of free variable ``vid`` from every table that has it.
  static inline void push_freevar(std::vector<Node *> & stack, xid_type vid)
  {
    size_t const index = vid % PUSHED_CACHE;
    if(g_pushed_stamp[index] == g_pushed_now && g_pushed[index] == vid)
      return;
    g_pushed_stamp[index] = g_pushed_now;
    g_pushed[index] = vid;
    for(InterpreterState * istate: g_istates)
    {
      auto p = istate->vtable.find(vid);
      if(p != istate->vtable.end())
        stack.push_back(p->second);
    }
  }

  // Pushes the nodes a queue holds: the root, the bindings, and the error
  // value of each configuration, and the free variables it names by id: its
  // residuals, the keys of its bindings, and the ids in its strict
  // constraints.  See the header of this file.
  static void push_queue_roots(std::vector<Node *> & stack, Queue * Q)
  {
    auto const start = gc_clock::now();
    for(auto * C: *Q)
    {
      ++g_last.configurations_pushed;
      if(C->root_storage)
        stack.push_back(C->root_storage);
      for(auto & pair: *C->bindings)
      {
        if(pair.second)
          stack.push_back(pair.second);
        push_freevar(stack, pair.first);
      }
      if(C->error.first)
        stack.push_back(C->error.first);
      for(xid_type vid: C->residuals)
        push_freevar(stack, vid);
      UnionFind const * constraints = C->strict_constraints.get();
      if(constraints != g_last_constraints)
      {
        g_last_constraints = constraints;
        if(!constraints->united.empty()
            && g_visited_tables.insert(constraints).second)
          for(xid_type vid: constraints->united)
            push_freevar(stack, vid);
      }
    }
    g_last.roots_seconds += seconds_since(start);
  }

  // The last queue and the last set accepted from a node.  The guards of
  // one set function share one set, so most lookups hit the cache.
  static Queue * g_last_queue = nullptr;
  static Set * g_last_set = nullptr;

  // Marks a set read from a node or a queue.  A pointer that the registry
  // does not know is ignored (see the header of this file).
  static inline void mark_set(Set * set)
  {
    if(!set)
      return;
    if(set != g_last_set)
    {
      if(!g_sets.count(set))
        return;
      g_last_set = set;
    }
    set->marked = true;
  }

  // Marks a queue read from a SetEval node and pushes its roots.
  static inline void mark_queue(std::vector<Node *> & stack, Queue * queue)
  {
    if(!queue)
      return;
    if(queue != g_last_queue)
    {
      if(!g_queues.count(queue))
        return;
      g_last_queue = queue;
    }
    queue->marked = true;
    push_queue_roots(stack, queue);
  }

  // The end of the forward chain that starts at ``node``: the first node of
  // the chain that is not a forward node.  Returns nullptr when the chain is
  // a cycle.  Marks are ignored: a node of the chain may be marked already.
  static Node * fwd_chain_end(Node * node)
  {
    Node * slow = node;
    Node * fast = node;
    while(true)
    {
      if(fast->info->tag != T_FWD) return fast;
      fast = NodeU{fast}.fwd->target;
      if(fast->info->tag != T_FWD) return fast;
      fast = NodeU{fast}.fwd->target;
      slow = NodeU{slow}.fwd->target;
      if(slow == fast) return nullptr;
    }
  }

  // Whether a node is outside the heap: the static object of a pinned info
  // table, or a literal node.  Neither is marked or swept.
  static inline bool outside_heap(Node const * node)
  {
    return is_pinned(*node->info) || in_literal_arena(node);
  }

  static void run_mark_phase(bool nested)
  {
    // The stack keeps its room between collections: in stress mode a
    // collection runs per step.
    static std::vector<Node *> stack;
    stack.clear();
    stack.reserve(100000);
    g_last_queue = nullptr;
    g_last_set = nullptr;
    g_visited_tables.clear();
    g_last_constraints = nullptr;
    clear_pushed();
    for(auto * rts: g_rtslist)
    {
      for(auto * Q: rts->qstack)
      {
        Q->marked = true;
        push_queue_roots(stack, Q);
      }
    }
    auto const start = gc_clock::now();
    for(auto const & pair: g_roots)
      stack.push_back(pair.first);
    // In a nested evaluation, every node of an older block is a root.  See
    // the comment at the top of this file.
    if(nested)
      push_older_nodes(stack, g_floor_seq);
    g_last.roots_seconds += seconds_since(start);
    while(!stack.empty())
    {
      Node * node = stack.back();
      stack.pop_back();
      // A literal node is outside this heap: it has no successors and is
      // never marked or swept (see graph/memory.cpp).  So is a pinned
      // static object.
      if(outside_heap(node) || heap_marked(node))
        continue;
      ++g_last.marked;
      if(heap_mark_and_age(node))
        ++g_last.marked_old;
      else
        ++g_last.marked_young;
      if(g_verifying)
        g_verify_list.push_back(node);
      auto * info = node->info;
      if(info->tag == T_FWD)
      {
        // Point the node at the end of its chain, as compress_fwd_chain does
        // during evaluation.  The nodes between are then reclaimed, unless
        // something else holds them.  Without this, a forwarded node that
        // is a root (a node Python holds, or a node from before a nested
        // evaluation) keeps every redex of a long tail recursion alive.
        Node * end = fwd_chain_end(node);
        if(end)
        {
          NodeU{node}.fwd->target = end;
          stack.push_back(end);
          continue;
        }
      }
      if(info == &SetEval_Info)
      {
        SetEvalNode * seteval = NodeU{node}.seteval;
        mark_queue(stack, seteval->queue);
        mark_set(seteval->set);
      }
      else if(info->tag == T_SETGRD)
        mark_set(NodeU{node}.setgrd->set);
      auto data = node->begin();
      for(index_type i=0, e=info->arity; i<e; ++i)
        if(info->format[i] == 'p' && data[i].node)
          stack.push_back(data[i].node);
    }
  }

  // Drops the entries of the free-variable tables whose node the mark phase
  // did not reach.  Runs after the mark phase and before the sweep, which
  // frees those nodes.  See the header of this file.
  static void sweep_freevar_tables()
  {
    for(InterpreterState * istate: g_istates)
    {
      vtable_type & table = istate->vtable;
      for(auto p = table.begin(); p != table.end();)
      {
        if(heap_marked(p->second))
          ++p;
        else
          p = table.erase(p);
      }
    }
  }

  // The Python iterators of the generator nodes the sweep freed.  They are
  // released after the collection (release_pending).
  static std::vector<void *> g_pending_releases;

  // Releases the iterators of the generator nodes the sweep freed.  The list
  // is taken first: a release may run Python code, which may start an
  // evaluation and a nested collection.
  static void release_pending()
  {
    if(g_pending_releases.empty())
      return;
    std::vector<void *> pending;
    pending.swap(g_pending_releases);
    for(void * data: pending)
      generator_release(data);
  }

  // Walks the generator nodes: a dead generator gives its iterator back,
  // and a node that is no longer a generator leaves the list.  Runs after
  // the mark phase and before the sweep.  See the header of this file.
  static void sweep_generators()
  {
    size_t kept = 0;
    for(Node * node: g_generators)
    {
      if(node->info != &_biGenerator_Info)
        continue;
      if(heap_marked(node))
        g_generators[kept++] = node;
      else
        g_pending_releases.push_back(NodeU{node}.generator->data);
    }
    g_generators.resize(kept);
  }

  // Destroys the queues and the sets the mark phase did not reach, and
  // clears the marks of the rest.  A queue goes with its configurations,
  // whose nodes the node sweep freed already (a dead queue is reached by no
  // root).  The sets go after the queues, because a queue that stays keeps
  // its set.  An entry is taken out of its registry before the object is
  // destroyed, so the destructor finds nothing to unregister and the
  // iteration stays valid.
  static void run_registry_sweep()
  {
    // A queue destroys its configurations, which count themselves out.
    size_t const configurations = g_num_configurations;
    for(auto p = g_queues.begin(); p != g_queues.end();)
    {
      Queue * queue = *p;
      if(queue->marked)
      {
        queue->marked = false;
        if(queue->set)
          queue->set->marked = true;
        ++p;
      }
      else
      {
        p = g_queues.erase(p);
        delete queue;
        ++g_last.queues_destroyed;
      }
    }
    g_last.configurations_destroyed += configurations - g_num_configurations;
    for(auto p = g_sets.begin(); p != g_sets.end();)
    {
      Set * set = *p;
      if(set->marked)
      {
        set->marked = false;
        ++p;
      }
      else
      {
        p = g_sets.erase(p);
        delete set;
      }
    }
    g_last_queue = nullptr;
    g_last_set = nullptr;
  }

  #ifndef NDEBUG
  // At a safepoint, every live configuration is in a registered queue, and
  // the holders of each are the queues it is in.
  static bool live_configurations_are_queued()
  {
    std::unordered_map<Configuration *, size_t> queued;
    for(Queue * queue: g_queues)
      for(Configuration * C: *queue)
        ++queued[C];
    if(queued.size() != g_num_configurations)
      return false;
    for(auto const & pair: queued)
      if(pair.first->holders != pair.second)
        return false;
    return true;
  }
  #endif

  // Adds the record of a collection to the sums.
  static void add_counters(GcCounters & sum, GcCounters const & record)
  {
    sum.roots_seconds += record.roots_seconds;
    sum.trace_seconds += record.trace_seconds;
    sum.sweep_seconds += record.sweep_seconds;
    sum.registries_seconds += record.registries_seconds;
    sum.marked += record.marked;
    sum.marked_old += record.marked_old;
    sum.marked_young += record.marked_young;
    sum.configurations_pushed += record.configurations_pushed;
    sum.queues_destroyed += record.queues_destroyed;
    sum.configurations_destroyed += record.configurations_destroyed;
    sum.old_redexes += record.old_redexes;
    sum.old_slot_writes += record.old_slot_writes;
    sum.old_nodes_written += record.old_nodes_written;
    sum.old_blocks += record.old_blocks;
  }

  // The line of SPRITE_GC_REPORT: the record of a collection as key=value
  // pairs, with the state of the heap around it.
  static void report_collection(
      size_t nodes_before, size_t survivors, double seconds
    )
  {
    GcCounters const & c = g_last;
    std::stringstream ss;
    ss << std::fixed << std::setprecision(6)
       << "gc collection=" << g_collections
       << " nested=" << (g_eval_depth > 1)
       << " nodes=" << nodes_before
       << " survivors=" << survivors
       << " marked=" << c.marked
       << " marked_old=" << c.marked_old
       << " marked_young=" << c.marked_young
       << " roots_seconds=" << c.roots_seconds
       << " trace_seconds=" << c.trace_seconds
       << " sweep_seconds=" << c.sweep_seconds
       << " registries_seconds=" << c.registries_seconds
       << " configurations_pushed=" << c.configurations_pushed
       << " queues_destroyed=" << c.queues_destroyed
       << " configurations_destroyed=" << c.configurations_destroyed
       << " old_redexes=" << c.old_redexes
       << " old_slot_writes=" << c.old_slot_writes
       << " old_nodes_written=" << c.old_nodes_written
       << " old_blocks=" << c.old_blocks
       << " threshold=" << g_threshold
       << " configurations=" << g_num_configurations
       << " queues=" << g_queues.size()
       << " sets=" << g_sets.size()
       << " blocks=" << gc_num_blocks()
       << " seconds=" << seconds
       << "\n";
    (std::cerr << ss.str()).flush();
  }

  void run_gc()
  {
    auto const start = gc_clock::now();
    bool const nested = g_eval_depth > 1;
    size_t const nodes_before = g_report ? nodes_in_use() : 0;
    retire_runs();
    g_verifying = g_stress || g_verify_requested;
    g_verify_list.clear();
    // The record of this collection.  The write counters of the interval
    // come from the heap (gc/blockheap.cpp) and start over.
    g_last = GcCounters();
    g_last.old_redexes = g_old_redexes;
    g_last.old_slot_writes = g_old_slot_writes;
    g_old_redexes = g_old_slot_writes = 0;
    auto const mark_start = gc_clock::now();
    run_mark_phase(nested);
    // The roots pushed inside the trace (the queue of a SetEval node) are
    // in roots_seconds; the rest of the mark phase is the trace.
    g_last.trace_seconds = seconds_since(mark_start) - g_last.roots_seconds;
    auto const tables_start = gc_clock::now();
    sweep_freevar_tables();
    sweep_generators();
    g_last.registries_seconds += seconds_since(tables_start);
    if(g_verifying)
    {
      // The stress mode checks the bitmaps of every block as well: an
      // error of the sweep (an old bit kept on a free slot, a block pooled
      // with a bit set) surfaces at the next collection, not at the end of
      // a test that asks for it.
      std::string const problem = verify_heap(true);
      g_verify_list.clear();
      g_verifying = false;
      if(g_verify_requested)
        g_verify_problem = problem;
      else if(!problem.empty())
      {
        std::cerr << "the heap verifier found " << problem << std::endl;
        std::abort();
      }
    }
    auto const sweep_start = gc_clock::now();
    size_t const survivors = sweep_blocks(nested, g_floor_seq);
    g_last.sweep_seconds = seconds_since(sweep_start);
    g_last.old_nodes_written = g_old_nodes_written;
    g_last.old_blocks = g_old_blocks;
    auto const registries_start = gc_clock::now();
    run_registry_sweep();
    g_last.registries_seconds += seconds_since(registries_start);
    assert(live_configurations_are_queued());
    ++g_collections;
    g_threshold = std::max(g_threshold_floor, g_growth * survivors);
    g_configuration_threshold = std::max(
        configuration_threshold(g_threshold_floor)
      , g_growth * g_num_configurations
      );
    double const seconds = seconds_since(start);
    g_seconds += seconds;
    add_counters(g_totals, g_last);
    if(g_report)
      report_collection(nodes_before, survivors, seconds);
    // In stress mode the next safepoint collects again.
    g_gc_collect = g_stress;
    release_pending();
  }

  std::string gc_verify()
  {
    if(g_eval_depth != 0)
      throw std::runtime_error(
          "cannot run the collector while an evaluation is active"
        );
    g_verify_requested = true;
    g_verify_problem.clear();
    try
    {
      run_gc();
    }
    catch(...)
    {
      g_verify_requested = false;
      throw;
    }
    g_verify_requested = false;
    return g_verify_problem;
  }
}
