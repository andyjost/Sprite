#include "cyrt/cyrt.hpp"

using namespace cyrt;

extern "C"
{
  #define NAME showCharLiteral
  #include "cyrt/currylib/defs/not_used.def"

  #define NAME showFloatLiteral
  #include "cyrt/currylib/defs/not_used.def"

  #define NAME showIntLiteral
  #include "cyrt/currylib/defs/not_used.def"

  #define NAME showStringLiteral
  #include "cyrt/currylib/defs/not_used.def"
}
