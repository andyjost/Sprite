
#include "curryrt/curryrt.hpp"
#include "curryrt/currylib/prelude.hpp"

using namespace curryrt;

extern "C"
{
  #define SPEC (failure, 2)
  #include "curryrt/currylib/defs/not_used.def"

  #define SPEC (ifVar, 2)
  #include "curryrt/currylib/defs/not_used.def"

  #define SPEC (letrec, 2)
  #include "curryrt/currylib/defs/not_used.def"

  #define SPEC (unifEqLinear, 2)
  #include "curryrt/currylib/defs/not_used.def"
}
