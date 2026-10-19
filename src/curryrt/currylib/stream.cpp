#include "curryrt/curryrt.hpp"
#include "curryrt/currylib/prelude.hpp"
#include "curryrt/module.hpp"

using namespace curryrt;

namespace
{
  tag_type emit_step(RuntimeState * rts, Configuration * C)
  {
    Cursor root = C->cursor();
    Node * event = Node::create(&Pair_Info, root[1], root[0]);
    root->forward_to(io(unit()));
    // This completed step exits before the usual safepoint.  The next
    // ordinary step checks the pending collection and rotation requests.
    bool const last = rts->steps_total + 1 >= rts->step_limit;
    rts->count_step();
    if(last)
      return E_TERMINATE;
    rts->stream_event = event;
    return E_YIELD;
  }

  InfoTable const emit_Info {
      T_FUNC, 2, sizeof(Node2), F_MONADIC | F_STATIC_OBJECT
    , "emitYield", "pp", emit_step, nullptr
    };

  tag_type yield_step(RuntimeState * rts, Configuration * C)
  {
    if(rts->in_recursive_call() || gc_eval_depth() > 1)
    {
      C->set_error("yield inside a set function or nested evaluation is not supported");
      return E_ERROR;
    }
    Cursor root = C->cursor();
    // ($!!) normalizes the complete value on behalf of a monadic
    // primitive, so a choice anywhere in it raises the I/O error.
    Node * emit = Node::create_partial(&emit_Info, root[0].target);
    root->forward_to(Node::create(&applynf_Info, emit, root[1]));
    return T_FWD;
  }
}

extern "C"
{
  extern InfoTable const CyI6Sprite6Stream9primYield {
      T_FUNC, 2, sizeof(Node2), F_MONADIC | F_STATIC_OBJECT
    , "primYield", "pp", yield_step, nullptr
    };
}

static int register_stream_builtins()
{
  Module::register_builtin_module(
      "Sprite.Stream", {}, {{"primYield", &CyI6Sprite6Stream9primYield}}
    );
  return 0;
}

static int _ = register_stream_builtins();
