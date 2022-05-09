#include "cyrt/cyrt.hpp"

using namespace cyrt;

extern "C"
{
  #define NAME appendFile
  #include "cyrt/currylib/defs/not_used.def"

  #define NAME bindIO
  #include "cyrt/currylib/defs/not_used.def"

  #define NAME catch
  #include "cyrt/currylib/defs/not_used.def"

  #define NAME getChar
  #include "cyrt/currylib/defs/not_used.def"

  #define NAME ioError
  #include "cyrt/currylib/defs/not_used.def"

  #define NAME putChar
  #include "cyrt/currylib/defs/not_used.def"

  #define NAME readFile
  #include "cyrt/currylib/defs/not_used.def"

  #define NAME readFileContents
  #include "cyrt/currylib/defs/not_used.def"

  #define NAME returnIO
  #include "cyrt/currylib/defs/not_used.def"

  #define NAME seqIO
  #include "cyrt/currylib/defs/not_used.def"

  #define NAME writeFile
  #include "cyrt/currylib/defs/not_used.def"
}
