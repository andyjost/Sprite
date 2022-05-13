#include "cyrt/cyrt.hpp"

using namespace cyrt;

extern "C"
{
  #define SPEC (appendFile, 2)
  #include "cyrt/currylib/defs/not_used.def"

  #define SPEC (bindIO, 2)
  #include "cyrt/currylib/defs/not_used.def"

  #define SPEC (catch, 2)
  #include "cyrt/currylib/defs/not_used.def"

  #define SPEC (getChar, 0)
  #include "cyrt/currylib/defs/not_used.def"

  #define SPEC (ioError, 1)
  #include "cyrt/currylib/defs/not_used.def"

  #define SPEC (putChar, 1)
  #include "cyrt/currylib/defs/not_used.def"

  #define SPEC (readFile, 1)
  #include "cyrt/currylib/defs/not_used.def"

  #define SPEC (readFileContents, 2)
  #include "cyrt/currylib/defs/not_used.def"

  #define SPEC (returnIO, 1)
  #include "cyrt/currylib/defs/not_used.def"

  #define SPEC (seqIO, 2)
  #include "cyrt/currylib/defs/not_used.def"

  #define SPEC (writeFile, 2)
  #include "cyrt/currylib/defs/not_used.def"
}
