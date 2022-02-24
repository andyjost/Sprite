#pragma once
#include "sprite/fwd.hpp"

namespace sprite
{
  struct ModuleHandle {};

  InfoTable const * create_info(
      ModuleHandle const & owner
    , char const *         name
    , index_type           arity
    , tag_type             tag
    , flag_type            flags
    );
}
