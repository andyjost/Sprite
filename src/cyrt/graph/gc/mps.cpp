// The Memory Pool System (MPS) as the node heap and the collector of the C++
// runtime.  Selected with make GC=mps (SPRITE_GC_MPS; see Make.config), in
// place of gc/blockheap.cpp and gc/wdgc.cpp, which stay the default.  An
// experiment behind a gate: the dated TODO entry records the measurements
// and the decision.  The library comes from the submodule extern/mps,
// compiled as one C object (graph/mpsgc.c).
//
// Heap.  One arena (the virtual-memory arena class) holds one pool of the
// AMC class: a generational, copying collector with two generations here
// (the nursery and one older generation; the capacities come from the
// environment, see below).  Every node is an object of one format: the info
// pointer first, the slots after it, aligned to eight bytes.  The format
// methods read the size of an object from its info table (alloc_size), as
// the mark phase of gc/wdgc.cpp reads the slots from the format string.  Two
// kinds of object are the collector's own: a forwarding object left in the
// old copy of a moved node (GcFwd_Info, GcFwdSz_Info; a table of its own,
// not the Fwd_Info of the runtime, whose target is a live reference the
// scan must fix), and a padding object (GcPad_Info, GcPadSz_Info) in memory
// the pool does not use.  A node rewritten in place into a smaller node
// (Node::rewrite and the other in-place writers of node.hxx) pads the slack
// of its block with the latter (gc_pad_slack in graph/memory.hpp), so that
// the objects of a segment stay contiguous.  The runtime's own forward node
// of a larger block, FwdSz, records the size of the block, which the skip
// method reads.
//
// Allocation.  node_refill (the slow path of node_reserve in memory.hpp,
// which this back end makes the only path: the runs of g_alloc_runs stay
// empty) reserves and commits one object on the allocation point of the
// pool.  The object is committed before the caller writes it, which the
// reserve-and-commit protocol of MPS does not foresee: so node_refill
// writes a padding object of the size into it first, and the heap is
// consistent at every moment, also when the caller allocates again before
// it has written every slot.  The slow path of the allocation point
// (mps_ap_fill) is where MPS does its incremental work; its time is
// measured.
//
// Roots.  Five roots.  (1) An exact root over every registered queue (the
// outermost queues of the runtime states and the queues of set functions):
// the root, the bindings, and the error value of every configuration.  An
// exact reference is updated when its node moves.  (2) An ambiguous root
// over the scans of those configurations: the cursors of a scan are interior
// pointers into the nodes of the spine, and an ambiguous reference pins the
// node it points into (MPS_KEY_INTERIOR is the default of AMC).  (3) An
// ambiguous root over the nodes Python holds (gc_add_root): such a node
// never moves, so its address stays its identity.  (4) An exact root over
// the free-variable tables of the interpreter states.  The table is strong
// here, unlike under gc/wdgc.cpp: MPS scans every root at the flip of a
// trace and admits the ambiguous and the exact rank there (trace.c,
// .root.rank), so a root of the weak rank, which would splat a dead entry,
// fails an assertion.  So a free variable and its generator live as long
// as the interpreter state, as before G3.  (5) The thread root:
// the registers and the C stack of the thread, from the current frame to
// the top of the stack (pthread_getattr_np), scanned ambiguously.  So the
// nodes a step holds in locals, the Variables and Cursors of a suspended
// step, and the frames of an enclosing evaluation are found and pinned,
// and a collection inside a nested evaluation needs no rule about older
// nodes.  The 2023 draft took the frame of a static initializer as the cold
// end of the stack root, which later frames could lie above.
//
// What must not move.  The graph copier, the equality, show, and the unique
// visitor of walk.hpp key tables by the address of a node and allocate (or
// run long) while they hold them.  Each holds a GcClamp for its lifetime,
// which clamps the arena: no collection starts, and no reference the
// mutator has loaded changes.  Literal nodes and the pinned static objects
// are outside the arena; a reference to them is ignored by the fix.
//
// Collection.  MPS schedules the collections itself, by the capacities of
// the generations, and does the work incrementally inside the allocation
// slow path and behind read and write barriers that it implements with
// memory protection and a SIGSEGV handler (the first access to a protected
// segment faults; MPS handles the fault and lets the access proceed).  The
// runtime installs a handler of its own on top of the MPS handler that
// counts the faults and the time in them (gc_fault_count,
// gc_backend_stats).  The safepoint of the scheduler (run_gc) is a message
// pump: it takes the finalization messages (the Python iterator of a dead
// generator node is released, the queue of a set function is destroyed when
// the last SetEval node that refers to it has died; every creator registers
// such nodes, gc_register_generator and gc_register_seteval) and counts
// the completed collections.  node_refill requests the pump every POLL_ALLOCATIONS
// allocations.  A full collection (mps_arena_collect) runs at the safepoint
// in the stress mode, when Python asks (run_gc at evaluation depth zero:
// gc_collect, gc_verify), every SPRITE_GC_THRESHOLD allocations when that
// is set (by default never: MPS decides), and when the live configurations
// reach the configuration threshold (as in gc/wdgc.cpp: dead queues hold
// memory the pool does not see).  The sets of set functions are not freed
// by this back end.
//
// Environment.  SPRITE_GC_MPS_ARENA_MB (the address space reserved first,
// 256), SPRITE_GC_MPS_NURSERY_KB (the capacity of the nursery, 8192),
// SPRITE_GC_MPS_GEN1_KB (the capacity of the older generation, 65536),
// SPRITE_GC_THRESHOLD (full collections every so many nodes; unset: none),
// SPRITE_GC_STRESS (a full collection at every safepoint).  SPRITE_GC_GROWTH
// scales the configuration threshold after a full collection.
//
// Not supported here: the scheduler counters (COUNTERS=1, a creator word per
// node), the heap verifier (gc_verify runs a full collection and reports
// nothing), an exact count of live nodes without a walk (gc_num_nodes walks
// the pool), the weak free-variable table (see Roots), the freeing of the
// sets of set functions, threads other than the one that first allocated.

