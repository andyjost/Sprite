// Implements @p Fingerprint as a tree to minimize copying.
//
// The tree comprises branch nodes and (leaf) block nodes.  Only blocks contain
// fingerprint data, indicating whether a particular choice has been made and
// whether it is LEFT or RIGHT.  Each block holds FP_BLOCK_SIZE elements of the
// fingerprint.  Internal (branch) nodes each have FP_BRANCH_SIZE children and
// a reference count, which is used to implement a copy-on-write policy.
// Early, when very few choice IDs have been introduced to the program, a
// fingerprint tree is nothing more than a block node.  As larger IDs are
// introduced, levels are added to the fingerprint trees so that they can
// accomodate more choices.  For instance, when the size first becomes larger
// than FP_BLOCK_SIZE, a branch node is inserted and filled with zeroed-out
// blocks.  Because of the copy-on-write policy, the FP_BRANCH_SIZE-1 new
// blocks are actually references to the same block.
//
// Given an ID, the corresponding block is located as follows based on the
// current tree depth.  First, we store the offset by selected the
// FP_BLOCK_MASK bits of the ID and right-shift those bits away.  Then, working
// from most significant to least significant bits, we select groups of
// FP_BRANCH_MASK bits.  Each group provides an index into branch node at the
// current depth (beginning with the root).  The depth of the fingerprint tree
// indicates how many groups to process.
//
// A simple cache is implemented.  It stores the most-recently-used block and
// its associated tag.  When choices from the same block are used in a
// temporally localized fashion, this avoids repeatedly traversing the branches
// of the tree.
//
// Examples
// --------
//
// 1) A fingerprint tree with depth=0.  It contains FP_BLOCK_SIZE choices.
//
//    ==BLOCK==
//     used=...   (FP_BLOCK_SIZE bits indicating which IDs are used)
//     lr=...     (FP_BLOCK_SIZE bits indicating LEFT/RIGHT for used IDs).
//    =========
//
// 2) A fingerprint tree with depth=1 (depicted for FP_BRANCH_SIZE=4).  It
// contains FP_BRANCH_SIZE * FP_BLOCK_SIZE choices.  Each increment of the
// depth increases the number of IDs by a factor of FP_BRANCH_SIZE.
//
//                     ====BRANCH====
//                      refcount=...
//                     ==============
//                    /    /    \    \                .
//                 /      /      \      \             .
//              /        /        \        \          .
//           /          /          \          \       .
//        /            /            \            \    .
//    ==BLOCK==    ==BLOCK==    ==BLOCK==    ==BLOCK==
//     used=...     used=...     used=...     used=...
//     lr=...       lr=...       lr=...       lr=...
//    =========    =========    =========    =========
//
#pragma once

// The cache is broken.  The unit tests will fail if it is activated.
// #define USE_FP_CACHE
// #define FP_CACHE_DIAGNOSTICS

#include <cassert>
#include "boost/integer.hpp"
#include "boost/integer/static_log2.hpp"
#include "boost/pool/pool.hpp"
#include "sprite/fwd.hpp"

namespace sprite
{
  // Each bit block contains however many choices fit into one pointer (each
  // choice requires two bits).  On x86_64, for instance, there are 32 choices
  // per block.
  size_t constexpr FP_BLOCK_SIZE = sizeof(void*)*8/2;
  size_t constexpr FP_BLOCK_SHIFT = boost::static_log2<FP_BLOCK_SIZE>::value;
  size_t constexpr FP_BLOCK_MASK = FP_BLOCK_SIZE-1;

  // Each branch has four successors.  FP_BRANCH_SHIFT can be tuned.
  size_t constexpr FP_BRANCH_SHIFT = 3;
  size_t constexpr FP_BRANCH_SIZE = 1<<FP_BRANCH_SHIFT;
  size_t constexpr FP_BRANCH_MASK = FP_BRANCH_SIZE-1;

  size_t constexpr FP_CACHE_WRITABLE = (1L<<(8*sizeof(size_t)-1));
  size_t constexpr FP_CACHE_TAG_MASK = ~(FP_BLOCK_MASK | FP_CACHE_WRITABLE);

  namespace fingerprints
  {
    struct Branch;

    // The pool used to allocate branches.
    extern boost::pool<> branch_pool;

