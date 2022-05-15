#include <algorithm>
#include "cyrt/builtins.hpp"
#include "cyrt/exceptions.hpp"
#include "cyrt/graph/show.hpp"
#include "cyrt/state/configuration.hpp"
#include <iostream>
#include <sstream>
#include <utility>

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

  void Configuration::clear_error()
  {
    this->error = std::make_pair(nullptr, std::string());
  }

  std::pair<Node *, std::string> Configuration::pop_error()
  {
    std::pair<Node *, std::string> error;
    std::swap(error, this->error);
    return error;
  }

  void Configuration::set_error(std::string const & msg)
  {
    assert(!this->error.first && this->error.second.empty());
    this->error = std::make_pair(nullptr, msg);
  }

  void Configuration::set_error(Node * error_object, std::string const & msg)
  {
    assert(!this->error.first && this->error.second.empty());
    this->error = std::make_pair(error_object, msg);
  }


  void Configuration::raise_error()
  {
    auto & [error_obj, msg] = this->error;
    if(msg.empty())
      throw std::runtime_error("raise_error() called with no error set");
    else
      throw EvaluationError(msg);
  }
}
