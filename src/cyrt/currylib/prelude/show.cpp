#include "cyrt/cyrt.hpp"

using namespace cyrt;

extern "C"
{
  #define NAME showCharLiteral
  #include "cyrt/not_used.def"

  #define NAME showFloatLiteral
  #include "cyrt/not_used.def"

  #define NAME showIntLiteral
  #include "cyrt/not_used.def"

  #define NAME showStringLiteral
  #include "cyrt/not_used.def"
}
