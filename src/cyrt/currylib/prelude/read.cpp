#include "cyrt/cyrt.hpp"

using namespace cyrt;

extern "C"
{
  #define NAME readCharLiteral
  #include "cyrt/currylib/defs/not_used.def"

  #define NAME readFloatLiteral
  #include "cyrt/currylib/defs/not_used.def"

  #define NAME readNatLiteral
  #include "cyrt/currylib/defs/not_used.def"

  #define NAME readStringLiteral
  #include "cyrt/currylib/defs/not_used.def"
}
