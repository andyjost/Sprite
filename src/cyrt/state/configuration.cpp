#include <algorithm>
#include <iostream>
#include "cyrt/builtins.hpp"
#include "cyrt/state/configuration.hpp"
#include "cyrt/graph/show.hpp"
#include <sstream>

namespace cyrt
{
  std::ostream & operator<<(std::ostream & os, BindingMap const & bnd)
  {
    std::vector<xid_type> keys;
    keys.reserve(bnd.size());
    for(auto && pair: bnd)
      keys.push_back(pair.first);
    std::sort(keys.begin(), keys.end());
    os << '{';
    for(auto && key: keys)
    {
      os << key << ':';
      bnd.at(key)->str(os);
    }
    os << '}';
    return os;
  }

  std::string Configuration::str() const
  {
    std::stringstream ss;
    this->str(ss);
    return ss.str();
  }

  void Configuration::str(std::ostream & os) const
  {
    os << "{{"
       << "root=@" << this->root.arg
       << ", fp="  << this->fingerprint
       << ", cst=" << *this->strict_constraints
       << ", bnd=" << *this->bindings
       << "}}";
  }
}
