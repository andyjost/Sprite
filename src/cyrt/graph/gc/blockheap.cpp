// The node heap: blocks of one size class each, with side bitmaps.  This
// file is included from graph/memory.cpp before gc/wdgc.cpp, the collector,
// which marks and sweeps the heap described here.
//
// Blocks.  The heap takes chunks of CHUNK_BYTES from the system and cuts
// them into blocks of BLOCK_BYTES, aligned to their size.  A block holds
// slots of one size (its size class: MIN_SLOT_BYTES to MAX_SMALL_BYTES in
// steps of SLOT_GRAIN; see memory.hpp) after a header of DATA_OFFSET bytes.
// The block of a node is the address of the node with the low bits masked
// (block_of), and the slot of a node is its offset divided by the slot size,
// by a reciprocal multiplication (slot_of).  The header keeps three bitmaps
// with one bit per slot: ``alloc``, the slots that hold a node, ``mark``,
// the marks of the current collection, and ``old``, the marks of the last
// one.  So the mark bit leaves the info pointer, and a collection reads and
// writes the bitmaps, not the nodes.  A node larger than MAX_SMALL_BYTES
// gets a span of whole blocks of its own, with the same header in the first
// block (kind BLOCK_LARGE), so block_of and the bitmaps serve it too.
// Memory taken from the system is kept: an empty block goes to a pool and
// serves any size class next.  The layout of a block is in gc/block.hpp.
//
// Ages.  A node marked in the last collection is old; a node allocated
// since is young.  The sweep copies ``mark`` into ``old`` before it clears
// it, so ``old`` names the old nodes until the next sweep, and it sets the
// flag ``young`` of a block that kept no node: every node in such a block
// is young.  The collector counts the old and the young nodes it marks, and
// a runtime built with SPRITE_GC_WRITE_COUNTERS counts the writes into old
// nodes (gc_count_redex_write, gc_count_write, gc_count_slot_write; see
// gc/wdgc.cpp) and keeps a fourth bitmap, ``dirty``, of the old slots
// written since the last sweep: the distinct old nodes a write barrier
// would have recorded.  The bitmaps are an input of those counters alone:
// the mark phase traces every live node as before.
//
// The heap map.  A write into a slot whose node is not at hand gives the
// counter a slot address, which may lie outside the heap: a field of a
// Configuration, a local of generated code, a cell of an interpreter
// frame.  A two-level bitmap over the address space tells whether an
// address is inside a block of this heap: the high bits of the address
// index a table of bitmaps, and each bitmap has a bit per BLOCK_BYTES of a
// region of 4 GB (in_heap_map).  take_chunk sets the bits of its blocks;
// large_reserve sets the bit of the first block of its span, the one with
// the header, and free_large clears it.
//
// Allocation.  Each size class has a run of free slots, published in
// g_alloc_runs for the inline fast path of node_reserve (memory.hpp).  When
// the run is empty, node_refill finds the next run of zero bits in the
// ``alloc`` bitmap of the current block of the class (a lazy sweep: the
// dead slots of a block are found when the allocator reaches the block, not
// at the collection), or takes the next block of the class list (blocks
// with live nodes and free slots), or an empty block from the pool, or a
// new chunk.  The counts of nodes and allocations are kept per run, not per
// node: a run counts when it is handed out, and the part of a run not yet
// consumed is subtracted when a count is read.
//
// Collection.  Before the mark phase, retire_runs records the consumed part
// of every run in the ``alloc`` bitmaps and empties the runs.  After the
// mark phase, sweep_blocks visits the blocks, not the nodes: the population
// count of ``mark`` gives the survivors, ``alloc`` takes the marks, an
// empty block goes to the pool, a block with free slots to the list of its
// class, and the span of a dead large node back to the system.  The
// collector itself (roots, the mark phase, the free-variable tables, the
// finalizers, the registries, the threshold policy, and the stress mode) is
// in gc/wdgc.cpp.
//
// Nested evaluations.  A collection inside a nested evaluation (one started
// from a Python callback) must keep every node the suspended steps of the
// enclosing evaluation may hold (see gc/wdgc.cpp).  Every block records the
// time it was taken from the pool (``seq``, a counter of such events), and
// gc_enter_evaluation records the counter.  A block taken before the
// innermost evaluation began is older: every allocated slot of it is a
// root, it is not swept, and it is not listed for allocation until the
// outermost evaluation collects.  That is a superset of the nodes allocated
// before the evaluation began (the free slots of an older block that were
// filled after it began are roots too), bounded by the free room of the
// heap at that moment.  A block keeps its ``seq`` while it holds nodes; it
// gets a new one when it leaves the pool.
//
// Threads.  One ThreadHeap holds the runs, the class lists, the pool, and
// the list of blocks.  Today there is one, g_heap.  A worker thread of the
// independent-world prototype gets a heap of its own, with the runs of its
// heap in place of g_alloc_runs, and the collector stops every thread at
// its safepoint before it marks.
//
// Verifier.  verify_heap, run by the collector after its mark phase in the
// stress mode (SPRITE_GC_STRESS=1) and on request (gc_verify), checks every
// marked node: it is a slot start of a known block, its info table is sane,
// its alloc_size fits the slot, and every successor is null, a literal
// node, the static object of a pinned info table, or a marked slot start;
// every node Python holds (gc_add_root) is a literal node, the static
// object of a pinned info table, or a marked slot start, so a heap copy of
// a pinned constructor, which the mark phase skips by its flag, is found
// before the sweep frees it under its holder; and in every block the marks
// are a subset of the allocated slots.  A dangling pointer into a freed slot
// shows up as a mark outside ``alloc``.
//
// Instrumented build.  With SPRITE_SCHEDULER_COUNTERS the creator of a node
// is kept in a table beside the block (one word per slot), written by
// node_refill: the heap never publishes a run, so every allocation goes
// through it.  Generated code is the same in both builds.

