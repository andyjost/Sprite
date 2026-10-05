#pragma once
#include "cyrt/fwd.hpp"
#include "cyrt/graph/memory.hpp"
#include <cstdint>

// The block of the node heap (gc/blockheap.cpp): its constants, its
// header, and the address arithmetic that finds the block and the slot of
// a node.  This header exists so that the scheduler can test the age of a
// redex inline (gc_count_redex_write_fast, below); gc/blockheap.cpp holds
// everything else.  It is not installed: generated code never sees a block.

namespace cyrt
{
  static constexpr size_t BLOCK_BYTES = size_t(64) << 10;
  static constexpr size_t CHUNK_BYTES = size_t(1) << 20;
  static constexpr size_t BLOCKS_PER_CHUNK = CHUNK_BYTES / BLOCK_BYTES;
  static constexpr size_t MAX_SLOTS = BLOCK_BYTES / MIN_SLOT_BYTES;
  static constexpr size_t BITMAP_WORDS = MAX_SLOTS / 64;
  static_assert(BLOCK_BYTES % MIN_SLOT_BYTES == 0, "");
  static_assert(CHUNK_BYTES % BLOCK_BYTES == 0, "");
  static_assert(MAX_SLOTS % 64 == 0, "");

  enum BlockKind : uint32_t
    { BLOCK_EMPTY = 0, BLOCK_SMALL = 1, BLOCK_LARGE = 2 };

  struct Block
  {
    uint32_t kind;
    uint32_t slot_bytes; // the size of a slot; of the node, for a large one
    uint32_t slot_magic; // ceil(2^32 / slot_bytes); zero for a large node
    uint32_t nslots;     // slots in the block; one for a large node
    size_t   seq;        // the time the block left the pool (see blockheap.cpp)
    Block *  next;       // the next block of the pool or of a class list
    uint32_t cursor;     // the first slot the lazy sweep has not examined
    uint32_t spans;      // blocks in the span of a large node; one otherwise
    // The age of the block, for the counters of writes into old nodes (see
    // gc/wdgc.cpp).  ``young``: no node of the block survived the last
    // collection, so every node in it is young.  ``touched``: a write into
    // an old node of the block was counted since the last collection.
    uint8_t  young;
    uint8_t  touched;
    #ifdef SPRITE_SCHEDULER_COUNTERS
    size_t * creators;   // the creator of the node in each slot
    #endif
    uint64_t alloc[BITMAP_WORDS]; // the slots that hold a node
    uint64_t mark[BITMAP_WORDS];  // the marks of the current collection
    uint64_t old[BITMAP_WORDS];   // the marks of the last collection
    #ifdef SPRITE_GC_WRITE_COUNTERS
    // The old slots written since the last sweep: the distinct old nodes a
    // write barrier would have recorded.  The sweep counts and clears them.
    uint64_t dirty[BITMAP_WORDS];
    #endif
  };

  // The slots start here.  Every slot size is a multiple of the grain, so
  // every slot is aligned to it.
  static constexpr size_t DATA_OFFSET = (sizeof(Block) + 15) & ~size_t(15);
  static_assert(DATA_OFFSET % 16 == 0, "");
  static_assert((BLOCK_BYTES - DATA_OFFSET) / MIN_SLOT_BYTES <= MAX_SLOTS, "");
  // The offset of a slot fits the reciprocal multiplication of slot_of.
  static_assert(BLOCK_BYTES <= (size_t(1) << 16), "");

  inline char * block_data(Block * b)
    { return (char *) b + DATA_OFFSET; }

  // The words of a bitmap that cover the slots of a block.  The bits beyond
  // the last slot are never set.
  inline size_t words_of(Block const * b)
    { return (size_t(b->nslots) + 63) >> 6; }

  inline Block * block_of(void const * p)
    { return (Block *) ((uintptr_t) p & ~(uintptr_t) (BLOCK_BYTES - 1)); }

  // The slot of an address in its block.  Exact for a slot start: the
  // offset is below 2^16 and the error of the reciprocal is below 2^-32 per
  // byte.  For another address the result is the slot that holds it.  Zero
  // in the block of a large node, whose magic is zero.
  inline uint32_t slot_of(Block const * b, void const * p)
  {
    char const * const data = (char const *) b + DATA_OFFSET;
    uint32_t const offset = (uint32_t) ((char const *) p - data);
    return (uint32_t) (((uint64_t) offset * b->slot_magic) >> 32);
  }

  inline char * slot_address(Block * b, uint32_t i)
    { return block_data(b) + size_t(i) * b->slot_bytes; }

  inline bool test_bit(uint64_t const * bits, uint32_t i)
    { return (bits[i >> 6] >> (i & 63)) & 1; }

  inline void set_bit(uint64_t * bits, uint32_t i)
    { bits[i >> 6] |= uint64_t(1) << (i & 63); }

  // The counter of the writes of a step into its redex (see gc/wdgc.cpp).
  // The fast path, for the scheduler: the flag of the block.  The slow
  // path tests the bit of the slot and counts.  Compiled in under
  // SPRITE_GC_WRITE_COUNTERS; gc_count_redex_write of memory.hpp is the
  // out-of-line form.
  void gc_count_redex_write_slow(Node const *, Block *);

  inline void gc_count_redex_write_fast(Node const * redex)
  {
    Block * b = block_of(redex);
    if(__builtin_expect(!b->young, 0))
      gc_count_redex_write_slow(redex, b);
  }
}
