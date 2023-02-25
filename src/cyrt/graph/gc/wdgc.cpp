// The world's dumbest garbage collector.  The address of every node allocated
// is stored in a vector.  When collection runs, it does a mark-and-sweep pass
// over that list.  There are no generations and nothing is moved.

#include <cstdint>
#include <sstream>
#include <iomanip>
#include <iostream>
#include <vector>

// #define GC_REPORT

// The fractional threshold triggering a size increase/decrease.
#define GROWFRAC 0.15
#define SHRINKFRAC 0.00001
#define MARKBIT 0x8000000000000000
#define INFO(node) ((InfoTable *)(((uintptr_t) node->info) & ~MARKBIT))

static std::vector<void *> g_addr;

// The number of live objects at which point GC should run.
static size_t g_threshold = 10000000;

static struct _Init
{
  _Init()
  {
    size_t res = 1 + g_threshold / (2 * sizeof(void*));
    g_addr.reserve(res);
  }
} _init;

namespace cyrt
{
  Node * node_reserve(size_t bytes)
  {
    void * addr = std::malloc(bytes);
    g_addr.push_back(addr);
    if(g_addr.size() >= g_threshold)
      g_gc_collect = true;
    return (Node *) addr;
  }

  bool node_commit(void * addr, size_t bytes)
  {
    return true;
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

  static void run_mark_phase()
  {
    std::vector<Node *> stack;
    stack.reserve(100000);
    for(auto * rts: g_rtslist)
    {
      for(auto * Q: rts->qstack)
      {
        for(auto * C: *Q)
        {
          stack.push_back(C->root_storage);
          for(auto & pair: *C->bindings)
            stack.push_back(pair.second);
        }
      }
      for(auto pair: rts->vtable)
        stack.push_back(pair.second);
    }
    while(!stack.empty())
    {
      Node * node = stack.back();
      stack.pop_back();
      if(is_marked_or_pinned(node))
        continue;
      else
        mark(node);
      auto data = node->begin();
      auto * info = INFO(node);
      for(index_type i=0, e=info->arity; i<e; ++i)
        if(info->format[i] == 'p')
          stack.push_back(data[i].node);
    }
  }

  static void run_sweep_phase()
  {
    auto p = g_addr.begin();
    auto q = p;
    auto const e = g_addr.end();
    while(q != e)
    {
      Node * node = (Node *) *q;
      if(is_marked(node))
      {
        clear(node);
        *p++ = *q++;
      }
      else
        std::free(*q++);
    }
    g_addr.resize(p - g_addr.begin());
  }

  // static void show_nodes(bool show)
  // {
  //   for(auto addr: g_addr)
  //   {
  //     Node * node = (Node *) addr;
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
    for(auto addr: g_addr)
    {
      Node * node = (Node *) addr;
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
    #ifdef GC_REPORT
    (std::cerr << "GC " << g_addr.size() << "/" << g_threshold << " ").flush();
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
    double const frac = double(g_addr.size()) / double(g_threshold);
    if(frac >= GROWFRAC)
      g_threshold <<= 1;
    else if(frac <= SHRINKFRAC && g_threshold > 1)
      g_threshold >>= 1;
    #ifdef GC_REPORT
    (std::cerr << g_addr.size() << "/" << g_threshold << "\n").flush();
    #endif
    g_gc_collect = false;
  }
}

