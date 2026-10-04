#pragma once
#include "cyrt/graph/node.hpp"
#include "cyrt/smallvec.hpp"

namespace cyrt
{
  // The position of the scan of a configuration: one level per nesting of
  // the expression on the way from the root to the current position, and
  // the levels at which the nested evaluations of a step began (push and
  // pop).  Both have inline room (see smallvec.hpp), so a configuration
  // costs one block, and a shallow scan makes no heap call.
  struct Scan
  {
    struct Level
    {
      Cursor cur;
      index_type index = (index_type)(-1);
      index_type end = 0;

      Level(Cursor const & cur=Cursor()) : cur(cur) {}
    };
    using Levels = SmallVec<Level, 4>;

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
    Levels const & frames() const { return search; }
  private:
    Levels               search;
    SmallVec<size_t, 6>  callstack;
  };
}

#include "cyrt/state/scan.hxx"
