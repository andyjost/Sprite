#pragma once
#include "cyrt/graph/node.hpp"
#include <vector>

namespace cyrt
{
  struct Scan
  {
    Scan() {}
    Scan(Cursor root);

    explicit operator bool() const;
    void operator++();
    void extend();
    void push(Variable const *);
    void pop();
    Cursor cursor() const;
    size_t size() const;
    void resize(size_t);
    void reset();
    Node * copy_spine(
        Node * root, Node * end, xid_type cid=NOXID
      , Cursor * target=nullptr, size_t start=1
      );
    Node * copy_spine(Node * root, Node * end, xid_type cid, size_t start);
    struct Level
    {
      Cursor cur;
      index_type index = (index_type)(-1);
      index_type end = 0;

      Level(Cursor const & cur=Cursor()) : cur(cur) {}
    };
  private:
    std::vector<Level>  search;
    std::vector<size_t> callstack;
  public:
    std::vector<Level> const & frames() const { return search; }
  };
}

#include "cyrt/state/scan.hxx"
