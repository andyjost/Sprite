#pragma once
#include "boost/utility.hpp"
#include <cassert>
#include "cyrt/builtins.hpp"
#include "cyrt/fingerprint.hpp"
#include "cyrt/fingerprint.hpp"
#include "cyrt/graph/cursor.hpp"
#include "cyrt/state/scan.hpp"
#include "cyrt/unionfind.hpp"
#include <iosfwd>
#include <memory>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>

namespace cyrt
{
  using StrictConstraints = std::shared_ptr<UnionFind>;
  using BindingMap = std::unordered_map<xid_type, Node *>;
  using Bindings = std::shared_ptr<BindingMap>;
  using Residuals = std::unordered_set<xid_type>;

  struct Configuration : boost::noncopyable
  {
    Configuration(Node * root=nullptr)
      : root_storage(root)
      , root(this->root_storage)
      , scan(this->root)
      , strict_constraints(new UnionFind())
      , bindings(new BindingMap())
    {}

    Configuration(Node * root, Configuration const & obj)
      : root_storage(root)
      , root(this->root_storage)
      , scan(this->root)
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
    Scan              scan;
    Fingerprint       fingerprint;
    StrictConstraints strict_constraints;
    Bindings          bindings;
    Residuals         residuals;
    bool              escape_all = false;
    bool              forced_rotate = false;
    std::pair<Node *, std::string> error; // pair of (error_object, message)

    Cursor cursor() const { return this->scan.cursor(); }
    xid_type grp_id(xid_type id) const
      { return this->strict_constraints->root(id); }
    xid_type grp_id() const;
    bool has_binding(xid_type id) const { return this->bindings->count(id); }
    std::string str() const;
    void str(std::ostream &) const;

    void clear_error();
    std::pair<Node *, std::string> pop_error();
    void set_error(std::string const &);
    void set_error(Node *, std::string const &);
    void raise_error();

    void add_residual(xid_type vid);
  };

  inline xid_type obj_id(Node * node) { return NodeU{node}.choice->cid; }

  template<typename T>
  inline T & write(std::shared_ptr<T> & shared)
  {
    if(shared.use_count() != 1)
      shared = std::shared_ptr<T>(new T(*shared));
    assert(shared.use_count() == 1);
    return *shared;
  }

  std::ostream & operator<<(std::ostream &, BindingMap const &);
  inline xid_type Configuration::grp_id() const { return this->grp_id(obj_id(this->root)); }
}

