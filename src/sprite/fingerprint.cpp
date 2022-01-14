#include "sprite/fingerprint.hpp"
#include <new>

namespace sprite { namespace fingerprints
{
  boost::pool<> branch_pool(sizeof(Branch));

  #if defined(USE_FP_CACHE) && defined(FP_CACHE_DIAGNOSTICS)
  size_t cache_tries;
  size_t cache_hits;
  size_t cache_total_depth;
  #endif

  Branch::Branch(Branch * branch, size_t refs) : refcount(refs)
  {
    for(size_t i=0; i<FP_BRANCH_SIZE; ++i)
      next[i].branch = branch;
    branch->refcount += FP_BRANCH_SIZE;
  }

  Branch::Branch(Branch * first, Branch * rest, size_t refs) : refcount(refs)
  {
    next[0].branch = first; // Note: no change to first->refcount.
    for(size_t i=1; i<FP_BRANCH_SIZE; ++i)
      next[i].branch = rest;
    rest->refcount += FP_BRANCH_SIZE - 1;
  }

  void Branch::make_unique(Node & slot, size_t depth)
  {
    if(refcount > 1)
    {
      refcount--;
      auto copy = new Branch(1);
      if(depth == 0)
      {
        for(size_t i=0; i<FP_BRANCH_SIZE; ++i)
          copy->next[i].block = next[i].block;
      }
      else
      {
        for(size_t i=0; i<FP_BRANCH_SIZE; ++i)
        {
          auto p = next[i].branch;
          copy->next[i].branch = p;
          p->refcount++;
        }
      }
      slot.branch = copy;
    }
  }

  void Branch::release(size_t depth)
  {
    if(depth>0) // safe to call with typeof(*this) == Block.
    {
      if(--refcount == 0)
      {
        depth--;
        for(size_t i=0; i<FP_BRANCH_SIZE; ++i)
          next[i].branch->release(depth);
        delete this;
      }
    }
  }

  Node::Node(Node const & arg, size_t depth)
  {
    if(depth != 0)
    {
      branch = arg.branch;
      branch->refcount++;
    }
    else
      block = arg.block;
  }
}}

namespace sprite
{
  Fingerprint::Fingerprint(Fingerprint const & arg)
    : m_depth(arg.m_depth)
    , m_capacity(arg.m_capacity)
    , m_root(arg.m_root, m_depth)
  {
    #ifdef USE_FP_CACHE
    arg.m_cachedblock = nullptr;
    #endif
  }

  Fingerprint::Fingerprint(Fingerprint && arg)
    : m_depth(arg.m_depth)
    , m_capacity(arg.m_capacity)
    , m_root(arg.m_root, m_depth)
  {
    #ifdef USE_FP_CACHE
    arg.m_cachedblock = nullptr;
    #endif
  }

  Fingerprint & Fingerprint::operator=(Fingerprint const & arg)
  {
    if(this != &arg)
    {
      m_root.branch->release(m_depth); // safe if this is in the "block" state
      m_depth = arg.m_depth;
      m_capacity = arg.m_capacity;
      new(&this->m_root) Node(arg.m_root, m_depth);
      #ifdef USE_FP_CACHE
      m_cachedblock = arg.m_cachedblock = nullptr;
      #endif
    }
    return *this;
  }

  void Fingerprint::set_left_no_check(size_t id)
  {
    auto & block = write_block(id);
    size_t const offset = id & FP_BLOCK_MASK;
    block.used |= (1 << offset);
    block.lr &= ~(1 << offset);
  }

  void Fingerprint::set_right_no_check(size_t id)
  {
    auto & block = write_block(id);
    size_t const offset = id & FP_BLOCK_MASK;
    block.used |= (1 << offset);
    block.lr |= (1 << offset);
  }

  void Fingerprint::check_alloc(size_t id) const
  {
    while(id >= m_capacity)
    {
      if(m_depth == 0)
        m_root.branch = new Branch(m_root.block, 1);
      else
      {
        Branch * p = new Branch(0);
        for(auto i=1; i<m_depth; ++i)
          p = new Branch(p, 0);
        // Note: no change to m_root.branch->refcount below (for the node
        // currently there).
        assert(p->refcount == 0);
        m_root.branch = new Branch(m_root.branch, p, 1);
      }
      m_depth += 1;
      m_capacity <<= FP_BRANCH_SHIFT;
    }
  }

  ChoiceState Fingerprint::test(size_t id) const
  {
    check_alloc(id);
    return test_no_check(id);
  }

  ChoiceState Fingerprint::test_no_check(size_t id) const
  {
    auto & block = read_block(id);
    size_t const offset = id & FP_BLOCK_MASK;
    return (block.used & (1<<offset))
        ? (block.lr & (1<<offset)) ? RIGHT : LEFT
        : UNDETERMINED;
  }

  bool Fingerprint::choice_is_made(size_t id) const
  {
    if(id >= m_capacity) return false;
    auto & block = read_block(id);
    size_t const offset = id & FP_BLOCK_MASK;
    return block.used & (1 << offset);
  }

  #ifdef USE_FP_CACHE
  bool Fingerprint::try_cache(size_t id, bool writable) const
  {
    #ifdef FP_CACHE_DIAGNOSTICS
    fingerprints::cache_tries++;
    fingerprints::cache_total_depth += m_depth;
    #endif
    if(m_cachedblock && (id &~ FP_CACHE_TAG_MASK) == m_cachetag)
    {
      if(!writable || m_cachetag & FP_CACHE_WRITABLE)
      {
        #ifdef FP_CACHE_DIAGNOSTICS
        fingerprints::cache_hits++;
        #endif
        return true;
      }
    }
    return false;
  }
  #endif

  // Locates the block containing @p id for read access.
  auto Fingerprint::read_block(size_t id) const -> Block const &
  {
    #ifdef USE_FP_CACHE
    if(try_cache(id, false)) return *m_cachedblock;
    #endif

    Node * p = &m_root;
    for(auto i=m_depth-1; i>=0; --i)
    {
      auto selector = id >> (i * FP_BRANCH_SHIFT + FP_BLOCK_SHIFT);
      auto which = FP_BRANCH_MASK & selector;
      p = &p->branch->next[which];
    }
    #ifdef USE_FP_CACHE
    m_cachedblock = &p->block;
    m_cachetag = id &~ FP_CACHE_TAG_MASK;
    #endif
    return p->block;
  }

  // Locates the block containing @p id for write access.
  auto Fingerprint::write_block(size_t id) const -> Block &
  {
    #ifdef USE_FP_CACHE
    if(try_cache(id, true)) return *m_cachedblock;
    #endif

    Node * p = &m_root;
    for(auto i=m_depth-1; i>=0; --i)
    {
      auto selector = id >> (i * FP_BRANCH_SHIFT + FP_BLOCK_SHIFT);
      auto which = FP_BRANCH_MASK & selector;
      p->branch->make_unique(*p, i); // copy-on-write
      p = &p->branch->next[which];
    }
    #ifdef USE_FP_CACHE
    m_cachedblock = &p->block;
    m_cachetag = (id &~ FP_CACHE_TAG_MASK) | FP_CACHE_WRITABLE;
    #endif
    return p->block;
  }
}
