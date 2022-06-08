#include "cyrt/cyrt.hpp"

using namespace cyrt;

static tag_type _biString_step(RuntimeState * rts, Configuration * C)
{
  Cursor _0 = C->cursor();
  biStringNode * str = NodeU{_0}.c_str;
  Node * replacement = build_curry_string(str->data);
  _0->forward_to(replacement);
  return T_FWD;
}

InfoTable const _biString_Info{
    /*tag*/        T_FUNC
  , /*arity*/      1
  , /*alloc_size*/ sizeof(biStringNode)
  , /*flags*/      F_CSTRING_TYPE | F_STATIC_OBJECT
  , /*name*/       "_biString"
  , /*format*/     "x"
  , /*step*/       _biString_step
  , /*type*/       nullptr
  };

extern "C"
{
  #define SPEC (_biGenerator, 1)
  #include "cyrt/currylib/defs/not_used.def"

  #define UBSPEC (prim_chr, unboxed_char_type, 1, int_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_ord, unboxed_int_type, 1, char_)
  #include "cyrt/currylib/defs/unboxed.def"
}
