#include "cyrt/cyrt.hpp"

using namespace cyrt;

extern "C"
{
  #define NAME _PyGenerator
  #include "cyrt/not_used.def"

  #define NAME _PyString
  #include "cyrt/not_used.def"

  #define NAME chr
  #include "cyrt/not_used.def"

  #define NAME ord
  #include "cyrt/not_used.def"
}
