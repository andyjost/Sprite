#pragma once
#include "sprite/fingerprint.hpp"
#include "sprite/fingerprint.hpp"
#include "sprite/graph/cursor.hpp"
#include "sprite/state/callstack.hpp"
#include <memory>

namespace sprite
{
  struct StrictConstraints {};
  struct Bindings {};
  struct Residuals {};

  struct Configuration
  {
    Configuration(
        Cursor root            = Cursor()
      , Fingerprint * fp       = nullptr
      , StrictConstraints * sc = nullptr
      , Bindings * b           = nullptr
      , Residuals * r          = nullptr
      , bool escape_all        = false
      )
      : callstack(root)
      , root(root)
      , fingerprint(fp ? *fp : Fingerprint())
      , strict_constraints(sc ? *sc : StrictConstraints())
      , bindings(b ? *b : Bindings())
      , residuals(r ? *r : Residuals())
      , escape_all(escape_all)
    {}

    template<typename ... Args>
    static Configuration * create(Args && ... args)
      { return new Configuration(std::forward<Args>(args)...); }

    CallStack         callstack;
    Cursor            root;
    Fingerprint       fingerprint;
    StrictConstraints strict_constraints;
    Bindings          bindings;
    Residuals         residuals;
    bool              escape_all;

    std::unique_ptr<Configuration> clone(Cursor root);
    void reset(Cursor root = Cursor());
  };
}
