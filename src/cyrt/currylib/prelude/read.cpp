#include "cyrt/cyrt.hpp"

using namespace cyrt;

extern "C"
{
  #define NAME readCharLiteral
  #include "cyrt/not_used.def"

  #define NAME readFloatLiteral
  #include "cyrt/not_used.def"

  #define NAME readNatLiteral
  #include "cyrt/not_used.def"

  #define NAME readStringLiteral
  #include "cyrt/not_used.def"
}
