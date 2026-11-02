#pragma once
#include "curryrt/fwd.hpp"
#include <algorithm>
#include <iosfwd>
#include <unordered_map>
#include <vector>

namespace curryrt
{
  struct UnionFind
  {
    UnionFind() = default;
    UnionFind(UnionFind const & other)
      : data(other.data)
    {
      united.reserve(std::max(other.united.capacity(), other.united.size() + 2));
      united.assign(other.united.begin(), other.united.end());
    }
    struct Item { xid_type parent; size_t size=1; };
    // Absent identifiers are singleton classes. Only identifiers passed to
    // unite need entries, independently of the process-wide counter.
    mutable std::unordered_map<xid_type, Item> data;
    // Endpoints of real unions, in insertion order. Every member of a
    // non-singleton class occurs here, so the collector can keep its free
    // variable alive without scanning the identifier space.
    std::vector<xid_type> united;

    xid_type root(xid_type) const;
    bool find(xid_type, xid_type) const;
    void unite(xid_type, xid_type);

    friend std::ostream & operator<<(std::ostream &, UnionFind const &);

  private:

    xid_type get(xid_type) const;
    xid_type set(xid_type, xid_type) const;
  };
}

#include "curryrt/unionfind.hxx"
