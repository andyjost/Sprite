#include "cyrt/cyrt.hpp"

using namespace cyrt;

static tag_type _cString_step(RuntimeState * rts, Configuration * C)
{
  Cursor _0 = C->cursor();
  Node * head = nil();
  Node ** tail = &head;
  for(char const * ch = NodeU{_0}.c_str->data; *ch; ++ch)
  {
    *tail = cons(char_(*ch), nil());
    tail = &NodeU{*tail}.cons->tail;
  }
  _0->forward_to(head);
  return T_FWD;
}

InfoTable const _cString_Info{
    /*tag*/        T_FUNC
  , /*arity*/      1
  , /*alloc_size*/ sizeof(cStringNode)
  , /*flags*/      F_CSTRING_TYPE | F_STATIC_OBJECT
  , /*name*/       "_cString"
  , /*format*/     "x"
  , /*step*/       _cString_step
  , /*type*/       nullptr
  };

extern "C"
{
  #define SPEC (_cGenerator, 1)
  #include "cyrt/currylib/defs/not_used.def"

  #define UBSPEC (chr, unboxed_char_type, 1, int_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (ord, unboxed_int_type, 1, char_)
  #include "cyrt/currylib/defs/unboxed.def"
}
