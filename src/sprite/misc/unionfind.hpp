#pragma once
#include "sprite/fwd.hpp"
#include <iosfwd>
#include <vector>

namespace sprite
{
  struct UnionFind
  {
    struct Item { cid_type parent; size_t size=1; };
    mutable std::vector<Item> data;

    cid_type root(cid_type) const;
    bool find(cid_type, cid_type) const;
    void unite(cid_type, cid_type);

    friend std::ostream & operator<<(std::ostream &, UnionFind const &);

  private:

    void increase_capacity(cid_type limit) const;
    cid_type get(cid_type) const;
    cid_type set(cid_type, cid_type) const;
  };
}

#include "sprite/misc/unionfind.hxx"
