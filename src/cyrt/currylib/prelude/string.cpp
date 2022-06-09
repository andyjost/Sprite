#include <cassert>
#include "cyrt/cyrt.hpp"

using namespace cyrt;

static generator_next_type g_generator_next = nullptr;

namespace cyrt
{
  // The _cyrtbindings module in Python will call this.
  void register_generator_funcs(generator_next_type generator_next)
  {
    assert(generator_next);
    g_generator_next = generator_next;
  }
}

static tag_type _biString_step(RuntimeState * rts, Configuration * C)
{
  Cursor _0 = C->cursor();
  biStringNode * str = NodeU{_0}.c_str;
  Node * replacement = build_curry_string(str->data);
  _0->forward_to(replacement);
  return T_FWD;
}

extern "C" InfoTable const _biString_Info{
    /*tag*/        T_FUNC
  , /*arity*/      1
  , /*alloc_size*/ sizeof(biStringNode)
  , /*flags*/      F_CSTRING_TYPE | F_STATIC_OBJECT
  , /*name*/       "_biString"
  , /*format*/     "x"
  , /*step*/       _biString_step
  , /*type*/       nullptr
  };

static tag_type _biGenerator_step(RuntimeState * rts, Configuration * C)
{
  Cursor _0 = C->cursor();
  biGeneratorNode * gen = NodeU{_0}.generator;
  Node * next_item = g_generator_next(gen->data);
  _0->forward_to(next_item ? cons(next_item, generator(gen->data)) : nil());
  return T_FWD;
}

extern "C" InfoTable const _biGenerator_Info{
    /*tag*/        T_FUNC
  , /*arity*/      1
  , /*alloc_size*/ sizeof(biGeneratorNode)
  , /*flags*/      F_STATIC_OBJECT
  , /*name*/       "_biGenerator"
  , /*format*/     "x" // PyObject *
  , /*step*/       _biGenerator_step
  , /*type*/       nullptr
  };

extern "C"
{
  #define UBSPEC (prim_chr, unboxed_char_type, 1, int_)
  #include "cyrt/currylib/defs/unboxed.def"

  #define UBSPEC (prim_ord, unboxed_int_type, 1, char_)
  #include "cyrt/currylib/defs/unboxed.def"
}
