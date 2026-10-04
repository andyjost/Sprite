#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>
#include "cyrt/fwd.hpp"
#include <type_traits>

namespace cyrt
{
  // The heap fallback of SmallVec.  Both live in the runtime library, so a
  // generated module imports no allocator for its variables.
  void * smallvec_alloc(size_t bytes);
  void smallvec_free(void * block);

  // A sequence of plain values with room for N of them inside the object.
  // A longer sequence moves to a heap block.  Variable keeps its path and
  // its set guards in two of these, so an argument access in a step makes
  // no heap call.  Only the operations the runtime needs are provided.
  template<typename T, unsigned N>
  struct SmallVec
  {
    static_assert(std::is_trivially_copyable<T>::value, "plain values only");
    static_assert(N > 0, "no inline room");

    static constexpr unsigned inline_capacity = N;

    SmallVec() noexcept : size_(0), capacity_(N) {}
    SmallVec(SmallVec const & other) : SmallVec() { this->assign(other); }
    SmallVec(SmallVec && other) noexcept : SmallVec() { this->take(other); }
    ~SmallVec() { this->release(); }

    SmallVec & operator=(SmallVec const & other)
    {
      if(this != &other)
        this->assign(other);
      return *this;
    }

    SmallVec & operator=(SmallVec && other) noexcept
    {
      if(this != &other)
      {
        this->release();
        this->size_ = 0;
        this->capacity_ = N;
        this->take(other);
      }
      return *this;
    }

    bool empty() const noexcept { return this->size_ == 0; }
    size_t size() const noexcept { return this->size_; }
    size_t capacity() const noexcept { return this->capacity_; }
    // True while the values live inside the object.
    bool is_inline() const noexcept { return this->capacity_ == N; }

    T * data() noexcept
      { return this->is_inline() ? this->buf_ : this->heap_; }
    T const * data() const noexcept
      { return this->is_inline() ? this->buf_ : this->heap_; }
    T * begin() noexcept { return this->data(); }
    T * end() noexcept { return this->data() + this->size_; }
    T const * begin() const noexcept { return this->data(); }
    T const * end() const noexcept { return this->data() + this->size_; }
    T & operator[](size_t i) noexcept { return this->data()[i]; }
    T const & operator[](size_t i) const noexcept { return this->data()[i]; }
    T & back() noexcept { return this->data()[this->size_ - 1]; }
    T const & back() const noexcept { return this->data()[this->size_ - 1]; }

    void push_back(T value)
    {
      if(this->size_ == this->capacity_)
        this->grow(size_t(this->size_) + 1);
      this->data()[this->size_++] = value;
    }

    void pop_back() noexcept { --this->size_; }

    // Keeps the capacity.
    void clear() noexcept { this->size_ = 0; }

    // Sets the size.  A new value is value-initialized.  Keeps the capacity.
    void resize(size_t n)
    {
      if(n > this->capacity_)
        this->grow(n);
      T * data = this->data();
      for(size_t i = this->size_; i < n; ++i)
        data[i] = T();
      this->size_ = uint32_t(n);
    }

    // Appends the values of [first, last).
    void append(T const * first, T const * last)
    {
      size_t const count = last - first;
      if(count == 0)
        return;
      if(this->size_ + count > this->capacity_)
        this->grow(this->size_ + count);
      std::memcpy(this->data() + this->size_, first, count * sizeof(T));
      this->size_ += count;
    }

    friend bool operator==(SmallVec const & lhs, SmallVec const & rhs) noexcept
    {
      return lhs.size_ == rhs.size_
          && std::memcmp(lhs.data(), rhs.data(), lhs.size_ * sizeof(T)) == 0;
    }
    friend bool operator!=(SmallVec const & lhs, SmallVec const & rhs) noexcept
      { return !(lhs == rhs); }

  private:
    // Replaces the values with those of ``other``.  Two inline objects copy
    // the whole inline room: a fixed size, so no call to memcpy.
    void assign(SmallVec const & other)
    {
      if(this->is_inline() && other.is_inline())
      {
        std::memcpy(this->buf_, other.buf_, sizeof(this->buf_));
        this->size_ = other.size_;
      }
      else
      {
        this->size_ = 0;
        this->append(other.begin(), other.end());
      }
    }

    // Moves the values of ``other`` into this empty, inline object.
    void take(SmallVec & other) noexcept
    {
      if(other.is_inline())
        std::memcpy(this->buf_, other.buf_, sizeof(this->buf_));
      else
      {
        this->heap_ = other.heap_;
        this->capacity_ = other.capacity_;
        other.capacity_ = N;
      }
      this->size_ = other.size_;
      other.size_ = 0;
    }

    void release() noexcept
    {
      if(!this->is_inline())
        smallvec_free(this->heap_);
    }

    // Moves the values to a heap block with room for ``need`` of them.  Out
    // of line: the step functions keep only the call.
    __attribute__((noinline, cold)) void grow(size_t need)
    {
      size_t capacity = 2 * size_t(this->capacity_);
      if(capacity < need)
        capacity = need;
      T * block = static_cast<T *>(smallvec_alloc(capacity * sizeof(T)));
      std::memcpy(block, this->data(), size_t(this->size_) * sizeof(T));
      this->release();
      this->heap_ = block;
      this->capacity_ = uint32_t(capacity);
    }

    uint32_t size_;
    uint32_t capacity_; // N while inline, more on the heap
    union
    {
      T   buf_[N];
      T * heap_;
    };
  };

  // The path of a variable from the root of its step, and the set guards
  // crossed on the way.  A path has one entry per subscript, forward node,
  // and set guard crossed; the inline room covers the nesting of ordinary
  // patterns.  Guards appear inside set functions only.
  using RealPath  = SmallVec<index_type, 8>;
  using GuardList = SmallVec<Set *, 2>;
}