extern "C"
{
  #include "mps.h"
  #include "mpsavm.h"
  #include "mpscamc.h"
}
#include <algorithm>
#include <chrono>
#include <csignal>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <iostream>
#include <new>
#include <pthread.h>
#include <stdexcept>
#include <string>
#include <vector>
#include "cyrt/currylib/setfunctions.hpp"
#include "cyrt/state/queue.hpp"

#ifdef SPRITE_SCHEDULER_COUNTERS
#error "The scheduler counters (COUNTERS=1) are not supported with GC=mps."
#endif

namespace cyrt
{
  // The runs of the inline fast path stay empty: every allocation goes
  // through node_refill.
  AllocRun g_alloc_runs[NUM_SIZE_CLASSES];

  // The objects of the collector.  The sizes in the tables satisfy the
  // checks of InfoTable; the skip method knows the true sizes: a GcPad is
  // one word, a GcPadSz and a GcFwdSz keep their size in a word of their
  // own, a GcFwd is two words.
  InfoTable const GcPad_Info{
      T_PAD, 0, sizeof(Head) + sizeof(Arg), F_STATIC_OBJECT, "_GcPad", ""
    , nullptr, nullptr
    };
  InfoTable const GcPadSz_Info{
      T_PAD, 1, sizeof(Head) + sizeof(Arg), F_STATIC_OBJECT, "_GcPadSz", "i"
    , nullptr, nullptr
    };
  static InfoTable const GcFwd_Info{
      T_PAD, 1, sizeof(Head) + sizeof(Arg), F_STATIC_OBJECT, "_GcFwd", "x"
    , nullptr, nullptr
    };
  static InfoTable const GcFwdSz_Info{
      T_PAD, 2, sizeof(Head) + 2 * sizeof(Arg), F_STATIC_OBJECT, "_GcFwdSz"
    , "xi", nullptr, nullptr
    };

  static inline bool is_gc_object(InfoTable const * info)
  {
    return info == &GcPad_Info || info == &GcPadSz_Info
        || info == &GcFwd_Info || info == &GcFwdSz_Info;
  }

