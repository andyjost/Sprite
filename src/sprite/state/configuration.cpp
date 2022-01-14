#include "sprite/state/configuration.hpp"

namespace sprite
{
  std::unique_ptr<Configuration> Configuration::clone(Cursor root)
  {
    // TODO
    return std::unique_ptr<Configuration>();
  }

  void Configuration::reset(Cursor root)
  {
    if(root)
      this->root = root;
    this->callstack.reset(this->root);
  }
}
