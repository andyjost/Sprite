#pragma once
#include <deque>
#include "sprite/graph/node.hpp"
#include <unordered_set>
#include <vector>

namespace sprite
{
  using datadisposer_type = void(*)(void * static_data, void * data);

  struct Search
  {
    Search() {}
    Search(Cursor root, void * static_data=nullptr, datadisposer_type=nullptr);

    explicit operator bool() const;
    void operator++();
    void pop();
    void push(void * data=nullptr);
    void extend(index_type pos);
    void extend(index_type const * path);
    size_t extend(RealpathResult const *);

    size_t size() const { return this->stack.size(); }
    void resize(size_t n) { this->stack.resize(n); }

    void set_barrier();

    Cursor root() const;
    Cursor cursor() const;
    Cursor at(size_t n) const { return this->stack[n].cur; }
    void *& data() const;
    void reset();

    Node * copy_spine(
        Node * root, Node * end, Cursor * target=nullptr
      , size_t start=1
      );
    Node * copy_spine(Node * root, Node * end, size_t start);

  private:

    struct Frame
    {
      Cursor cur;
      void * data = nullptr;
      index_type index = (index_type)(-1);
      index_type end = 0;
      index_type barrier = 0;

      Frame() {}
      Frame(void * data) : data(data) {}
      Frame(Cursor const & cur, void * data=nullptr)
        : cur(cur), data(data)
      {}
    };

    mutable std::vector<Frame> stack;
    void *                     static_data;
    datadisposer_type          dispose;
    bool                       bad = false;
  };

  template<typename ... Args>
  Search walk(Args && ... args)
    { return Search(std::forward<Args>(args)...); }

  struct NodeIterator
  {
    NodeIterator(Node * root) : queue({root}) {}
    Node * next();
    std::deque<Node*> queue;
    std::unordered_set<Node*> seen;
  };

  inline NodeIterator iternodes(Node * root) { return NodeIterator(root); }
}
