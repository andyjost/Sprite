#pragma once
#include "boost/utility.hpp"
#include <memory>
#include "sprite/fingerprint.hpp"
#include "sprite/fingerprint.hpp"
#include "sprite/graph/cursor.hpp"
#include "sprite/state/callstack.hpp"

namespace sprite
{
  struct StrictConstraints {};
  struct Bindings {};
  struct Residuals {};

  struct Configuration : boost::noncopyable
  {
    Configuration(Cursor root=Cursor()) : callstack(root) , root(root) {}
    Configuration(Cursor root, Configuration const & obj)
      : callstack(root)
      , root(root)
      , fingerprint(obj.fingerprint)
      , strict_constraints(obj.strict_constraints)
      , bindings(obj.bindings)
      , residuals(obj.residuals)
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
  };
}