  // The state of the back end.
  static mps_arena_t g_arena = nullptr;
  static mps_fmt_t   g_fmt;
  static mps_chain_t g_chain;
  static mps_pool_t  g_pool;
  static mps_ap_t    g_ap;
  static mps_thr_t   g_thread;
  static mps_root_t  g_root_configurations;
  static mps_root_t  g_root_scans;
  static mps_root_t  g_root_python;
  static mps_root_t  g_root_vtables;
  static mps_root_t  g_root_thread;

  // The parameters.  See the header of this file.
  static size_t g_arena_mb = 256;
  static size_t g_nursery_kb = 8192;
  static size_t g_gen1_kb = 65536;
  static size_t g_threshold = NOLIMIT;
  static size_t g_growth = 8;
  static bool   g_stress = false;
  static constexpr size_t DEFAULT_CONFIGURATION_THRESHOLD = (size_t(1) << 20) / 8;
  // node_refill requests the message pump every so many allocations.
  static constexpr size_t POLL_ALLOCATIONS = size_t(1) << 14;

  // The counters.
  static size_t g_allocations = 0;
  static size_t g_allocations_at_full = 0;
  static size_t g_collections = 0;      // completed traces (gc messages)
  static size_t g_starts = 0;           // traces started (gc_start messages)
  static size_t g_full_collections = 0; // explicit full collections
  static size_t g_faults = 0;           // barrier faults handled
  static size_t g_clamps = 0;           // GcClamp regions entered
  static size_t g_clamp_depth = 0;
  static size_t g_live_bytes = 0;       // of the last completed trace
  static size_t g_condemned_bytes = 0;  // of the last completed trace
  static double g_seconds_collect = 0.0; // run_gc: full collections and the pump
  static double g_seconds_fill = 0.0;    // the allocation slow path
  static double g_seconds_fault = 0.0;   // the barrier faults
  static std::string g_last_why;

  // The Python iterators of dead generator nodes, released after the pump
  // (a release may run Python code).
  static std::vector<void *> g_pending_releases;
  // Queues whose last SetEval node died while the queue was in use by a
  // nested evaluation; destroyed at a later pump.
  static std::vector<Queue *> g_orphan_queues;

  static double seconds_since(std::chrono::steady_clock::time_point start)
  {
    return std::chrono::duration<double>(
        std::chrono::steady_clock::now() - start
      ).count();
  }

