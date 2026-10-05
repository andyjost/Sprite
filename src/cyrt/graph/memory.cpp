#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include "cyrt/graph/cursor.hpp"
#include "cyrt/graph/memory.hpp"
#include "cyrt/state/queue.hpp"
#include "cyrt/state/rts.hpp"
#include <new>
#include <set>
#include <stdexcept>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace cyrt
{
  Arg const * pack(char * out, char const *format, Arg const * args)
  {
    RawNodeMemory mem{out};
    for(; *format; ++format)
    {
      switch(*format)
      {
        case 'p':
          *mem.boxed++ = *(Node **)(args++);
          break;
        case 'i':
          *mem.ub_int++ = *(unboxed_int_type*)(args++);
          break;
        case 'f':
          *mem.ub_float++ = *(unboxed_float_type*)(args++);
          break;
        case 'c':
          *mem.ub_char++ = *(unboxed_char_type*)(args++);
          break;
        case 'x':
          *mem.ub_ptr++ = *(unboxed_ptr_type*)(args++);
          break;
        default: assert(0);
      }
    }
    return args;
  }

  size_t packed_size(char const *format, size_t limit)
  {
    size_t size=0;
    for(size_t i=0; *format && i<limit; ++format, ++i)
    {
      switch(*format)
      {
        case 'p':
          size += sizeof(Node *);
          break;
        case 'i':
          size += sizeof(unboxed_int_type);
          break;
        case 'f':
          size += sizeof(unboxed_float_type);
          break;
        case 'c':
          size += sizeof(unboxed_char_type);
          break;
        case 'x':
          size += sizeof(unboxed_ptr_type);
          break;
        default: assert(0);
      }
    }
    return size;
  }

  static std::set<RuntimeState *> g_rtslist;
  bool g_gc_collect = false;

  // The nodes Python holds, with the number of registrations of each.  The
  // map is never destroyed: a wrapper may be destroyed after the static
  // objects of this library.
  using RootMap = std::unordered_map<Node *, size_t>;
  static RootMap & g_roots = *new RootMap();

  // The number of evaluations on the C stack.  See gc_enter_evaluation.
  static size_t g_eval_depth = 0;

  void gc_register_rts(RuntimeState * rts)
  {
    assert(rts);
    assert(g_rtslist.count(rts) == 0);
    g_rtslist.insert(rts);
  }

  void gc_unregister_rts(RuntimeState * rts)
  {
    assert(rts);
    g_rtslist.erase(rts);
    assert(g_rtslist.count(rts) == 0);
  }

  // The interpreter states alive.  The list is never destroyed: a state
  // held by Python may be destroyed after the static objects of this
  // library.
  static std::vector<InterpreterState *> & g_istates
      = *new std::vector<InterpreterState *>();

  void gc_register_istate(InterpreterState * istate)
  {
    assert(istate);
    assert(
        std::find(g_istates.begin(), g_istates.end(), istate)
        == g_istates.end()
      );
    g_istates.push_back(istate);
  }

  void gc_unregister_istate(InterpreterState * istate)
  {
    auto p = std::find(g_istates.begin(), g_istates.end(), istate);
    if(p != g_istates.end())
      g_istates.erase(p);
  }

  size_t gc_num_freevars()
  {
    size_t count = 0;
    for(InterpreterState * istate: g_istates)
      count += istate->vtable.size();
    return count;
  }

  void gc_add_root(Node * node)
  {
    assert(node);
    ++g_roots[node];
  }

  void gc_remove_root(Node * node)
  {
    auto p = g_roots.find(node);
    assert(p != g_roots.end());
    if(p == g_roots.end())
      return;
    if(--p->second == 0)
      g_roots.erase(p);
  }

  size_t gc_root_count(Node * node)
  {
    auto p = g_roots.find(node);
    return p == g_roots.end() ? 0 : p->second;
  }

  size_t gc_num_roots()
  {
    return g_roots.size();
  }

  // The arena of the literal nodes (see memory.hpp): one block, taken from
  // malloc at the first request and never returned.  The pages are committed
  // as they are touched.  The objects here are constant-initialized, so a
  // literal node may be made during the static initialization of this
  // library (the tables of builtins.cpp are).  In an instrumented build a
  // literal node has no creator (node_creator answers zero by the address).
  static char * g_literal_arena = nullptr;
  static size_t g_literal_used = 0;
  static size_t g_num_literals = 0;

  // Whether ``p`` points into a block of the arena.  The mark phase of the
  // collector asks this for every node it would mark.
  static inline bool in_literal_arena(void const * p)
  {
    return (uintptr_t) p - (uintptr_t) g_literal_arena < g_literal_used;
  }

  Node * literal_reserve(size_t bytes)
  {
    bytes = round_up(bytes);
    if(!g_literal_arena)
    {
      g_literal_arena = (char *) std::malloc(LITERAL_ARENA_BYTES);
      if(!g_literal_arena)
        throw std::bad_alloc();
    }
    if(LITERAL_ARENA_BYTES - g_literal_used < bytes)
      throw std::runtime_error("the arena of the literal nodes is full");
    char * addr = g_literal_arena + g_literal_used;
    g_literal_used += bytes;
    ++g_num_literals;
    return (Node *) addr;
  }

  bool gc_is_literal(Node const * node)
  {
    return in_literal_arena(node);
  }

  size_t gc_num_literals()
  {
    return g_num_literals;
  }

  size_t gc_eval_depth()
  {
    return g_eval_depth;
  }

  // The queues and the sets alive.  The registries are never destroyed: a
  // runtime state held by Python may be destroyed after the static objects
  // of this library.
  static std::unordered_set<Queue *> & g_queues = *new std::unordered_set<Queue *>();
  static std::unordered_set<Set *> & g_sets = *new std::unordered_set<Set *>();

  // The configurations alive, and the count at which a collection is
  // requested.  The collector sets the threshold (see gc/wdgc.cpp).
  static size_t g_num_configurations = 0;
  static size_t g_configuration_threshold = NOLIMIT;

  void gc_configuration_created()
  {
    if(++g_num_configurations >= g_configuration_threshold)
      g_gc_collect = true;
  }

  void gc_configuration_destroyed()
  {
    assert(g_num_configurations > 0);
    --g_num_configurations;
  }

  void gc_register_queue(Queue * queue)
  {
    assert(queue);
    g_queues.insert(queue);
  }

  void gc_unregister_queue(Queue * queue)
  {
    g_queues.erase(queue);
  }

  void gc_register_set(Set * set)
  {
    assert(set);
    g_sets.insert(set);
  }

  void gc_unregister_set(Set * set)
  {
    g_sets.erase(set);
  }

  size_t gc_num_configurations() { return g_num_configurations; }
  size_t gc_num_queues() { return g_queues.size(); }
  size_t gc_num_sets() { return g_sets.size(); }

  std::vector<size_t> gc_queue_lengths()
  {
    std::vector<size_t> lengths;
    lengths.reserve(g_queues.size());
    for(Queue * queue: g_queues)
      lengths.push_back(queue->size());
    return lengths;
  }
}

// The heap and the collector.  gc/blockheap.cpp defines the heap behind
// node_refill (the fast path is in memory.hpp), and gc/wdgc.cpp the
// collector over it.  With make GC=mps (SPRITE_GC_MPS) gc/mps.cpp replaces
// both: the Memory Pool System, a moving generational collector, as an
// experiment behind a gate (see TODO).  gc/leaky.cpp is an alternative that
// never frees.
#ifdef SPRITE_GC_MPS
#include "cyrt/graph/gc/mps.cpp"
#else
// #include "cyrt/graph/gc/leaky.cpp"
#include "cyrt/graph/gc/blockheap.cpp"
#include "cyrt/graph/gc/wdgc.cpp"
#endif

