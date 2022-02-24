#include "sprite/builtins.hpp"
#include "sprite/compiler.hpp"

namespace sprite
{
  InfoTable const * create_info(
      ModuleHandle const & owner
    , char const *         name
    , index_type           arity
    , tag_type             tag
    , flag_type            flags
    )
  {
    return &Unit_Info;
  }
}
