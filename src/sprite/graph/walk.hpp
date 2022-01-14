#pragma once
#include "sprite/graph/node.hpp"

namespace sprite
{
  using datadisposer_type = void(*)(void * static_data, void * data);

  struct Walk
  {
    Walk() {}
    Walk(Cursor root, void * static_data=nullptr, datadisposer_type =nullptr);

    explicit operator bool() const;
    void operator++();

    void pop();
    void push(void * data=nullptr);

    Cursor & root();
    Cursor & cursor();
    void *& data();

    Node * copy_spine(Node * end);

  private:

    struct Frame
    {
      Cursor cur;
      void * data;
      index_type index = NOINDEX - 1;
      index_type end;

      Frame(Cursor cur=Cursor(), void * data=nullptr)
        : cur(cur), data(data)
        , end(cur.kind == 'p' ? cur->node->info->arity : 0)
      {}
      explicit operator bool() const { return index < end; }
    };

    std::vector<Frame>      stack;
    void *                  static_data;
    datadisposer_type       dispose;
  };

  template<typename ... Args>
  Walk walk(Args && ... args)
    { return Walk(std::forward<Args>(args)...); }
}
