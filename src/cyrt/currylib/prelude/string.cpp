#include <cassert>
#include "cyrt/cyrt.hpp"
#include "cyrt/currylib/prelude.hpp"

using namespace cyrt;

static generator_next_type g_generator_next = nullptr;
static generator_hold_type g_generator_acquire = nullptr;
static generator_hold_type g_generator_release = nullptr;

namespace cyrt
{
  // The _cyrtbindings module in Python will call this.
  void register_generator_funcs(
      generator_next_type generator_next, generator_hold_type acquire
    , generator_hold_type release
    )
  {
    assert(generator_next);
    g_generator_next = generator_next;
    g_generator_acquire = acquire;
    g_generator_release = release;
  }

  void generator_acquire(void * data)
  {
    if(data && g_generator_acquire)
      g_generator_acquire(data);
  }

  void generator_release(void * data)
  {
    if(data && g_generator_release)
      g_generator_release(data);
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
  void * data = gen->data;
  Node * next_item = g_generator_next(data);
  if(next_item)
  {
    // The item is built now, after set_goal walked the goal.  A free variable
    // made outside this evaluation (a curry.free marker used before) is new to
    // the variable table.  See RuntimeState::register_freevars.
    if(rts->istate.external_freevars)
      rts->register_freevars(next_item);
    // The node of the rest of the list takes over the reference.
    _0->forward_to(cons(next_item, generator(data)));
    return T_FWD;
  }
  // The iterator is exhausted.  A forward node owns nothing, so the
  // reference goes now.  The release may run Python code (the finalizer of
  // a generator), so it comes after the rewrite.
  _0->forward_to(nil());
  generator_release(data);
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
