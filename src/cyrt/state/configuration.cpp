#include <algorithm>
#include <cstdlib>
#include <new>
#include "cyrt/builtins.hpp"
#include "cyrt/exceptions.hpp"
#include "cyrt/graph/show.hpp"
#include "cyrt/state/configuration.hpp"
#include <iostream>
#include <sstream>
#include <utility>

namespace cyrt
{
  // The free list of configuration blocks.  A block holds the link to the
  // next free block.  The memory is not returned to the system.
  static void * g_free_configurations = nullptr;

  void * Configuration::operator new(size_t bytes)
  {
    assert(bytes == sizeof(Configuration));
    if(void * block = g_free_configurations)
    {
      g_free_configurations = *(void **) block;
      return block;
    }
    void * block = std::malloc(bytes);
    if(!block)
      throw std::bad_alloc();
    return block;
  }

  void Configuration::operator delete(void * block, size_t)
  {
    *(void **) block = g_free_configurations;
    g_free_configurations = block;
  }

  #ifdef SPRITE_SCHEDULER_COUNTERS
  size_t Configuration::next_configuration_serial()
  {
    static size_t serial = 0;
    return ++serial;
  }
  #endif

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

  void Configuration::add_residual(xid_type vid)
  {
    this->residuals.insert(vid);
    this->residuals.insert(this->grp_id(vid));
  }

  void Configuration::remove_residual(xid_type vid)
  {
    this->residuals.erase(vid);
    this->residuals.erase(this->grp_id(vid));
  }
}
