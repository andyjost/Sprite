#pragma once
#include "boost/utility.hpp"
#include <memory>
#include "sprite/builtins.hpp"
#include "sprite/fingerprint.hpp"
#include "sprite/fingerprint.hpp"
#include "sprite/graph/cursor.hpp"
#include "sprite/misc/unionfind.hpp"
#include "sprite/state/callstack.hpp"
#include "sprite/state/callstack.hpp"
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
    Configuration(Cursor root=Cursor())
      : callstack(root)
      , root(root)
      , strict_constraints(new UnionFind())
      , bindings(new BindingMap())
    {}

    Configuration(Cursor root, Configuration const & obj)
      : callstack(root)
      , root(root)
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

    std::unique_ptr<Configuration> clone(Cursor root)
      { return Configuration::create(root, *this); }

    CallStack         callstack;
    Cursor            root;
    Fingerprint       fingerprint;
    StrictConstraints strict_constraints;
    Bindings          bindings;
    Residuals         residuals;
    bool              escape_all = false;

    void reset(Cursor root = Cursor());
    id_type grp_id(id_type id) { return this->strict_constraints->root(id); }
  };

  inline id_type obj_id(Node * node) { return NodeU{node}.choice->cid; }
}

