
#include "curryrt/curryrt.hpp"
#include "curryrt/currylib/prelude.hpp"

using namespace curryrt;

extern "C"
{
  #define SPEC (failure, 2)
  #include "curryrt/currylib/defs/not_used.def"

  InfoTable const ifVar_Info {
      T_FUNC, 3, sizeof(Node3), F_STATIC_OBJECT,
      "ifVar", "ppp", curryrt::not_used, nullptr
    };

  #define SPEC (letrec, 2)
  #include "curryrt/currylib/defs/not_used.def"

  #define SPEC (unifEqLinear, 2)
  #include "curryrt/currylib/defs/not_used.def"
}
