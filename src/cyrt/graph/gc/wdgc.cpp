// The world's dumbest garbage collector.  The address and size of every node
// allocated is stored in a vector.  When collection runs, it does a
// mark-and-sweep pass over that list.  There are no generations and nothing
// is moved.
//
// Allocation.  Nodes of up to POOL_MAX bytes come from free lists, one per
// size (a multiple of 8 bytes), and the sweep returns dead nodes to those
// lists instead of to malloc.  That keeps the sweep cheap, and the next
// allocations reuse adjacent addresses in runs, in the order the sweep
// found them.  Measured on the PermSort benchmark, reuse through malloc
// made the evaluation 75 percent slower after the first collection; the
// free lists remove that.  Memory in the free lists is not returned to the
// system.  Larger nodes use malloc and free.
//
// Roots.  The queues of every runtime state (the root, the bindings, and the
// error value of each configuration), the free-variable tables, the nodes
// registered with gc_add_root (the nodes Python holds), and the queue of
// every SetEval node reached: a lazy set function keeps the alternatives it
// has not produced yet in that queue, which is reachable only through the
// node.
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
// treats every node allocated before the innermost evaluation began as a
// root and sweeps only the nodes allocated since.  See gc_enter_evaluation.
// The price: the mark phase pushes and traces every older node, so such a
// collection costs the whole heap and reclaims nothing from before the
// nested evaluation began.  The scheduler of a set function therefore hands
// the request outward (E_GC, see procD), and the outermost scheduler of
// the state collects with no step of the state on the C stack.  Only an
// evaluation started from a Python callback collects nested.  The precise
// fix for that case is to make the suspended steps safe for collection, by
// registering their Variable and Cursor locals as roots while a nested
// evaluation runs.
//
// Threshold.  A collection runs when the number of nodes reaches the
// threshold.  The default is GC_DEFAULT_THRESHOLD; SPRITE_GC_THRESHOLD in
// the environment overrides it, and gc_set_threshold at run time.  After a
// collection the threshold is the growth factor times the survivors, but
// not less than the configured value.  So the heap stays within the growth
// factor times the live nodes, and the mark cost of a collection is
// amortized over at least growth-1 times that many allocations.  A heap
// that only grows, as in a program that retains everything it computes, is
// marked once per factor of growth in size; the former policy, one doubling
// of the threshold per collection, marked it once per doubling.  The
// default growth factor is GC_DEFAULT_GROWTH; SPRITE_GC_GROWTH in the
// environment overrides it.
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
// crash, instead of once per million nodes.  The mode costs a collection
// per step and is meant for the test suite (see tests/README).  The hot
// path is unchanged: the flag is the one the threshold sets.  gc_stress()
// reports the mode, and gc_num_collections() counts the collections.

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
#include <vector>
#include "cyrt/currylib/setfunctions.hpp"
#include "cyrt/state/queue.hpp"

// #define GC_REPORT

// The number of live nodes at which the collector runs, unless the
// environment says otherwise.  At about 50 bytes per node (the node, the
// allocator's overhead, and the address entry), this is about 50 MB.
#define GC_DEFAULT_THRESHOLD (size_t(1) << 20)

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
#define MARKBIT 0x8000000000000000
#define INFO(node) ((InfoTable *)(((uintptr_t) node->info) & ~MARKBIT))

// The block of one node: its address and its size, both of the whole block.
// In an instrumented build (see below) the block starts with the creator
// word, and the node follows it.
struct Entry
{
  void * addr;
  size_t bytes;
};

// The scheduler counters (cyrt/state/counters.hpp) ask which configuration
// created a node.  An instrumented build keeps that in the word before every
// node: node_reserve allocates NODE_PREFIX bytes more, writes the serial
// number the scheduler set (g_creator_serial), and returns the address after
// it.  The entries, the free lists, and malloc see the whole block.  A plain
// build has no prefix, and the node is the block.
#ifdef SPRITE_SCHEDULER_COUNTERS
static constexpr size_t NODE_PREFIX = sizeof(size_t);
#else
static constexpr size_t NODE_PREFIX = 0;
#endif

