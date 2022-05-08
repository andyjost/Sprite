#pragma once
#include <iosfwd>
#include "cyrt/graph/node.hpp"

namespace cyrt
{
  struct ShowMonitor
  {
    virtual void enter(std::ostream & os, Walk2 const *, char context) = 0;
    virtual void exit(std::ostream & os, Walk2 const *, char context) = 0;
  };

  void show(std::ostream &, Cursor, ShowStyle, ShowMonitor * = nullptr);
  void show(std::ostream &, std::vector<index_type> const &);
  void show(std::ostream &, std::vector<Set *> const &);
}
