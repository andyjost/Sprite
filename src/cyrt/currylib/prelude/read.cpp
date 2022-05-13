#include "cyrt/cyrt.hpp"

using namespace cyrt;

extern "C"
{
  #define SPEC (readCharLiteral, 1)
  #include "cyrt/currylib/defs/not_used.def"

  #define SPEC (readFloatLiteral, 1)
  #include "cyrt/currylib/defs/not_used.def"

  #define SPEC (readNatLiteral, 1)
  #include "cyrt/currylib/defs/not_used.def"

  #define SPEC (readStringLiteral, 1)
  #include "cyrt/currylib/defs/not_used.def"
}
