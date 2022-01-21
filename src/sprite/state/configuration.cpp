#include "sprite/state/configuration.hpp"
#include "sprite/builtins.hpp"

namespace sprite
{
  void Configuration::reset(Cursor root)
  {
    if(root)
      this->root = root;
    this->callstack.reset(this->root);
  }
}
