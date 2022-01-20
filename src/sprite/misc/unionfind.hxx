#include <algorithm>
#include <iostream>

namespace sprite
{
  inline cid_type UnionFind::root(cid_type i) const
  {
    cid_type a_i = this->get(i);
    while(i != a_i)
    {
      i = this->set(i, this->get(a_i));
      a_i = this->get(i);
    }
    return i;
  }

  inline bool UnionFind::find(cid_type i, cid_type j) const
  {
    return this->root(i) == this->root(j);
  }

  inline void UnionFind::unite(cid_type p, cid_type q)
  {
    cid_type i = this->root(p);
    cid_type j = this->root(q);
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

  inline void UnionFind::increase_capacity(cid_type maxindex) const
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

  inline cid_type UnionFind::get(cid_type i) const
  {
    return (i < this->data.size())
        ? this->data[i].parent
        : i;
  }

  inline cid_type UnionFind::set(cid_type i, cid_type j) const
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
