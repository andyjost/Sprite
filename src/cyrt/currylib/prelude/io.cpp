#include "cyrt/cyrt.hpp"

using namespace cyrt;

namespace cyrt { inline namespace
{
  static tag_type returnIO_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    _0.arg->node->info = &IO_Info;
    assert(IO_Info.tag == T_CTOR);
    return T_CTOR;
  }
}}

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

  InfoTable const returnIO_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "returnIO"
    , /*format*/     "p"
    , /*step*/       returnIO_step
    , /*type*/       nullptr
    };

  #define SPEC (seqIO, 2)
  #include "cyrt/currylib/defs/not_used.def"

  #define SPEC (writeFile, 2)
  #include "cyrt/currylib/defs/not_used.def"
}
