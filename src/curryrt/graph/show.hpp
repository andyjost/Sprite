#pragma once
#include "curryrt/fwd.hpp"
#include "curryrt/graph/cursor.hpp"
#include <iosfwd>
#include <vector>

namespace curryrt
{
  struct ShowMonitor
  {
    virtual void enter(std::ostream & os, Walk2 const *, char context) = 0;
    virtual void exit(std::ostream & os, Walk2 const *, char context) = 0;
  };

  void show(std::ostream &, Cursor, ShowStyle, ShowMonitor * = nullptr);
  void show(std::ostream &, RealPath const &);
  void show(std::ostream &, GuardList const &);
}
