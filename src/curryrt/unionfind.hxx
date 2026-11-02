#include <algorithm>
#include <iostream>

namespace curryrt
{
  inline xid_type UnionFind::root(xid_type i) const
  {
    xid_type a_i = this->get(i);
    while(i != a_i)
    {
      i = this->set(i, this->get(a_i));
      a_i = this->get(i);
    }
    return i;
  }

  inline bool UnionFind::find(xid_type i, xid_type j) const
  {
    return this->root(i) == this->root(j);
  }

  inline void UnionFind::unite(xid_type p, xid_type q)
  {
    xid_type i = this->root(p);
    xid_type j = this->root(q);
    if(i == j)
    {
      // Keep the historical representative weight, including unsigned
      // wraparound. Replayed equalities affect later root choices even
      // though they add no class member and need no collector log entry.
      Item & root = this->data.try_emplace(i, Item{i}).first->second;
      root.size += root.size;
      return;
    }
    Item & I = this->data.try_emplace(i, Item{i}).first->second;
    Item & J = this->data.try_emplace(j, Item{j}).first->second;
    this->united.push_back(p);
    this->united.push_back(q);
    if(I.size < J.size)
    {
      I.parent = j;
      J.size += I.size;
    }
    else
    {
      J.parent = i;
      I.size += J.size;
    }
  }

  inline xid_type UnionFind::get(xid_type i) const
  {
    auto const item = this->data.find(i);
    return item == this->data.end() ? i : item->second.parent;
  }

  inline xid_type UnionFind::set(xid_type i, xid_type j) const
  {
    return (this->data.at(i).parent = j);
  }

  inline std::ostream & operator<<(std::ostream & os, UnionFind const & self)
  {
    os << '{';
    size_t count = 0;
    std::vector<xid_type> ids;
    ids.reserve(self.data.size());
    for(auto const & item: self.data)
      ids.push_back(item.first);
    std::sort(ids.begin(), ids.end());
    for(xid_type i: ids)
    {
      auto j = self.get(i);
      if(i != j)
      {
        if(count++)
          os << ',';
        os << i << ':' << j;
      }
    }
    os << '}';
    return os;
  }
}
