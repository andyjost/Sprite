#include <algorithm>
#include <iostream>

namespace sprite
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
    this->increase_capacity(std::max(i, j));
    Item & I = this->data[i];
    Item & J = this->data[j];
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

  inline void UnionFind::increase_capacity(xid_type maxindex) const
  {
    size_t limit = maxindex + 1;
    size_t n = this->data.size();
    if(n < limit)
    {
      this->data.resize(limit);
      for(; n<limit; ++n)
        this->data[n].parent = n;
    }
  }

  inline xid_type UnionFind::get(xid_type i) const
  {
    return (i < this->data.size())
        ? this->data[i].parent
        : i;
  }

  inline xid_type UnionFind::set(xid_type i, xid_type j) const
  {
    this->increase_capacity(i);
    return (this->data[i].parent = j);
  }

  inline std::ostream & operator<<(std::ostream & os, UnionFind const & self)
  {
    os << '{';
    size_t count = 0;
    for(size_t i=0; i<self.data.size(); ++i)
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