#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <new>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include "cyrt/graph/gc/block.hpp"

namespace cyrt
{
  // Sets the bits from ``begin`` up to ``end``.
  static void set_bits(uint64_t * bits, uint32_t begin, uint32_t end)
  {
    for(uint32_t i = begin; i < end;)
    {
      uint32_t const word = i >> 6;
      uint32_t const low = i & 63;
      uint32_t const stop = std::min<uint32_t>(end - (word << 6), 64);
      uint64_t const upto
          = stop == 64 ? ~uint64_t(0) : (uint64_t(1) << stop) - 1;
      bits[word] |= upto & (~uint64_t(0) << low);
      i = (word + 1) << 6;
    }
  }

  // Clears the bits from ``begin`` up to ``end``.
  static void clear_bits(uint64_t * bits, uint32_t begin, uint32_t end)
  {
    for(uint32_t i = begin; i < end;)
    {
      uint32_t const word = i >> 6;
      uint32_t const low = i & 63;
      uint32_t const stop = std::min<uint32_t>(end - (word << 6), 64);
      uint64_t const upto
          = stop == 64 ? ~uint64_t(0) : (uint64_t(1) << stop) - 1;
      bits[word] &= ~(upto & (~uint64_t(0) << low));
      i = (word + 1) << 6;
    }
  }

  static inline size_t popcount_words(uint64_t const * bits, size_t words)
  {
    size_t n = 0;
    for(size_t k = 0; k < words; ++k)
      if(bits[k])
        n += (size_t) __builtin_popcountll(bits[k]);
    return n;
  }

  static inline bool any_bit(uint64_t const * bits, size_t words)
  {
    uint64_t any = 0;
    for(size_t k = 0; k < words; ++k)
      any |= bits[k];
    return any != 0;
  }

  // The state of one size class.
  struct SizeClass
  {
    uint32_t slot_bytes; // zero until the class is first used
    uint32_t nslots;
    uint32_t slot_magic;
    Block *  block;      // the block of the current run
    Block *  list;       // blocks with live nodes and free slots
    bool     active;     // in ThreadHeap::active (see retire_runs)
    #ifdef SPRITE_SCHEDULER_COUNTERS
    AllocRun run;        // the run of an instrumented build; see above
    #endif
  };

  // The heap of one thread.  Constant-initialized: it is usable during the
  // static initialization of the library.
  // A range of addresses the heap holds: a chunk or the span of a large
  // node.  The verifier asks whether a pointer is inside the heap.
  struct Range
  {
    uintptr_t base;
    size_t    bytes;
    bool operator<(Range const & other) const { return base < other.base; }
  };

  struct ThreadHeap
  {
    SizeClass classes[NUM_SIZE_CLASSES];
    Block *   pool;        // empty blocks
    Block **  blocks;      // every block: small, empty, and large spans
    size_t    nblocks;
    size_t    capacity;    // room in ``blocks``
    size_t    block_seq;   // the last value given to Block::seq
    size_t    chunks;      // chunks taken from the system
    size_t    large_bytes; // bytes of the spans of large nodes
    // The chunks and spans, sorted; made on first use.
    std::vector<Range> * ranges;
    // The classes with a current block, for retire_runs: a collection per
    // step (the stress mode) must not visit every class.
    uint8_t   active[NUM_SIZE_CLASSES];
    size_t    nactive;
  };

  AllocRun g_alloc_runs[NUM_SIZE_CLASSES];
  static ThreadHeap g_heap;

  // The counts.  g_survivors is the number of nodes alive at the end of the
  // last collection, g_handed the slots handed out in runs since then, and
  // g_allocations the slots handed out since the start.  The slots of the
  // current runs not yet consumed are in both of the last two; unconsumed()
  // subtracts them.
  static size_t g_survivors = 0;
  static size_t g_handed = 0;
  static size_t g_allocations = 0;