    // Stores FP_BLOCK_SIZE bits of fingerprint data.  If the @p used bit is set,
    // then the corresponding choice is made.  If so, then @p lr indicates
    // whether that choice is left or right.
    struct Block
    {
      boost::int_t<FP_BLOCK_SIZE>::exact used = 0;
      boost::int_t<FP_BLOCK_SIZE>::exact lr = 0;
    };

    // Holds either a branch or block (leaf).
    union Node
    {
      Block block;
      Branch * branch;
      static_assert(sizeof(Block) == sizeof(Branch*), "bad sizes in union Node");

      Node() : block() {}
      Node(Node const & arg, size_t depth);

      // Conventional copy is forbidden (the depth argument is required).
      Node(Node const & arg) = delete;
      Node(Node && arg) = delete;
      Node & operator=(Node const & arg) = delete;
      Node & operator=(Node && arg) = delete;
    };


    // Stores FP_BRANCH_SIZE successors and a reference count.
    struct Branch
    {
      Node next[FP_BRANCH_SIZE];
      size_t refcount;

      Branch(size_t refs) : next(), refcount(refs) {}

      // Construct a terminal branch.  The first block of bits is copied.  The
      // rest are set to zero.
      Branch(Block const & block, size_t refs) : next(), refcount(refs)
        { next[0].block = block; }

      // Construct a non-terminal branch, up one level in the tree, where all
      // successors point to @p branch.
      Branch(Branch * branch, size_t refs);

      // Construct a non-terminal branch, up one level in the tree, where the
      // first branch points to @p branch and the rest point to @p rest.
      Branch(Branch * first, Branch * rest, size_t refs);

      // Forces a copy, if necessary.
      void make_unique(Node & slot, size_t depth);

      // Release this branch.  Decrement its reference count and reclaim
      // resources as required.
      void release(size_t depth);

      void * operator new(size_t sz) { return branch_pool.malloc(); }
      void operator delete(void * px) { branch_pool.free(px); }
    };

    #if defined(USE_FP_CACHE) && defined(FP_CACHE_DIAGNOSTICS)
    extern size_t cache_tries;
    extern size_t cache_hits;
    extern size_t cache_total_depth;
    #endif
  }

  // Implements the fingerprint as a tree structure.
  struct Fingerprint
  {
  private:

    using Branch = fingerprints::Branch;
    using Block = fingerprints::Block;
    using Node = fingerprints::Node;

  public:

    Fingerprint() {}
    Fingerprint(Fingerprint const &);
    Fingerprint(Fingerprint && arg);
    Fingerprint & operator=(Fingerprint const & arg);
    Fingerprint & operator=(Fingerprint && arg) { return (*this = arg); }
    ~Fingerprint() { m_root.branch->release(m_depth); }

    void set_left(size_t id) { check_alloc(id); set_left_no_check(id); }
    void set_right(size_t id) { check_alloc(id); set_right_no_check(id); }
    void set_left_no_check(size_t id);
    void set_right_no_check(size_t id);

    // Check that the tree has enough space for @p id choices.  Expand it if
    // necessary.
    void check_alloc(size_t id) const;
    ChoiceState test(size_t id) const;
    ChoiceState test_no_check(size_t id) const;
    bool choice_is_made(size_t id) const;
    bool choice_is_left_no_check(size_t id) const
      { return test_no_check(id) == LEFT; }
    size_t capacity() const { return m_capacity; }
    size_t depth() const { return m_depth; } // size_t not int is OK.
    Node const & root() const { return m_root; }

  private:

    #ifdef USE_FP_CACHE
    bool try_cache(size_t id, bool writable) const;
    #endif

    // Locates the block containing @p id for read access.
    Block const & read_block(size_t id) const;

    // Locates the block containing @p id for write access.
    Block & write_block(size_t id) const;

    #ifdef USE_FP_CACHE
    // Contains the cached block, if there is one.
    mutable Block * m_cachedblock = nullptr;

    // The tag associated with the cached block.  Ignored if @p m_cachedblock is
    // null.
    mutable size_t m_cachetag;
    #endif

    // Counts the number of levels of branches occurring above the blocks.  A
    // signed integer is used because negative values are used in the
    // implementation as loop variables.
    mutable int m_depth = 0;

    // The largest ID representable in the current tree, plus one.
    mutable size_t m_capacity = FP_BLOCK_SIZE;

    // The root of the tree structure containing fingerprint data.
    mutable Node m_root;
  };
}
