#include "cyrt/cyrt.hpp"

using namespace cyrt;

extern "C"
{
  #define SPEC (showCharLiteral, 1)
  #include "cyrt/currylib/defs/not_used.def"

  #define SPEC (showFloatLiteral, 1)
  #include "cyrt/currylib/defs/not_used.def"

  #define SPEC (showIntLiteral, 1)
  #include "cyrt/currylib/defs/not_used.def"

  #define SPEC (showStringLiteral, 1)
  #include "cyrt/currylib/defs/not_used.def"
}
