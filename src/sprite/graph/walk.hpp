#pragma once
#include <deque>
#include "sprite/graph/node.hpp"
#include <unordered_set>
#include <vector>

namespace sprite
{
  using datadisposer_type = void(*)(void * static_data, void * data);
  struct Walk;
  struct Walk2;

  Walk walk(Cursor root);
  Walk2 walk(Cursor root, void * static_data, datadisposer_type);

  // Walk a graph.
  struct Walk
  {
    Walk() {}
    Walk(Cursor root);
    explicit operator bool() const;
    void operator++();
    void push();
    Cursor cursor() const;
  private:
    void pop();
    struct Frame
    {
      Cursor cur;
      index_type index = (index_type)(-1);
      index_type end = 0;
    };
    std::vector<Frame> stack;
  };

  // Walk a graph, with support for contextual data.
  struct Walk2
  {
    Walk2() {}
    Walk2(Cursor root, void * static_data, datadisposer_type);
    explicit operator bool() const;
    void operator++();
    void push(void * data=nullptr);
    Cursor cursor() const;
    void *& data() const;
  private:
    void pop();
    struct Frame
    {
      Cursor         cur;
      mutable void * data = nullptr;
      index_type     index = (index_type)(-1);
      index_type     end = 0;

      Frame(void * data) : data(data) {}
      Frame(Cursor const & cur, void * data=nullptr) : cur(cur), data(data) {}
    };
    std::vector<Frame>  stack;
    void *              static_data;
    datadisposer_type   dispose;
  };

  struct UniqueNodeVisitor
  {
    UniqueNodeVisitor(Node * root) : queue({root}) {}
    Node * next();
    std::deque<Node*> queue;
    std::unordered_set<Node*> seen;
  };

  inline UniqueNodeVisitor visit_unique(Node * root)
      { return UniqueNodeVisitor(root); }
}

#include "sprite/graph/walk.hxx"
