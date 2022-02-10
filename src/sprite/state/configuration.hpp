#pragma once
#include "boost/utility.hpp"
#include <cassert>
#include <iosfwd>
#include <memory>
#include "sprite/builtins.hpp"
#include "sprite/fingerprint.hpp"
#include "sprite/fingerprint.hpp"
#include "sprite/graph/cursor.hpp"
#include "sprite/graph/walk.hpp"
#include "sprite/misc/unionfind.hpp"
#include <string>
#include <unordered_map>
#include <unordered_set>

namespace sprite
{
  using StrictConstraints = std::shared_ptr<UnionFind>;
  using BindingMap = std::unordered_map<id_type, Node *>;
  using Bindings = std::shared_ptr<BindingMap>;
  using Residuals = std::unordered_set<id_type>;

  struct Configuration : boost::noncopyable
  {
    Configuration(Node * root=nullptr)
      : root_storage(root)
      , root(this->root_storage)
      , search(this->root)
      , strict_constraints(new UnionFind())
      , bindings(new BindingMap())
    {}

    Configuration(Node * root, Configuration const & obj)
      : root_storage(root)
      , root(this->root_storage)
      , search(this->root)
      , fingerprint(obj.fingerprint)
      , strict_constraints(obj.strict_constraints)
      , bindings(obj.bindings)
      , residuals()
      , escape_all(obj.escape_all)
    {}

    template<typename ... Args>
    static std::unique_ptr<Configuration> create(Args && ... args)
    {
      return std::unique_ptr<Configuration>(
          new Configuration(std::forward<Args>(args)...)
        );
    }

    std::unique_ptr<Configuration> clone(Node * root)
      { return Configuration::create(root, *this); }

    Node *            root_storage;
    Cursor            root;
    Search            search;
    Fingerprint       fingerprint;
    StrictConstraints strict_constraints;
    Bindings          bindings;
    Residuals         residuals;
    bool              escape_all = false;

    Cursor cursor() const { return this->search.cursor(); }
    id_type grp_id(id_type id) const
      { return this->strict_constraints->root(id); }
    bool has_binding(id_type id) const { return this->bindings->count(id); }
    std::string str() const;
    void str(std::ostream &) const;
  };

  inline id_type obj_id(Node * node) { return NodeU{node}.choice->cid; }

  template<typename T>
  inline T & write(std::shared_ptr<T> & shared)
  {
    if(shared.use_count() != 1)
      shared = std::shared_ptr<T>(new T(*shared));
    assert(shared.use_count() == 1);
    return *shared;
  }

  std::ostream & operator<<(std::ostream &, BindingMap const &);
}