  // The number of nodes at which the collector runs.  The policy is in
  // gc/wdgc.cpp; node_refill reads the threshold.
  #define GC_DEFAULT_THRESHOLD (size_t(1) << 20)
  static size_t g_threshold = GC_DEFAULT_THRESHOLD;

  #ifdef SPRITE_SCHEDULER_COUNTERS
  size_t g_creator_serial = 0;
  #endif

  // The heap map (see the header of this file).  A user address has 47
  // bits; a region is the 4 GB that share the high 15 bits, and its bitmap
  // has a bit per BLOCK_BYTES of it.  A region's bitmap is made when the
  // first block of the region is taken, and never freed.
  static constexpr unsigned HEAP_MAP_REGION_SHIFT = 32;
  static constexpr unsigned HEAP_MAP_BLOCK_SHIFT = 16;
  static_assert(BLOCK_BYTES == (size_t(1) << HEAP_MAP_BLOCK_SHIFT), "");
  static constexpr size_t HEAP_MAP_REGIONS = size_t(1) << (47 - HEAP_MAP_REGION_SHIFT);
  static constexpr size_t HEAP_MAP_WORDS
      = (size_t(1) << (HEAP_MAP_REGION_SHIFT - HEAP_MAP_BLOCK_SHIFT)) / 64;
  static uint64_t * g_heap_map[HEAP_MAP_REGIONS];

  static inline bool in_heap_map(void const * p)
  {
    uintptr_t const a = (uintptr_t) p;
    if(a >> 47)
      return false;
    uint64_t const * region = g_heap_map[a >> HEAP_MAP_REGION_SHIFT];
    if(!region)
      return false;
    uintptr_t const i
        = (a >> HEAP_MAP_BLOCK_SHIFT) & ((HEAP_MAP_WORDS << 6) - 1);
    return (region[i >> 6] >> (i & 63)) & 1;
  }

  // Sets or clears the bits of the blocks from ``base`` over ``bytes``.
  static void heap_map_set(void const * base, size_t bytes, bool value)
  {
    uintptr_t const first = (uintptr_t) base;
    assert(first % BLOCK_BYTES == 0);
    // The map covers the 47-bit user space.  A block above it (a host with
    // five-level paging may hand one out) stays unmapped: in_heap_map
    // answers false for it, and a slot write there goes uncounted.
    if(first >> 47)
      return;
    for(uintptr_t a = first; a < first + bytes; a += BLOCK_BYTES)
    {
      uint64_t *& region = g_heap_map[a >> HEAP_MAP_REGION_SHIFT];
      if(!region)
      {
        region = (uint64_t *) std::calloc(HEAP_MAP_WORDS, sizeof(uint64_t));
        if(!region)
          throw std::bad_alloc();
      }
      uintptr_t const i
          = (a >> HEAP_MAP_BLOCK_SHIFT) & ((HEAP_MAP_WORDS << 6) - 1);
      if(value)
        region[i >> 6] |= uint64_t(1) << (i & 63);
      else
        region[i >> 6] &= ~(uint64_t(1) << (i & 63));
    }
  }

  static inline void set_current(SizeClass & cls, Block * b, size_t c)
  {
    if(!cls.active)
    {
      cls.active = true;
      g_heap.active[g_heap.nactive++] = (uint8_t) c;
    }
    cls.block = b;
  }

  static inline AllocRun & run_of(size_t c)
  {
    #ifdef SPRITE_SCHEDULER_COUNTERS
    return g_heap.classes[c].run;
    #else
    return g_alloc_runs[c];
    #endif
  }

  static size_t unconsumed()
  {
    size_t n = 0;
    for(size_t c = 0; c < NUM_SIZE_CLASSES; ++c)
    {
      AllocRun const & run = run_of(c);
      if(run.free != run.limit)
        n += size_t(run.limit - run.free) / g_heap.classes[c].slot_bytes;
    }
    return n;
  }

  static inline size_t nodes_in_use()
    { return g_survivors + g_handed - unconsumed(); }

  static void init_class(SizeClass & cls, size_t slot_bytes)
  {
    cls.slot_bytes = (uint32_t) slot_bytes;
    cls.nslots = (uint32_t) ((BLOCK_BYTES - DATA_OFFSET) / slot_bytes);
    cls.slot_magic
        = (uint32_t) (((uint64_t(1) << 32) + slot_bytes - 1) / slot_bytes);
    cls.block = nullptr;
    cls.list = nullptr;
  }