static inline cyrt::Node * entry_node(Entry const & entry)
  { return (cyrt::Node *) ((char *) entry.addr + NODE_PREFIX); }

static std::vector<Entry> g_addr;

// Nodes of up to this many bytes come from the free lists.
static constexpr size_t POOL_MAX = 512;
static void * g_freelist[POOL_MAX / 8 + 1];

static inline size_t round_up(size_t bytes) { return (bytes + 7) & ~size_t(7); }

static inline void * take_memory(size_t bytes)
{
  if(bytes <= POOL_MAX)
  {
    void *& head = g_freelist[bytes / 8];
    if(head)
    {
      void * addr = head;
      head = *(void **) addr;
      return addr;
    }
  }
  return std::malloc(bytes);
}

static inline void give_memory(void * addr, size_t bytes)
{
  if(bytes <= POOL_MAX)
  {
    void *& head = g_freelist[bytes / 8];
    *(void **) addr = head;
    head = addr;
  }
  else
    std::free(addr);
}

// The number of live objects at which point GC should run.
static size_t g_threshold = GC_DEFAULT_THRESHOLD;

// The configured threshold.  The adaptive policy never goes below it.
static size_t g_threshold_floor = GC_DEFAULT_THRESHOLD;

// The growth factor of the adaptive policy.  See the header of this file.
static size_t g_growth = GC_DEFAULT_GROWTH;

// The stress mode: a collection at every safepoint.  See the header of this
// file.
static bool g_stress = false;

// The index in g_addr of the first node allocated by the innermost
// evaluation.  A collection sweeps from here.  Zero outside an evaluation
// and in an outermost one.
static size_t g_sweep_floor = 0;

static size_t g_collections = 0;

// The time spent in collections, in seconds.
static double g_seconds = 0.0;

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

static bool stress_from_environment()
{
  char const * text = std::getenv("SPRITE_GC_STRESS");
  if(!text || !*text || std::strcmp(text, "0") == 0)
    return false;
  if(std::strcmp(text, "1") == 0)
    return true;
  std::cerr << "SPRITE_GC_STRESS=" << text
            << " is not 0 or 1; the stress mode is off" << std::endl;
  return false;
}

static struct _Init
{
  _Init()
  {
    g_threshold = g_threshold_floor = threshold_from_environment();
    g_growth = growth_from_environment();
    g_stress = stress_from_environment();
    // In stress mode the first safepoint collects already.
    g_gc_collect = g_stress;
    cyrt::g_configuration_threshold = configuration_threshold(g_threshold_floor);
    // Reserve the address list up to 16 MB, so that it does not grow
    // during the first collection cycle.
    g_addr.reserve(std::min(g_threshold, size_t(1) << 20));
  }
} _init;

namespace cyrt
{
  #ifdef SPRITE_SCHEDULER_COUNTERS
  size_t g_creator_serial = 0;
  #endif

  Node * node_reserve(size_t bytes)
  {
    bytes = round_up(bytes) + NODE_PREFIX;
    void * addr = take_memory(bytes);
    // Out of memory.  The exception leaves the step functions and the
    // scheduler; pybind11 turns it into MemoryError.
    if(!addr)
      throw std::bad_alloc();
    try
    {
      g_addr.push_back(Entry{addr, bytes});
    }
    catch(...)
    {
      give_memory(addr, bytes);
      throw;
    }
    if(g_addr.size() >= g_threshold)
      g_gc_collect = true;
    #ifdef SPRITE_SCHEDULER_COUNTERS
    *(size_t *) addr = g_creator_serial;
    #endif
    return (Node *) ((char *) addr + NODE_PREFIX);
  }

  bool node_commit(void * addr, size_t bytes)
  {
    return true;
  }

  size_t gc_num_nodes() { return g_addr.size(); }
  size_t gc_num_collections() { return g_collections; }
  double gc_seconds() { return g_seconds; }
  size_t gc_threshold() { return g_threshold; }
  size_t gc_growth() { return g_growth; }
  bool gc_stress() { return g_stress; }

