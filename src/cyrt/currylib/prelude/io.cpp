#include "cyrt/cyrt.hpp"

using namespace cyrt;

extern "C"
{
  #define NAME appendFile
  #include "cyrt/not_used.def"

  #define NAME bindIO
  #include "cyrt/not_used.def"

  #define NAME catch
  #include "cyrt/not_used.def"

  #define NAME getChar
  #include "cyrt/not_used.def"

  #define NAME ioError
  #include "cyrt/not_used.def"

  #define NAME putChar
  #include "cyrt/not_used.def"

  #define NAME readFile
  #include "cyrt/not_used.def"

  #define NAME readFileContents
  #include "cyrt/not_used.def"

  #define NAME returnIO
  #include "cyrt/not_used.def"

  #define NAME seqIO
  #include "cyrt/not_used.def"

  #define NAME writeFile
  #include "cyrt/not_used.def"
}