  // Makes room for ``count`` more blocks in the list of blocks.
  static void reserve_blocks(size_t count)
  {
    if(g_heap.nblocks + count <= g_heap.capacity)
      return;
    size_t capacity = std::max(g_heap.capacity * 2, size_t(64));
    while(capacity < g_heap.nblocks + count)
      capacity *= 2;
    Block ** blocks = (Block **) std::realloc(
        g_heap.blocks, capacity * sizeof(Block *)
      );
    if(!blocks)
      throw std::bad_alloc();
    g_heap.blocks = blocks;
    g_heap.capacity = capacity;
  }

  // Records a range the heap holds.  The vector is made on first use, so
  // the heap is usable during static initialization.
  static void add_range(void const * base, size_t bytes)
  {
    if(!g_heap.ranges)
      g_heap.ranges = new std::vector<Range>();
    Range const range{(uintptr_t) base, bytes};
    auto & ranges = *g_heap.ranges;
    ranges.insert(std::lower_bound(ranges.begin(), ranges.end(), range), range);
  }

  static void remove_range(void const * base)
  {
    auto & ranges = *g_heap.ranges;
    Range const key{(uintptr_t) base, 0};
    auto p = std::lower_bound(ranges.begin(), ranges.end(), key);
    assert(p != ranges.end() && p->base == key.base);
    ranges.erase(p);
  }

  // Takes a chunk from the system and puts its blocks into the pool.
  static void take_chunk()
  {
    reserve_blocks(BLOCKS_PER_CHUNK);
    void * mem = std::aligned_alloc(BLOCK_BYTES, CHUNK_BYTES);
    if(!mem)
      throw std::bad_alloc();
    try
    {
      add_range(mem, CHUNK_BYTES);
      heap_map_set(mem, CHUNK_BYTES, true);
    }
    catch(...)
    {
      std::free(mem);
      throw;
    }
    for(size_t k = 0; k < BLOCKS_PER_CHUNK; ++k)
    {
      Block * b = (Block *) ((char *) mem + k * BLOCK_BYTES);
      std::memset(b, 0, DATA_OFFSET);
      b->kind = BLOCK_EMPTY;
      b->next = g_heap.pool;
      g_heap.pool = b;
      g_heap.blocks[g_heap.nblocks++] = b;
    }
    ++g_heap.chunks;
  }

  static Block * take_empty_block()
  {
    if(!g_heap.pool)
      take_chunk();
    Block * b = g_heap.pool;
    g_heap.pool = b->next;
    b->next = nullptr;
    b->seq = ++g_heap.block_seq;
    return b;
  }

  static void init_small_block(Block * b, SizeClass const & cls)
  {
    // The bitmaps of an empty block are clear: a new block is zeroed with
    // its chunk, and a block that became empty took its clear marks.
    assert(!any_bit(b->alloc, BITMAP_WORDS) && !any_bit(b->mark, BITMAP_WORDS));
    assert(!any_bit(b->old, BITMAP_WORDS));
    #ifdef SPRITE_GC_WRITE_COUNTERS
    assert(!any_bit(b->dirty, BITMAP_WORDS));
    #endif
    b->kind = BLOCK_SMALL;
    b->slot_bytes = cls.slot_bytes;
    b->slot_magic = cls.slot_magic;
    b->nslots = cls.nslots;
    b->cursor = 0;
    b->spans = 1;
    // No node of it survived a collection: every node it gets is young.
    b->young = 1;
    b->touched = 0;
    #ifdef SPRITE_SCHEDULER_COUNTERS
    if(!b->creators)
    {
      b->creators = (size_t *) std::malloc(MAX_SLOTS * sizeof(size_t));
      if(!b->creators)
        throw std::bad_alloc();
    }
    #endif
  }

  // Finds the next run of free slots of ``b`` at or after its cursor, moves
  // the cursor past it, and returns false when none is left.
  static bool find_free_run(Block * b, AllocRun & run)
  {
    uint32_t const n = b->nslots;
    uint32_t i = b->cursor;
    while(i < n)
    {
      uint64_t const w = ~b->alloc[i >> 6] & (~uint64_t(0) << (i & 63));
      if(w)
      {
        i = (i & ~63u) + (uint32_t) __builtin_ctzll(w);
        break;
      }
      i = (i & ~63u) + 64;
    }
    if(i >= n)
    {
      b->cursor = n;
      return false;
    }
    uint32_t j = i + 1;
    while(j < n)
    {
      uint64_t const w = b->alloc[j >> 6] & (~uint64_t(0) << (j & 63));
      if(w)
      {
        j = (j & ~63u) + (uint32_t) __builtin_ctzll(w);
        break;
      }
      j = (j & ~63u) + 64;
    }
    if(j > n)
      j = n;
    run.free = slot_address(b, i);
    run.limit = slot_address(b, j);
    b->cursor = j;
    // The run counts as allocated from now on; retire_runs clears the part
    // not consumed before a collection reads the bitmap.
    set_bits(b->alloc, i, j);
    return true;
  }

