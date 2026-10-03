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
// Nested evaluations.  The scheduler collects at the top of its loop, when
// no step function of its own evaluation is on the C stack.  A set function
// runs a nested scheduler inside a step of the enclosing evaluation, and so
// does an evaluation started from a Python callback.  The steps of the
// enclosing evaluation may hold nodes in C++ locals that no root reaches
// (an expression built before a case, for example).  Those nodes were
// allocated before the nested evaluation began.  So a nested collection
// treats every node allocated before the innermost evaluation began as a
// root and sweeps only the nodes allocated since.  See gc_enter_evaluation.
// The price: the mark phase pushes and traces every older node, so a
// collection inside a set function costs the whole heap, and no garbage
// from before the set function began is reclaimed until it returns.  A
// program that spends its time in set functions over a large heap gains
// little from the collector.  The precise fix is to make the suspended
// steps safe for collection, by registering their Variable and Cursor
// locals as roots while a nested evaluation runs.
//
// Threshold.  A collection runs when the number of nodes reaches the
// threshold.  The default is GC_DEFAULT_THRESHOLD; SPRITE_GC_THRESHOLD in
// the environment overrides it, and gc_set_threshold at run time.  After a
// collection the threshold is GC_GROWTH times the survivors, but not less
// than the configured value.  So the heap stays within GC_GROWTH times the
// live nodes, and the mark cost of a collection is amortized over at least
// GC_GROWTH-1 times that many allocations.  A heap that only grows, as in a
// program that retains everything it computes, is marked once per factor of
// GC_GROWTH in size; the former policy, one doubling of the threshold per
// collection, marked it once per doubling.

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <new>
#include <stdexcept>
#include <sstream>
#include <iomanip>
#include <iostream>
#include <vector>
#include "cyrt/currylib/setfunctions.hpp"

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
#define GC_GROWTH 8
#define MARKBIT 0x8000000000000000
#define INFO(node) ((InfoTable *)(((uintptr_t) node->info) & ~MARKBIT))

struct Entry
{
  void * addr;
  size_t bytes;
};

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

// The index in g_addr of the first node allocated by the innermost
// evaluation.  A collection sweeps from here.  Zero outside an evaluation
// and in an outermost one.
static size_t g_sweep_floor = 0;

static size_t g_collections = 0;

// The time spent in collections, in seconds.
static double g_seconds = 0.0;

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

static struct _Init
{
  _Init()
  {
    g_threshold = g_threshold_floor = threshold_from_environment();
    // Reserve the address list up to 16 MB, so that it does not grow
    // during the first collection cycle.
    g_addr.reserve(std::min(g_threshold, size_t(1) << 20));
  }
} _init;

namespace cyrt
{
  Node * node_reserve(size_t bytes)
  {
    bytes = round_up(bytes);
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
    return (Node *) addr;
  }

  bool node_commit(void * addr, size_t bytes)
  {
    return true;
  }

  size_t gc_num_nodes() { return g_addr.size(); }
  size_t gc_num_collections() { return g_collections; }
  double gc_seconds() { return g_seconds; }
  size_t gc_threshold() { return g_threshold; }

  void gc_set_threshold(size_t threshold)
  {
    if(threshold == 0)
      throw std::invalid_argument("the collection threshold must be positive");
    g_threshold = g_threshold_floor = threshold;
    if(g_addr.size() >= g_threshold)
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
    if(!Q)
      return;
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
    std::vector<Node *> stack;
    stack.reserve(100000);
    for(auto * rts: g_rtslist)
    {
      for(auto * Q: rts->qstack)
        push_queue_roots(stack, Q);
      for(auto pair: rts->vtable)
        if(pair.second)
          stack.push_back(pair.second);
    }
    for(auto const & pair: g_roots)
      stack.push_back(pair.first);
    // In a nested evaluation, every node allocated before it began is a
    // root.  See the comment at the top of this file.
    for(size_t i=0; i<g_sweep_floor; ++i)
      stack.push_back((Node *) g_addr[i].addr);
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
        push_queue_roots(stack, NodeU{node}.seteval->queue);
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
      Node * node = (Node *) g_addr[i].addr;
      if(is_marked(node))
        clear(node);
    }
    auto p = g_addr.begin() + g_sweep_floor;
    auto q = p;
    auto const e = g_addr.end();
    while(q != e)
    {
      Node * node = (Node *) q->addr;
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
      Node * node = (Node *) entry.addr;
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
    #endif
    run_sweep_phase();
    ++g_collections;
    g_threshold = std::max(g_threshold_floor, GC_GROWTH * g_addr.size());
    g_seconds += std::chrono::duration<double>(
        std::chrono::steady_clock::now() - start
      ).count();
    #ifdef GC_REPORT
    (std::cerr << g_addr.size() << "/" << g_threshold << "\n").flush();
    #endif
    g_gc_collect = false;
  }
}
