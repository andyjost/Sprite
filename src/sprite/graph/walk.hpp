#pragma once
#include "sprite/graph/node.hpp"
#include <vector>

namespace sprite
{
  using datadisposer_type = void(*)(void * static_data, void * data);

  struct Walk
  {
    Walk() {}
    Walk(Cursor root, void * static_data=nullptr, datadisposer_type=nullptr);

    explicit operator bool() const;
    void operator++();
    void pop();
    void push(void * data=nullptr);
    void extend(index_type pos);
    void extend(index_type const * path);

    size_t size() const { return this->stack.size(); }
    void resize(size_t n) { this->stack.resize(n); }

    Cursor root() const;
    Cursor cursor() const;
    Cursor at(size_t n) const { return this->stack[n].cur; }
    void *& data() const;

    Node * copy_spine(Node * root, Node * end, Cursor * target=nullptr);

  private:

    struct Frame
    {
      Cursor cur;
      void * data = nullptr;
      index_type index = (index_type)(-1);
      index_type end = 0;

      Frame() {}
      Frame(void * data) : data(data) {}
      Frame(Cursor const & cur, void * data=nullptr)
        : cur(cur), data(data)
      {}
    };

    mutable std::vector<Frame> stack;
    void *                     static_data;
    datadisposer_type          dispose;
  };

  template<typename ... Args>
  Walk walk(Args && ... args)
    { return Walk(std::forward<Args>(args)...); }
}