  static inline void count_handed(size_t slots)
  {
    g_handed += slots;
    g_allocations += slots;
    if(g_survivors + g_handed >= g_threshold)
      g_gc_collect = true;
  }

  // A node larger than the largest size class: a span of its own.
  static Node * large_reserve(size_t slot_bytes)
  {
    size_t const spans
        = (DATA_OFFSET + slot_bytes + BLOCK_BYTES - 1) / BLOCK_BYTES;
    reserve_blocks(1);
    void * mem = std::aligned_alloc(BLOCK_BYTES, spans * BLOCK_BYTES);
    if(!mem)
      throw std::bad_alloc();
    try
    {
      add_range(mem, spans * BLOCK_BYTES);
      // The first block of the span alone: the others have no header.
      heap_map_set(mem, BLOCK_BYTES, true);
    }
    catch(...)
    {
      std::free(mem);
      throw;
    }
    Block * b = (Block *) mem;
    std::memset(b, 0, DATA_OFFSET);
    b->kind = BLOCK_LARGE;
    b->slot_bytes = (uint32_t) slot_bytes;
    b->slot_magic = 0;
    b->nslots = 1;
    b->seq = ++g_heap.block_seq;
    b->cursor = 1;
    b->spans = (uint32_t) spans;
    b->young = 1;
    b->alloc[0] = 1;
    #ifdef SPRITE_SCHEDULER_COUNTERS
    b->creators = (size_t *) std::malloc(sizeof(size_t));
    if(!b->creators)
    {
      std::free(mem);
      throw std::bad_alloc();
    }
    b->creators[0] = g_creator_serial;
    #endif
    g_heap.blocks[g_heap.nblocks++] = b;
    g_heap.large_bytes += spans * BLOCK_BYTES;
    count_handed(1);
    return (Node *) block_data(b);
  }

  static void free_large(Block * b)
  {
    remove_range(b);
    heap_map_set(b, BLOCK_BYTES, false);
    g_heap.large_bytes -= size_t(b->spans) * BLOCK_BYTES;
    #ifdef SPRITE_SCHEDULER_COUNTERS
    std::free(b->creators);
    #endif
    std::free(b);
  }

  Node * node_refill(size_t bytes)
  {
    size_t const slot_bytes = std::max(round_up(bytes), MIN_SLOT_BYTES);
    if(slot_bytes > MAX_SMALL_BYTES)
      return large_reserve(slot_bytes);
    size_t const c = (slot_bytes - MIN_SLOT_BYTES) / SLOT_GRAIN;
    SizeClass & cls = g_heap.classes[c];
    if(!cls.slot_bytes)
      init_class(cls, slot_bytes);
    AllocRun & run = run_of(c);
    if(size_t(run.limit - run.free) < slot_bytes)
    {
      while(true)
      {
        if(Block * b = cls.block)
        {
          if(find_free_run(b, run))
            break;
          // Exhausted.  It stays in the list of blocks and is classified
          // again at the next collection; the class stays active until
          // then (its run is empty).
          cls.block = nullptr;
        }
        if(Block * listed = cls.list)
        {
          cls.list = listed->next;
          listed->next = nullptr;
          set_current(cls, listed, c);
        }
        else
        {
          Block * fresh = take_empty_block();
          init_small_block(fresh, cls);
          set_current(cls, fresh, c);
        }
      }
      count_handed(size_t(run.limit - run.free) / slot_bytes);
    }
    char * const addr = run.free;
    run.free = addr + slot_bytes;
    #ifdef SPRITE_SCHEDULER_COUNTERS
    Block * b = block_of(addr);
    b->creators[slot_of(b, addr)] = g_creator_serial;
    #endif
    return (Node *) addr;
  }

  #ifdef SPRITE_SCHEDULER_COUNTERS
  size_t node_creator(Node const * node)
  {
    if(in_literal_arena(node) || is_pinned(*node->info))
      return 0;
    Block * b = block_of(node);
    return b->creators[slot_of(b, node)];
  }
  #endif

  // The mark bits.  The collector calls these for heap nodes only: a pinned
  // static object and a literal node have no block.
  static inline bool heap_marked(Node const * node)
  {
    Block * b = block_of(node);
    return test_bit(b->mark, slot_of(b, node));
  }

  static inline void heap_mark(Node const * node)
  {
    Block * b = block_of(node);
    set_bit(b->mark, slot_of(b, node));
  }

  // Marks a node and tells whether it is old: marked in the last
  // collection as well (see the header of this file).
  static inline bool heap_mark_and_age(Node const * node)
  {
    Block * b = block_of(node);
    uint32_t const i = slot_of(b, node);
    set_bit(b->mark, i);
    return test_bit(b->old, i);
  }

