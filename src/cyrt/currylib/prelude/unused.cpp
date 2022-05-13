
#include "cyrt/cyrt.hpp"

using namespace cyrt;

extern "C"
{
  #define SPEC (failure, 2)
  #include "cyrt/currylib/defs/not_used.def"

  #define SPEC (ifVar, 2)
  #include "cyrt/currylib/defs/not_used.def"

  #define SPEC (letrec, 2)
  #include "cyrt/currylib/defs/not_used.def"

  #define SPEC (unifEqLinear, 2)
  #include "cyrt/currylib/defs/not_used.def"
}
