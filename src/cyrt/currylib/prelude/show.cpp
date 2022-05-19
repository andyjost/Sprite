#include "cyrt/cyrt.hpp"

using namespace cyrt;

namespace cyrt
{
  static tag_type show_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = _0[0]; // pre-normalized with $## in the Prelude
    std::string str = _1.target->str();
    Node * replacement = build_curry_string(str.c_str());
    _0->forward_to(replacement);
    return T_FWD;
  }
}

extern "C"
{
  InfoTable const prim_showCharLiteral_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "showCharLiteral"
    , /*format*/     "p"
    , /*step*/       show_step
    , /*type*/       nullptr
    };

  InfoTable const prim_showFloatLiteral_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "showFloatLiteral"
    , /*format*/     "p"
    , /*step*/       show_step
    , /*type*/       nullptr
    };

  InfoTable const prim_showIntLiteral_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "showIntLiteral"
    , /*format*/     "p"
    , /*step*/       show_step
    , /*type*/       nullptr
    };

  InfoTable const prim_showStringLiteral_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "showStringLiteral"
    , /*format*/     "p"
    , /*step*/       show_step
    , /*type*/       nullptr
    };
}