  // The counters of writes into old nodes.  See the header of this file
  // and gc/wdgc.cpp, which reports them.  ``g_old_redexes`` and
  // ``g_old_slot_writes`` count since the last collection; the sweep counts
  // the old nodes written (the ``dirty`` bits) and the blocks touched since
  // then in ``g_old_nodes_written`` and ``g_old_blocks``.  Without
  // SPRITE_GC_WRITE_COUNTERS the functions are empty inline functions
  // (memory.hpp) and the counts stay zero.
  static size_t g_old_redexes = 0;
  static size_t g_old_slot_writes = 0;
  static size_t g_old_nodes_written = 0;
  static size_t g_old_blocks = 0;

  bool gc_write_counters_enabled()
  {
    #ifdef SPRITE_GC_WRITE_COUNTERS
    return true;
    #else
    return false;
    #endif
  }

  #ifdef SPRITE_GC_WRITE_COUNTERS
  // Counts a write into slot ``i`` of block ``b`` when the slot is old.
  static inline void count_old_write(Block * b, uint32_t i, size_t & counter)
  {
    if(test_bit(b->old, i))
    {
      ++counter;
      set_bit(b->dirty, i);
      b->touched = 1;
    }
  }

  void gc_count_redex_write_slow(Node const * redex, Block * b)
  {
    count_old_write(b, slot_of(b, redex), g_old_redexes);
  }

  void gc_count_redex_write(Node const * redex)
  {
    gc_count_redex_write_fast(redex);
  }

  void gc_count_write(Node const * node)
  {
    // A pinned static object and a literal node are outside the heap.
    if(is_pinned(*node->info) || in_literal_arena(node))
      return;
    Block * b = block_of(node);
    if(b->young)
      return;
    count_old_write(b, slot_of(b, node), g_old_slot_writes);
  }

  void gc_count_slot_write(void const * slot)
  {
    if(!in_heap_map(slot))
      return;
    Block * b = block_of(slot);
    if(b->young || b->kind == BLOCK_EMPTY)
      return;
    if((char const *) slot < block_data(b))
      return;
    uint32_t const i = slot_of(b, slot);
    if(i < b->nslots)
      count_old_write(b, i, g_old_slot_writes);
  }
  #endif

  // Gives the part of every run not yet consumed back to its block (the
  // ``alloc`` bits of a run are set when it is handed out) and empties the
  // runs, so that the bitmaps name every node and nothing else, and the
  // next allocation of each class starts from the lists the sweep builds.
  static void retire_runs()
  {
    for(size_t k = 0; k < g_heap.nactive; ++k)
    {
      size_t const c = g_heap.active[k];
      SizeClass & cls = g_heap.classes[c];
      AllocRun & run = run_of(c);
      Block * b = cls.block;
      if(b && run.free != run.limit)
      {
        clear_bits(b->alloc, slot_of(b, run.free), slot_of(b, run.limit));
        size_t const rest = size_t(run.limit - run.free) / cls.slot_bytes;
        g_handed -= rest;
        g_allocations -= rest;
      }
      cls.block = nullptr;
      cls.active = false;
      run.free = run.limit = nullptr;
    }
    g_heap.nactive = 0;
  }

  static inline bool is_older(Block const * b, bool nested, size_t floor_seq)
    { return nested && b->seq <= floor_seq; }

  // Pushes every allocated slot of every older block (see the header of
  // this file).  retire_runs has run, so the bitmaps are complete.
  static void push_older_nodes(
      std::vector<Node *> & stack, size_t floor_seq
    )
  {
    for(size_t k = 0; k < g_heap.nblocks; ++k)
    {
      Block * b = g_heap.blocks[k];
      if(b->kind == BLOCK_EMPTY || !is_older(b, true, floor_seq))
        continue;
      if(b->kind == BLOCK_LARGE)
      {
        stack.push_back((Node *) block_data(b));
        continue;
      }
      size_t const words = words_of(b);
      for(uint32_t w = 0; w < words; ++w)
      {
        uint64_t bits = b->alloc[w];
        while(bits)
        {
          uint32_t const i = (w << 6) + (uint32_t) __builtin_ctzll(bits);
          stack.push_back((Node *) slot_address(b, i));
          bits &= bits - 1;
        }
      }
    }
  }

