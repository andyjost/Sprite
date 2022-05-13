#include "cyrt/cyrt.hpp"
#include <cassert>

using namespace cyrt;

namespace cyrt { inline namespace
{
  static tag_type bindIO_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = _0[0];
    auto tag = rts->hnf(C, &_1);
    if(tag < T_CTOR) return tag;
    assert(_1.target->info == &IO_Info);
    Variable _2 = _1[0];
    Node * replacement = Node::create(&apply_Info, _0[1], _2);
    _0->forward_to(replacement);
    return T_FWD;
  }

  static tag_type returnIO_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    _0.arg->node->info = &IO_Info;
    assert(IO_Info.tag == T_CTOR);
    return T_CTOR;
  }

  static tag_type seqIO_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = _0[0];
    auto tag = rts->hnf(C, &_1);
    if(tag < T_CTOR) return tag;
    _0->forward_to(_0->successor(1));
    return T_FWD;
  }
}}

extern "C"
{
  #define SPEC (appendFile, 2)
  #include "cyrt/currylib/defs/not_used.def"

  InfoTable const bindIO_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "bindIO"
    , /*format*/     "pp"
    , /*step*/       bindIO_step
    , /*type*/       nullptr
    };

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

  InfoTable const seqIO_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "seqIO"
    , /*format*/     "pp"
    , /*step*/       seqIO_step
    , /*type*/       nullptr
    };

  #define SPEC (writeFile, 2)
  #include "cyrt/currylib/defs/not_used.def"
}
