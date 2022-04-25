#include "cyrt/cyrt.hpp"

using namespace cyrt;

extern "C"
{
  #define NAME choice
  #include "cyrt/not_used.def"

  #define NAME error
  #include "cyrt/not_used.def"

  #define NAME failed
  #include "cyrt/not_used.def"

  #define NAME notused
  #include "cyrt/not_used.def"
}
