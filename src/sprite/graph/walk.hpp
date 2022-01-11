#pragma once
#include "sprite/graph/node.hpp"

namespace sprite
{
  using datadisposer_type = void(*)(void * static_data, void * data);

  struct WalkState
  {
    WalkState(
        Cursor root
      , index_type const * realpath=nullptr
      , void * static_data=nullptr
      , datadisposer_type=nullptr
      , void * data=nullptr
      );

    explicit operator bool() const { return !this->spine.empty(); }
    void operator++();

    void pop();
    void push(void * data=nullptr);

    Cursor cursor();
    Cursor parent();
    void *& data() { return data_.back(); }
    index_type const * realpath() const { return realpath_.data(); }

  private:

    struct Successor { Cursor succ; index_type index; };
    using Frame = std::vector<Successor>;
    std::vector<Frame>      stack;
    std::vector<index_type> realpath_;
    std::vector<Cursor>     spine;
    std::vector<void *>     data_;
    void *                  static_data;
    datadisposer_type       dispose;
  };

  template<typename ... Args>
  WalkState walk(Args && ... args)
    { return WalkState(std::forward<Args>(args)...); }
}
