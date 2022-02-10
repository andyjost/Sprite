#pragma once
#include "sprite/fwd.hpp"
#include <iosfwd>
#include <vector>

namespace sprite
{
  struct UnionFind
  {
    struct Item { xid_type parent; size_t size=1; };
    mutable std::vector<Item> data;

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

#include "sprite/misc/unionfind.hxx"