  static size_t size_from_environment(char const * name, size_t fallback)
  {
    char const * text = std::getenv(name);
    if(!text || !*text)
      return fallback;
    char * end = nullptr;
    unsigned long long const value = std::strtoull(text, &end, 10);
    if(end != text && *end == '\0' && value > 0)
      return (size_t) value;
    std::cerr << name << "=" << text
              << " is not a positive integer; using the default "
              << fallback << std::endl;
    return fallback;
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
      g_arena_mb = size_from_environment("SPRITE_GC_MPS_ARENA_MB", g_arena_mb);
      g_nursery_kb = size_from_environment("SPRITE_GC_MPS_NURSERY_KB", g_nursery_kb);
      g_gen1_kb = size_from_environment("SPRITE_GC_MPS_GEN1_KB", g_gen1_kb);
      g_threshold = size_from_environment("SPRITE_GC_THRESHOLD", NOLIMIT);
      g_growth = std::max<size_t>(2, size_from_environment("SPRITE_GC_GROWTH", g_growth));
      g_stress = stress_from_environment();
      g_gc_collect = g_stress;
      g_configuration_threshold = DEFAULT_CONFIGURATION_THRESHOLD;
    }
  } _init;

  // The format.
  // ===========

  // The size of the object at ``base``.
  static inline size_t object_size(mps_addr_t base)
  {
    Node const * obj = (Node const *) base;
    InfoTable const * info = obj->info;
    size_t const * words = (size_t const *) base;
    if(info == &GcPad_Info)
      return sizeof(void *);
    if(info == &GcPadSz_Info)
      return words[1];
    if(info == &GcFwd_Info)
      return 2 * sizeof(void *);
    if(info == &GcFwdSz_Info)
      return words[2];
    if(info == &FwdSz_Info)
      return NodeU{const_cast<Node *>(obj)}.fwdsz->bytes;
    return info->alloc_size;
  }

  static mps_res_t obj_scan(mps_ss_t ss, mps_addr_t base, mps_addr_t limit)
  {
    MPS_SCAN_BEGIN(ss)
    {
      while(base < limit)
      {
        Node * obj = (Node *) base;
        InfoTable const * info = obj->info;
        size_t size;
        if(is_gc_object(info))
          size = object_size(base);
        else
        {
          size = info == &FwdSz_Info ? NodeU{obj}.fwdsz->bytes : info->alloc_size;
          Arg * data = obj->begin();
          char const * format = info->format;
          for(index_type i=0, e=info->arity; i<e; ++i)
          {
            if(format[i] != 'p')
              continue;
            Node * ref = data[i].node;
            // A null slot (a recursive let before its patch) and a literal
            // node are outside the heap.
            if(!ref || in_literal_arena(ref))
              continue;
            mps_addr_t addr = ref;
            mps_res_t const res = MPS_FIX12(ss, &addr);
            if(res != MPS_RES_OK)
              return res;
            data[i].node = (Node *) addr;
          }
        }
        base = (char *) base + size;
      }
    }
    MPS_SCAN_END(ss);
    return MPS_RES_OK;
  }

  static mps_addr_t obj_skip(mps_addr_t base)
  {
    return (char *) base + object_size(base);
  }

  static void obj_fwd(mps_addr_t old, mps_addr_t new_)
  {
    size_t const size = object_size(old);
    size_t * words = (size_t *) old;
    if(size == 2 * sizeof(void *))
    {
      ((Node *) old)->info = &GcFwd_Info;
      words[1] = (size_t) new_;
    }
    else
    {
      ((Node *) old)->info = &GcFwdSz_Info;
      words[1] = (size_t) new_;
      words[2] = size;
    }
  }

  static mps_addr_t obj_isfwd(mps_addr_t addr)
  {
    InfoTable const * info = ((Node *) addr)->info;
    if(info == &GcFwd_Info || info == &GcFwdSz_Info)
      return (mps_addr_t) ((size_t *) addr)[1];
    return nullptr;
  }

  static void obj_pad(mps_addr_t addr, size_t size)
  {
    gc_pad(addr, size);
  }

  // The roots.
  // ==========

  // Fixes an exact reference in place.  A null reference and a reference
  // to a literal node are left alone.
  #define CYRT_FIX_EXACT(ref)                                        \
    do {                                                             \
      Node * _node = (ref);                                          \
      if(_node && !in_literal_arena(_node))                          \
      {                                                              \
        mps_addr_t _addr = _node;                                    \
        mps_res_t const _res = MPS_FIX12(ss, &_addr);                \
        if(_res != MPS_RES_OK) return _res;                          \
        (ref) = (Node *) _addr;                                      \
      }                                                              \
    } while(0)

  // Fixes an ambiguous reference: the collector pins the object it points
  // to or into; the reference itself is not changed.
  #define CYRT_FIX_AMBIG(ptr)                                        \
    do {                                                             \
      mps_addr_t _addr = (mps_addr_t) (ptr);                         \
      if(_addr)                                                      \
      {                                                              \
        mps_res_t const _res = MPS_FIX12(ss, &_addr);                \
        if(_res != MPS_RES_OK) return _res;                          \
      }                                                              \
    } while(0)

  static mps_res_t scan_configurations(mps_ss_t ss, void *, size_t)
  {
    MPS_SCAN_BEGIN(ss)
    {
      for(Queue * Q: g_queues)
      {
        for(Configuration * C: *Q)
        {
          CYRT_FIX_EXACT(C->root_storage);
          for(auto & pair: *C->bindings)
            CYRT_FIX_EXACT(pair.second);
          CYRT_FIX_EXACT(C->error.first);
        }
      }
    }
    MPS_SCAN_END(ss);
    return MPS_RES_OK;
  }

  static mps_res_t scan_scans(mps_ss_t ss, void *, size_t)
  {
    MPS_SCAN_BEGIN(ss)
    {
      for(Queue * Q: g_queues)
        for(Configuration * C: *Q)
          for(Scan::Level const & level: C->scan.frames())
            CYRT_FIX_AMBIG(level.cur.arg);
    }
    MPS_SCAN_END(ss);
    return MPS_RES_OK;
  }

  static mps_res_t scan_python_roots(mps_ss_t ss, void *, size_t)
  {
    MPS_SCAN_BEGIN(ss)
    {
      for(auto const & pair: g_roots)
        CYRT_FIX_AMBIG(pair.first);
    }
    MPS_SCAN_END(ss);
    return MPS_RES_OK;
  }

  static mps_res_t scan_vtables(mps_ss_t ss, void *, size_t)
  {
    MPS_SCAN_BEGIN(ss)
    {
      for(InterpreterState * istate: g_istates)
        for(auto & pair: istate->vtable)
          CYRT_FIX_EXACT(pair.second);
    }
    MPS_SCAN_END(ss);
    return MPS_RES_OK;
  }

  #undef CYRT_FIX_EXACT
  #undef CYRT_FIX_AMBIG

  // The top of the stack of the calling thread: the cold end of the thread
  // root.  Every frame of the process lies below it.
  static void * stack_cold_end()
  {
    pthread_attr_t attr;
    if(pthread_getattr_np(pthread_self(), &attr) == 0)
    {
      void * addr = nullptr;
      size_t size = 0;
      int const rc = pthread_attr_getstack(&attr, &addr, &size);
      pthread_attr_destroy(&attr);
      if(rc == 0 && addr)
        return (char *) addr + size;
    }
    throw std::runtime_error("MPS: cannot find the stack of this thread");
  }

  // The fault counter.
  // ==================

  // The handler MPS installed, called by count_fault.
  static struct sigaction g_mps_action;
  static bool g_counting_faults = false;

  static void count_fault(int sig, siginfo_t * info, void * context)
  {
    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    ++g_faults;
    if(g_mps_action.sa_flags & SA_SIGINFO)
      g_mps_action.sa_sigaction(sig, info, context);
    else if(g_mps_action.sa_handler != SIG_DFL && g_mps_action.sa_handler != SIG_IGN)
      g_mps_action.sa_handler(sig);
    clock_gettime(CLOCK_MONOTONIC, &t1);
    g_seconds_fault += (double) (t1.tv_sec - t0.tv_sec)
                     + (double) (t1.tv_nsec - t0.tv_nsec) * 1e-9;
  }

  // Installs count_fault on top of the handler MPS installed when the arena
  // was created.  For a fault MPS does not own, its handler passes the
  // signal on to the handler that was there before it.
  static void install_fault_counter()
  {
    struct sigaction current;
    if(sigaction(SIGSEGV, nullptr, &current) != 0)
      return;
    if(!(current.sa_flags & SA_SIGINFO) || current.sa_sigaction == count_fault)
      return;
    g_mps_action = current;
    struct sigaction mine = current;
    mine.sa_sigaction = count_fault;
    if(sigaction(SIGSEGV, &mine, nullptr) == 0)
      g_counting_faults = true;
  }

  // Creation.
  // =========

  static void fail(char const * what, mps_res_t res)
  {
    throw std::runtime_error(
        std::string("MPS: ") + what + " failed with code " + std::to_string(res)
      );
  }

  static void init_mps()
  {
    mps_res_t res;
    MPS_ARGS_BEGIN(args)
    {
      MPS_ARGS_ADD(args, MPS_KEY_ARENA_SIZE, g_arena_mb << 20);
      res = mps_arena_create_k(&g_arena, mps_arena_class_vm(), args);
    }
    MPS_ARGS_END(args);
    if(res != MPS_RES_OK)
      fail("the creation of the arena", res);

    MPS_ARGS_BEGIN(args)
    {
      MPS_ARGS_ADD(args, MPS_KEY_FMT_ALIGN, (mps_align_t) sizeof(void *));
      MPS_ARGS_ADD(args, MPS_KEY_FMT_SCAN, obj_scan);
      MPS_ARGS_ADD(args, MPS_KEY_FMT_SKIP, obj_skip);
      MPS_ARGS_ADD(args, MPS_KEY_FMT_FWD, obj_fwd);
      MPS_ARGS_ADD(args, MPS_KEY_FMT_ISFWD, obj_isfwd);
      MPS_ARGS_ADD(args, MPS_KEY_FMT_PAD, obj_pad);
      res = mps_fmt_create_k(&g_fmt, g_arena, args);
    }
    MPS_ARGS_END(args);
    if(res != MPS_RES_OK)
      fail("the creation of the object format", res);

    mps_gen_param_s gens[2] = {{g_nursery_kb, 0.85}, {g_gen1_kb, 0.45}};
    res = mps_chain_create(&g_chain, g_arena, 2, gens);
    if(res != MPS_RES_OK)
      fail("the creation of the generation chain", res);

    MPS_ARGS_BEGIN(args)
    {
      MPS_ARGS_ADD(args, MPS_KEY_FORMAT, g_fmt);
      MPS_ARGS_ADD(args, MPS_KEY_CHAIN, g_chain);
      res = mps_pool_create_k(&g_pool, g_arena, mps_class_amc(), args);
    }
    MPS_ARGS_END(args);
    if(res != MPS_RES_OK)
      fail("the creation of the pool", res);

    res = mps_ap_create_k(&g_ap, g_pool, mps_args_none);
    if(res != MPS_RES_OK)
      fail("the creation of the allocation point", res);

    res = mps_root_create(
        &g_root_configurations, g_arena, mps_rank_exact(), 0
      , scan_configurations, nullptr, 0
      );
    if(res != MPS_RES_OK)
      fail("the registration of the configuration root", res);
    res = mps_root_create(
        &g_root_scans, g_arena, mps_rank_ambig(), 0, scan_scans, nullptr, 0
      );
    if(res != MPS_RES_OK)
      fail("the registration of the scan root", res);
    res = mps_root_create(
        &g_root_python, g_arena, mps_rank_ambig(), 0, scan_python_roots
      , nullptr, 0
      );
    if(res != MPS_RES_OK)
      fail("the registration of the Python root", res);
    res = mps_root_create(
        &g_root_vtables, g_arena, mps_rank_exact(), 0, scan_vtables, nullptr, 0
      );
    if(res != MPS_RES_OK)
      fail("the registration of the free-variable root", res);

    res = mps_thread_reg(&g_thread, g_arena);
    if(res != MPS_RES_OK)
      fail("the registration of the thread", res);
    res = mps_root_create_thread(
        &g_root_thread, g_arena, g_thread, stack_cold_end()
      );
    if(res != MPS_RES_OK)
      fail("the registration of the thread root", res);

    mps_message_type_enable(g_arena, mps_message_type_finalization());
    mps_message_type_enable(g_arena, mps_message_type_gc());
    mps_message_type_enable(g_arena, mps_message_type_gc_start());

    install_fault_counter();
    if(g_clamp_depth > 0)
      mps_arena_clamp(g_arena);
  }

  // Allocation.
  // ===========

  Node * node_refill(size_t bytes)
  {
    if(!g_arena)
      init_mps();
    size_t const size = std::max(round_up(bytes), MIN_SLOT_BYTES);
    mps_addr_t p;
    do
    {
      // The inline part of mps_reserve, with the slow path timed.
      char * const alloc = (char *) g_ap->alloc;
      if(alloc + size > alloc && alloc + size <= (char *) g_ap->limit)
      {
        g_ap->alloc = alloc + size;
        p = g_ap->init;
      }
      else
      {
        auto const start = std::chrono::steady_clock::now();
        mps_res_t const res = mps_ap_fill(&p, g_ap, size);
        g_seconds_fill += seconds_since(start);
        if(res != MPS_RES_OK)
          throw std::bad_alloc();
      }
      // A valid object from now on (see the header of this file).
      gc_pad(p, size);
    } while(!mps_commit(g_ap, p, size));
    ++g_allocations;
    if(g_allocations % POLL_ALLOCATIONS == 0
        || g_allocations - g_allocations_at_full >= g_threshold)
      g_gc_collect = true;
    return (Node *) p;
  }

  // The messages.
  // =============

  // Takes the messages of the completed and the started traces.  No side
  // effect beyond the counters, so the getters may call it.
  static void pump_gc_messages()
  {
    if(!g_arena)
      return;
    mps_message_t message;
    while(mps_message_get(&message, g_arena, mps_message_type_gc()))
    {
      ++g_collections;
      g_live_bytes = mps_message_gc_live_size(g_arena, message);
      g_condemned_bytes = mps_message_gc_condemned_size(g_arena, message);
      mps_message_discard(g_arena, message);
    }
    while(mps_message_get(&message, g_arena, mps_message_type_gc_start()))
    {
      ++g_starts;
      g_last_why = mps_message_gc_start_why(g_arena, message);
      mps_message_discard(g_arena, message);
    }
  }

  static bool queue_in_use(Queue * queue)
  {
    for(RuntimeState * rts: g_rtslist)
      for(Queue * Q: rts->qstack)
        if(Q == queue)
          return true;
    return false;
  }

  // The last SetEval node of ``queue`` died.
  static void release_queue(Queue * queue)
  {
    if(!queue || !g_queues.count(queue))
      return;
    assert(queue->seteval_refs > 0);
    if(--queue->seteval_refs > 0)
      return;
    if(queue_in_use(queue))
      g_orphan_queues.push_back(queue);
    else
      delete queue;
  }

  static void destroy_orphan_queues()
  {
    size_t kept = 0;
    for(Queue * queue: g_orphan_queues)
    {
      if(!g_queues.count(queue))
        continue;
      if(queue_in_use(queue))
        g_orphan_queues[kept++] = queue;
      else
        delete queue;
    }
    g_orphan_queues.resize(kept);
  }

  static void pump_finalization_messages()
  {
    mps_message_t message;
    while(mps_message_get(&message, g_arena, mps_message_type_finalization()))
    {
      mps_addr_t ref;
      mps_message_finalization_ref(&ref, g_arena, message);
      Node * node = (Node *) ref;
      if(node->info == &_biGenerator_Info)
        g_pending_releases.push_back(NodeU{node}.generator->data);
      else if(node->info == &SetEval_Info)
        release_queue(NodeU{node}.seteval->queue);
      // A node that was stepped is a forward node now: the node of the
      // rest of the list took the iterator over, and a SetEval node is
      // never stepped.
      mps_message_discard(g_arena, message);
    }
    destroy_orphan_queues();
  }

  static void release_pending()
  {
    if(g_pending_releases.empty())
      return;
    std::vector<void *> pending;
    pending.swap(g_pending_releases);
    for(void * data: pending)
      generator_release(data);
  }

  static void pump_messages()
  {
    if(!g_arena)
      return;
    pump_gc_messages();
    pump_finalization_messages();
  }

  // The safepoint.
  // ==============

  void run_gc()
  {
    auto const start = std::chrono::steady_clock::now();
    if(g_arena)
    {
      bool const full = g_stress
          || g_eval_depth == 0
          || g_allocations - g_allocations_at_full >= g_threshold
          || g_num_configurations >= g_configuration_threshold;
      if(full && g_clamp_depth == 0)
      {
        mps_res_t const res = mps_arena_collect(g_arena);
        mps_arena_release(g_arena);
        if(res != MPS_RES_OK)
          fail("a full collection", res);
        ++g_full_collections;
        g_allocations_at_full = g_allocations;
        pump_messages();
        g_configuration_threshold = std::max(
            DEFAULT_CONFIGURATION_THRESHOLD, g_growth * g_num_configurations
          );
      }
      else
        pump_messages();
    }
    g_seconds_collect += seconds_since(start);
    g_gc_collect = g_stress;
    release_pending();
  }

  std::string gc_verify()
  {
    if(g_eval_depth != 0)
      throw std::runtime_error(
          "cannot run the collector while an evaluation is active"
        );
    run_gc();
    return std::string();
  }

  // Registrations.
  // ==============

  static void finalize(Node * node)
  {
    assert(g_arena);
    mps_addr_t addr = node;
    mps_res_t const res = mps_finalize(g_arena, &addr);
    if(res != MPS_RES_OK)
      fail("the registration of a node for finalization", res);
  }

  void gc_register_generator(Node * node)
  {
    assert(node->info == &_biGenerator_Info);
    finalize(node);
  }

  void gc_register_seteval(Node * node)
  {
    assert(node->info == &SetEval_Info);
    Queue * queue = NodeU{node}.seteval->queue;
    if(queue)
      ++queue->seteval_refs;
    finalize(node);
  }

  GcClamp::GcClamp()
  {
    ++g_clamps;
    if(g_clamp_depth++ == 0 && g_arena)
      mps_arena_clamp(g_arena);
  }

  GcClamp::~GcClamp()
  {
    assert(g_clamp_depth > 0);
    if(--g_clamp_depth == 0 && g_arena)
      mps_arena_release(g_arena);
  }

  size_t gc_enter_evaluation()
  {
    return ++g_eval_depth;
  }

  void gc_leave_evaluation(size_t)
  {
    assert(g_eval_depth > 0);
    --g_eval_depth;
  }

  // The counters.
  // =============

  char const * gc_backend_name() { return "mps"; }

  static void count_object(mps_addr_t addr, mps_fmt_t, mps_pool_t, void * p, size_t)
  {
    if(!is_gc_object(((Node *) addr)->info))
      ++*(size_t *) p;
  }

  // Walks the pool.  Costs the whole heap; for the tests and the statistics.
  size_t gc_num_nodes()
  {
    if(!g_arena)
      return 0;
    mps_arena_park(g_arena);
    size_t count = 0;
    mps_arena_formatted_objects_walk(g_arena, count_object, &count, 0);
    if(g_clamp_depth == 0)
      mps_arena_release(g_arena);
    return count;
  }

  size_t gc_num_allocations() { return g_allocations; }

  size_t gc_num_collections()
  {
    pump_gc_messages();
    return g_collections;
  }

  double gc_seconds()
  {
    return g_seconds_collect + g_seconds_fill + g_seconds_fault;
  }

  size_t gc_threshold() { return g_threshold; }
  size_t gc_growth() { return g_growth; }
  bool gc_stress() { return g_stress; }
  size_t gc_fault_count() { return g_faults; }

  void gc_set_threshold(size_t threshold)
  {
    if(threshold == 0)
      throw std::invalid_argument("the collection threshold must be positive");
    g_threshold = threshold;
    if(g_allocations - g_allocations_at_full >= g_threshold)
      g_gc_collect = true;
  }

  size_t gc_num_blocks()
  {
    return g_arena ? mps_arena_committed(g_arena) / (size_t(64) << 10) : 0;
  }

  size_t gc_heap_bytes()
  {
    return g_arena ? mps_arena_committed(g_arena) : 0;
  }

  std::vector<std::pair<std::string, double>> gc_backend_stats()
  {
    pump_gc_messages();
    std::vector<std::pair<std::string, double>> stats;
    stats.emplace_back("allocations", (double) g_allocations);
    stats.emplace_back("collections", (double) g_collections);
    stats.emplace_back("starts", (double) g_starts);
    stats.emplace_back("full_collections", (double) g_full_collections);
    stats.emplace_back("faults", (double) g_faults);
    stats.emplace_back("fault_seconds", g_seconds_fault);
    stats.emplace_back("fill_seconds", g_seconds_fill);
    stats.emplace_back("collect_seconds", g_seconds_collect);
    stats.emplace_back("clamps", (double) g_clamps);
    stats.emplace_back("counting_faults", g_counting_faults ? 1.0 : 0.0);
    stats.emplace_back("live_bytes", (double) g_live_bytes);
    stats.emplace_back("condemned_bytes", (double) g_condemned_bytes);
    stats.emplace_back("committed_bytes", g_arena ? (double) mps_arena_committed(g_arena) : 0.0);
    stats.emplace_back("reserved_bytes", g_arena ? (double) mps_arena_reserved(g_arena) : 0.0);
    stats.emplace_back("spare_committed_bytes", g_arena ? (double) mps_arena_spare_committed(g_arena) : 0.0);
    stats.emplace_back("arena_mb", (double) g_arena_mb);
    stats.emplace_back("nursery_kb", (double) g_nursery_kb);
    stats.emplace_back("gen1_kb", (double) g_gen1_kb);
    stats.emplace_back("orphan_queues", (double) g_orphan_queues.size());
    return stats;
  }
}
