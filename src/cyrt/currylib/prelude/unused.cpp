
#include "cyrt/cyrt.hpp"

using namespace cyrt;

extern "C"
{
  #define NAME failure
  #include "cyrt/currylib/defs/not_used.def"

  #define NAME ifVar
  #include "cyrt/currylib/defs/not_used.def"

  #define NAME letrec
  #include "cyrt/currylib/defs/not_used.def"

  #define NAME unifEqLinear
  #include "cyrt/currylib/defs/not_used.def"
}
