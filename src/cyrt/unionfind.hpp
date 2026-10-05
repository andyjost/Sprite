#pragma once
#include "cyrt/fwd.hpp"
#include <iosfwd>
#include <vector>

namespace cyrt
{
  struct UnionFind
  {
    struct Item { xid_type parent; size_t size=1; };
    mutable std::vector<Item> data;
    // The ids passed to unite, in order and with repetitions: every id in a
    // group of two or more is among them.  The collector reads them to keep
    // the free variables of the groups (see gc/wdgc.cpp).
    std::vector<xid_type> united;

    xid_type root(xid_type) const;
    bool find(xid_type, xid_type) const;
    void unite(xid_type, xid_type);

    friend std::ostream & operator<<(std::ostream &, UnionFind const &);

  private:

    void increase_capacity(xid_type limit) const;
    xid_type get(xid_type) const;
    xid_type set(xid_type, xid_type) const;
  };
}

#include "cyrt/unionfind.hxx"
