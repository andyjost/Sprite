#pragma once
#include "sprite/fwd.hpp"
#include <iosfwd>
#include <vector>

namespace sprite
{
  struct UnionFind
  {
    struct Item { id_type parent; size_t size=1; };
    mutable std::vector<Item> data;

    id_type root(id_type) const;
    bool find(id_type, id_type) const;
    void unite(id_type, id_type);

    friend std::ostream & operator<<(std::ostream &, UnionFind const &);

  private:

    void increase_capacity(id_type limit) const;
    id_type get(id_type) const;
    id_type set(id_type, id_type) const;
  };
}

#include "sprite/misc/unionfind.hxx"