  // Sweeps the blocks after a mark phase: counts the survivors, lets
  // ``old`` and ``alloc`` take the marks, builds the pool and the class
  // lists, and frees the spans of dead large nodes.  An older block (a
  // nested collection) keeps its allocation bitmap and is listed nowhere;
  // its marks, every node of it, become its old bits like any other's.
  // Counts the blocks touched by a write into an old node since the last
  // sweep (g_old_blocks) and, with the write counters, the old nodes
  // written (g_old_nodes_written, the dirty bits), and clears both.
  // Returns the survivors.
  static size_t sweep_blocks(bool nested, size_t floor_seq)
  {
    for(size_t c = 0; c < NUM_SIZE_CLASSES; ++c)
      g_heap.classes[c].list = nullptr;
    g_heap.pool = nullptr;
    size_t survivors = 0;
    size_t kept = 0;
    g_old_blocks = 0;
    g_old_nodes_written = 0;
    for(size_t k = 0; k < g_heap.nblocks; ++k)
    {
      Block * b = g_heap.blocks[k];
      if(b->touched)
      {
        ++g_old_blocks;
        #ifdef SPRITE_GC_WRITE_COUNTERS
        size_t const dirty_words = words_of(b);
        g_old_nodes_written += popcount_words(b->dirty, dirty_words);
        std::memset(b->dirty, 0, dirty_words * sizeof(uint64_t));
        #endif
        b->touched = 0;
      }
      switch(b->kind)
      {
        case BLOCK_EMPTY:
          b->next = g_heap.pool;
          g_heap.pool = b;
          g_heap.blocks[kept++] = b;
          break;
        case BLOCK_SMALL:
        {
          size_t const words = words_of(b);
          size_t const live = popcount_words(b->mark, words);
          survivors += live;
          std::memcpy(b->old, b->mark, words * sizeof(uint64_t));
          b->young = live == 0;
          if(is_older(b, nested, floor_seq))
          {
            std::memset(b->mark, 0, words * sizeof(uint64_t));
            g_heap.blocks[kept++] = b;
            break;
          }
          std::memcpy(b->alloc, b->mark, words * sizeof(uint64_t));
          std::memset(b->mark, 0, words * sizeof(uint64_t));
          b->cursor = 0;
          if(live == 0)
          {
            b->kind = BLOCK_EMPTY;
            b->next = g_heap.pool;
            g_heap.pool = b;
          }
          else if(live < b->nslots)
          {
            size_t const c = (b->slot_bytes - MIN_SLOT_BYTES) / SLOT_GRAIN;
            SizeClass & cls = g_heap.classes[c];
            b->next = cls.list;
            cls.list = b;
          }
          g_heap.blocks[kept++] = b;
          break;
        }
        case BLOCK_LARGE:
          if(b->mark[0] & 1)
          {
            b->mark[0] = 0;
            b->old[0] = 1;
            b->young = 0;
            ++survivors;
            g_heap.blocks[kept++] = b;
          }
          else
          {
            assert(!is_older(b, nested, floor_seq));
            free_large(b);
          }
          break;
      }
    }
    g_heap.nblocks = kept;
    g_survivors = survivors;
    g_handed = 0;
    return survivors;
  }

  size_t gc_num_blocks()
  {
    size_t n = 0;
    for(size_t k = 0; k < g_heap.nblocks; ++k)
      if(g_heap.blocks[k]->kind != BLOCK_EMPTY)
        ++n;
    return n;
  }

  size_t gc_heap_bytes()
    { return g_heap.chunks * CHUNK_BYTES + g_heap.large_bytes; }

  size_t gc_num_old_nodes()
  {
    size_t n = 0;
    for(size_t k = 0; k < g_heap.nblocks; ++k)
    {
      Block * b = g_heap.blocks[k];
      if(b->kind == BLOCK_SMALL)
        n += popcount_words(b->old, words_of(b));
      else if(b->kind == BLOCK_LARGE)
        n += b->old[0] & 1;
    }
    return n;
  }

  // The verifier.  See the header of this file.  It runs after a mark
  // phase, before the sweep.  The mark phase lists every node it marks in
  // g_verify_list while g_verifying is set, so the checks cost the marked
  // nodes, not the heap.  The explicit request (gc_verify) and the stress
  // mode check the bitmaps of every block as well, which costs a pass over
  // the blocks, as the sweep does.
  static bool g_verifying = false;
  static std::vector<Node *> g_verify_list;

  // The block of ``p`` when ``p`` is inside a range the heap holds.
  static Block * find_block(void const * p)
  {
    if(!g_heap.ranges)
      return nullptr;
    auto const & ranges = *g_heap.ranges;
    Range const key{(uintptr_t) p, 0};
    auto it = std::upper_bound(ranges.begin(), ranges.end(), key);
    if(it == ranges.begin())
      return nullptr;
    --it;
    if((uintptr_t) p - it->base >= it->bytes)
      return nullptr;
    return block_of(p);
  }

  static std::string describe(
      char const * what, Node const * node, Block const * b
    )
  {
    std::stringstream ss;
    ss << what;
    if(node)
      ss << ": node " << (void const *) node;
    if(b)
      ss << (node ? " in" : ":") << " block " << (void const *) b << " of "
         << b->slot_bytes << "-byte slots";
    return ss.str();
  }

