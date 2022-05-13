#include "cyrt/cyrt.hpp"
#include <sstream>

using namespace cyrt;

static tag_type choice_step(RuntimeState * rts, Configuration * C)
{
  Cursor _0 = C->cursor();
  Node * replacement = choice(rts->istate.xidfactory++, _0->successor(0), _0->successor(1));
  _0->forward_to(replacement);
  return T_FWD;
}

static tag_type failed_step(RuntimeState * rts, Configuration * C)
{
  Cursor _0 = C->cursor();
  return _0->make_failure();
}

static tag_type error_step(RuntimeState * rts, Configuration * C)
{
  Cursor _0 = C->cursor();
  Variable _1 = _0[0];
  auto tag = rts->hnf(C, &_1);
  if(tag < T_CTOR) return tag;
  std::string msg = _1.target->str();
  rts->set_error_msg(msg);
  return E_ERROR;
}

namespace cyrt
{
  tag_type not_used(RuntimeState * rts, Configuration * C)
  {
    std::stringstream ss;
    ss << "function 'Prelude." << C->cursor()->info->name << "' is not used by Sprite";
    rts->set_error_msg(ss.str());
    return E_ERROR;
  }
}

extern "C"
{
  InfoTable const choice_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_OPERATOR | F_STATIC_OBJECT
    , /*name*/       "?"
    , /*format*/     "pp"
    , /*step*/       choice_step
    , /*type*/       nullptr
    };

  InfoTable const failed_Info {
      /*tag*/        T_FUNC
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node0)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "failed"
    , /*format*/     ""
    , /*step*/       failed_step
    , /*type*/       nullptr
    };

  InfoTable const error_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "error"
    , /*format*/     "p"
    , /*step*/       error_step
    , /*type*/       nullptr
    };
}