  void gc_set_threshold(size_t threshold)
  {
    if(threshold == 0)
      throw std::invalid_argument("the collection threshold must be positive");
    g_threshold = g_threshold_floor = threshold;
    g_configuration_threshold = configuration_threshold(threshold);
    if(g_addr.size() >= g_threshold
        || g_num_configurations >= g_configuration_threshold)
      g_gc_collect = true;
  }

  size_t gc_enter_evaluation()
  {
    size_t const token = g_sweep_floor;
    ++g_eval_depth;
    g_sweep_floor = g_eval_depth == 1 ? 0 : g_addr.size();
    return token;
  }

  void gc_leave_evaluation(size_t token)
  {
    assert(g_eval_depth > 0);
    --g_eval_depth;
    // A nested collection compacts the list from its own floor, which is
    // not below the floor of the enclosing evaluation.  The token is valid.
    g_sweep_floor = token;
  }

  static inline void mark(Node * node)
  {
    assert(!is_pinned(*INFO(node)));
    uintptr_t ptr_value = (std::uintptr_t) node->info;
    ptr_value |= MARKBIT;
    node->info = (InfoTable *) ptr_value;
  }

  static inline void clear(Node * node)
  {
    assert(!is_pinned(*INFO(node)));
    uintptr_t ptr_value = (std::uintptr_t) node->info;
    ptr_value &= ~MARKBIT;
    node->info = (InfoTable *) ptr_value;
  }

  static inline bool is_marked(Node * node)
  {
    uintptr_t ptr_value = (std::uintptr_t) node->info;
    return ptr_value & MARKBIT;
  }

  static inline bool is_marked_or_pinned(Node * node)
  {
    return is_marked(node) || is_pinned(*node->info);
  }