  // Whether ``p`` is the start of a marked slot of a known block.
  static bool marked_slot_start(void const * p)
  {
    Block * b = find_block(p);
    if(!b || b->kind == BLOCK_EMPTY)
      return false;
    if(b->kind == BLOCK_LARGE)
      return p == block_data(b) && (b->mark[0] & 1);
    uint32_t const i = slot_of(b, p);
    return i < b->nslots && slot_address(b, i) == p && test_bit(b->mark, i);
  }

  static std::string verify_node(Node * node)
  {
    Block * b = find_block(node);
    if(!b || b->kind == BLOCK_EMPTY)
      return describe("a marked node outside the heap", node, nullptr);
    uint32_t const i = b->kind == BLOCK_LARGE ? 0 : slot_of(b, node);
    if(i >= b->nslots || slot_address(b, i) != (char *) node)
      return describe("a marked node that is not a slot start", node, b);
    if(!test_bit(b->alloc, i))
      return describe("a mark on a free slot", node, b);
    InfoTable const * info = node->info;
    if(!info)
      return describe("a marked node without an info table", node, b);
    if(info->tag < T_PAD)
      return describe("a marked node with an invalid tag", node, b);
    if(!info->format || info->arity > 8192)
      return describe("a marked node with an invalid arity", node, b);
    if(info->alloc_size > b->slot_bytes)
      return describe("a marked node larger than its slot", node, b);
    Arg const * data = node->begin();
    for(index_type i = 0, e = info->arity; i < e; ++i)
    {
      if(info->format[i] != 'p')
        continue;
      Node * succ = data[i].node;
      if(!succ || in_literal_arena(succ))
        continue;
      if(is_pinned(*succ->info))
      {
        if((Node const *) succ->info->step != succ)
          return describe(
              "a successor is a heap copy of a pinned constructor", node, b
            );
        continue;
      }
      if(!marked_slot_start(succ))
        return describe("a successor is not a marked node", node, b);
    }
    return std::string();
  }

  // Checks a node Python holds.  The mark phase skips a node with a pinned
  // info table, so a heap copy of a pinned constructor is never marked and
  // never listed; it is found here, by its address.
  static std::string verify_root(Node * node)
  {
    if(in_literal_arena(node))
      return std::string();
    if(is_pinned(*node->info))
    {
      if((Node const *) node->info->step != node)
        return describe(
            "a root is a heap copy of a pinned constructor", node
          , find_block(node)
          );
      return std::string();
    }
    if(!marked_slot_start(node))
      return describe("a root is not a marked node", node, find_block(node));
    return std::string();
  }

  // Checks the nodes the mark phase listed and the nodes Python holds.
  // With ``blocks`` the bitmaps of every block are checked as well: an empty
  // block has no bit set, the marks and the old bits of a block are within
  // its slots and its allocated bits, and a dirty bit (the write counters)
  // is on an old slot.
  static std::string verify_heap(bool blocks)
  {
    for(Node * node: g_verify_list)
    {
      std::string problem = verify_node(node);
      if(!problem.empty())
        return problem;
    }
    for(auto const & pair: g_roots)
    {
      std::string problem = verify_root(pair.first);
      if(!problem.empty())
        return problem;
    }
    if(!blocks)
      return std::string();
    for(size_t k = 0; k < g_heap.nblocks; ++k)
    {
      Block * b = g_heap.blocks[k];
      if(b->kind == BLOCK_EMPTY)
      {
        if(any_bit(b->mark, BITMAP_WORDS) || any_bit(b->alloc, BITMAP_WORDS)
            || any_bit(b->old, BITMAP_WORDS))
          return describe("an empty block with a set bit", nullptr, b);
        #ifdef SPRITE_GC_WRITE_COUNTERS
        if(any_bit(b->dirty, BITMAP_WORDS))
          return describe("an empty block with a set bit", nullptr, b);
        #endif
        continue;
      }
      size_t const words = words_of(b);
      for(size_t w = 0; w < words; ++w)
      {
        if(b->mark[w] & ~b->alloc[w])
          return describe("a mark on a free slot", nullptr, b);
        if(b->old[w] & ~b->alloc[w])
          return describe("an old bit on a free slot", nullptr, b);
        #ifdef SPRITE_GC_WRITE_COUNTERS
        if(b->dirty[w] & ~b->old[w])
          return describe("a dirty bit on a slot that is not old", nullptr, b);
        #endif
      }
      if(any_bit(b->mark + words, BITMAP_WORDS - words)
          || any_bit(b->alloc + words, BITMAP_WORDS - words)
          || any_bit(b->old + words, BITMAP_WORDS - words))
        return describe("a bit beyond the last slot", nullptr, b);
      #ifdef SPRITE_GC_WRITE_COUNTERS
      if(any_bit(b->dirty + words, BITMAP_WORDS - words))
        return describe("a bit beyond the last slot", nullptr, b);
      #endif
    }
    return std::string();
  }
}