  // Pushes the nodes a queue holds: the root, the bindings, and the error
  // value of each configuration.
  static void push_queue_roots(std::vector<Node *> & stack, Queue * Q)
  {
    for(auto * C: *Q)
    {
      if(C->root_storage)
        stack.push_back(C->root_storage);
      for(auto & pair: *C->bindings)
        if(pair.second)
          stack.push_back(pair.second);
      if(C->error.first)
        stack.push_back(C->error.first);
    }
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
      if(INFO(fast)->tag != T_FWD) return fast;
      fast = NodeU{fast}.fwd->target;
      if(INFO(fast)->tag != T_FWD) return fast;
      fast = NodeU{fast}.fwd->target;
      slow = NodeU{slow}.fwd->target;
      if(slow == fast) return nullptr;
    }
  }

  static void run_mark_phase()
  {
    // The stack keeps its room between collections: in stress mode a
    // collection runs per step.
    static std::vector<Node *> stack;
    stack.clear();
    stack.reserve(100000);
    g_last_queue = nullptr;
    g_last_set = nullptr;
    #ifdef GC_REPORT
    size_t vtable_entries = 0, vtable_nodes = 0;
    auto const t0 = std::chrono::steady_clock::now();
    #endif
    for(auto * rts: g_rtslist)
    {
      for(auto * Q: rts->qstack)
      {
        Q->marked = true;
        push_queue_roots(stack, Q);
      }
      for(auto pair: rts->vtable)
        if(pair.second)
          stack.push_back(pair.second);
      #ifdef GC_REPORT
      vtable_entries += rts->vtable.size();
      for(auto pair: rts->vtable)
        if(pair.second) ++vtable_nodes;
      #endif
    }
    #ifdef GC_REPORT
    auto const t1 = std::chrono::steady_clock::now();
    (std::cerr << "roots=" << stack.size() << " vtable=" << vtable_entries
               << "/" << vtable_nodes << " pyroots=" << g_roots.size()
               << " rootsecs=" << std::chrono::duration<double>(t1 - t0).count()
               << " ").flush();
    #endif
    for(auto const & pair: g_roots)
      stack.push_back(pair.first);
    // In a nested evaluation, every node allocated before it began is a
    // root.  See the comment at the top of this file.
    for(size_t i=0; i<g_sweep_floor; ++i)
      stack.push_back(entry_node(g_addr[i]));
    while(!stack.empty())
    {
      Node * node = stack.back();
      stack.pop_back();
      if(is_marked_or_pinned(node))
        continue;
      else
        mark(node);
      auto * info = INFO(node);
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

  static void run_sweep_phase()
  {
    // The nodes below the floor stay.  Clear their marks.
    for(size_t i=0; i<g_sweep_floor; ++i)
    {
      Node * node = entry_node(g_addr[i]);
      if(is_marked(node))
        clear(node);
    }
    auto p = g_addr.begin() + g_sweep_floor;
    auto q = p;
    auto const e = g_addr.end();
    while(q != e)
    {
      Node * node = entry_node(*q);
      if(is_marked(node))
      {
        clear(node);
        *p++ = *q++;
      }
      else
      {
        give_memory(q->addr, q->bytes);
        ++q;
      }
    }
    g_addr.resize(p - g_addr.begin());
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
      }
    }
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

  // static void show_nodes(bool show)
  // {
  //   for(auto entry: g_addr)
  //   {
  //     Node * node = (Node *) entry.addr;
  //     char const m = is_marked(node) ? 'M' : 'u';
  //     if(m == 'M') clear(node);
  //     if(node->info->tag == T_FWD)
  //       std::cerr << "    " << node << " " << m << " -> " << NodeU{node}.fwd->target;
  //     else
  //     {
  //       std::cerr << "    " << node << " " << m << " ";
  //       if(show)
  //         std::cerr << node->str(PLAIN_FREEVARS);
  //     }
  //     if(m == 'M') mark(node);
  //     std::cerr << std::endl;
  //   }
  // }

  #ifdef GC_REPORT
  static size_t count_marks()
  {
    size_t n_marked = 0;
    for(auto entry: g_addr)
    {
      Node * node = entry_node(entry);
      if(is_marked(node))
        n_marked++;
    }
    return n_marked;
  }

  static std::string show_frac(float frac)
  {
    std::stringstream ss;
    ss << std::fixed << std::setprecision(1) << frac;
    return ss.str();
  }
  #endif

  void run_gc()
  {
    auto const start = std::chrono::steady_clock::now();
    #ifdef GC_REPORT
    (std::cerr << "GC " << g_addr.size() << "/" << g_threshold
               << " floor=" << g_sweep_floor << " depth=" << g_eval_depth
               << " ").flush();
    // show_nodes(true);
    #endif
    run_mark_phase();
    // show_nodes(false);
    #ifdef GC_REPORT
    size_t n_marked = count_marks();
    float frac_used = 100.f * n_marked / (float) g_addr.size();
    (std::cerr << show_frac(frac_used) << "% ").flush();
    auto const marked = std::chrono::steady_clock::now();
    #endif
    run_sweep_phase();
    #ifdef GC_REPORT
    auto const swept = std::chrono::steady_clock::now();
    #endif
    run_registry_sweep();
    #ifdef GC_REPORT
    auto const done = std::chrono::steady_clock::now();
    using fsec = std::chrono::duration<double>;
    (std::cerr << "mark=" << fsec(marked - start).count()
               << " sweep=" << fsec(swept - marked).count()
               << " registries=" << fsec(done - swept).count() << " ").flush();
    #endif
    assert(live_configurations_are_queued());
    ++g_collections;
    g_threshold = std::max(g_threshold_floor, g_growth * g_addr.size());
    g_configuration_threshold = std::max(
        configuration_threshold(g_threshold_floor)
      , g_growth * g_num_configurations
      );
    g_seconds += std::chrono::duration<double>(
        std::chrono::steady_clock::now() - start
      ).count();
    #ifdef GC_REPORT
    (std::cerr << g_addr.size() << "/" << g_threshold
               << " configurations=" << g_num_configurations
               << " queues=" << g_queues.size()
               << " sets=" << g_sets.size()
               << " seconds=" << g_seconds << "\n").flush();
    #endif
    // In stress mode the next safepoint collects again.
    g_gc_collect = g_stress;
  }
}
