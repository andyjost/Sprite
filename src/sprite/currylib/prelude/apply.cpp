#include <cassert>
#include "sprite/builtins.hpp"
#include "sprite/currylib/prelude.hpp"
#include "sprite/exceptions.hpp"
#include "sprite/inspect.hpp"
#include "sprite/state/rts.hpp"

namespace sprite { inline namespace
{
  SStatus cond_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = variable(_0, 0);
    auto tag = rts->hnf(C, &_1, &Bool_Type);
    switch(tag)
    {
      case T_FALSE: _0->node->forward_to(Fail);
                    return T_FWD;
      case T_TRUE : _0->node->forward_to(_0->node->successor(1));
                    return T_FWD;
      default: return tag;
    }
  }

  SStatus apply_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = variable(_0, 0);
    auto tag = rts->hnf(C, &_1);
    if(tag != T_CTOR)
      return tag;
    PartApplicNode * partial = NodeU{_1.target}.partapplic;
    Node * arg = _0->node->successor(1);
    Node * replacement = partial->complete(arg)
        ? Node::from_partial(partial, arg)
        : Node::create(
              &PartApplic_Info
            , partial->missing - 1
            , partial->head_info
            , cons(arg, partial->terms)
            );
    _0->node->forward_to(replacement);
    return T_FWD;
  }

  template<typename Action>
  static SStatus _applyspecial(
      RuntimeState * rts, Configuration * C, Action const & action
    )
  {
    Cursor _0 = C->cursor();
    Variable _1 = variable(_0, 0);
    auto tag = rts->hnf(C, &_1);
    if(tag != T_CTOR)
      return tag;
    // TODO: catch nondeterminism in IO
    Variable _2 = variable(_0, 1);
    tag = action(rts, C, &_2);
    if(_2.target.info()->tag < T_CTOR)
      return tag;
    Node * replacement = Node::create(
        &apply_Info, _1.target->node, _2.target->node
      );
    _0->node->forward_to(replacement);
    return T_FWD;
  }

  SStatus applynf_step(RuntimeState * rts, Configuration * C)
  {
    auto && normalize = [](RuntimeState * rts, Configuration * C, Variable * var)
    {
      C->search.push_barrier();
      size_t ret = C->search.extend(var);
      tag_type tag;
      auto result = rts->procN(C, tag);
      C->search.resize(ret);
      C->search.pop_barrier();
      return result;
    };
    return _applyspecial(rts, C, normalize);
  }

  SStatus applygnf_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    auto rv = applynf_step(rts, C);
    std::unordered_set<xid_type> unbound;
    auto nodes = iternodes(_0->node);
    while(Node * node = nodes.next())
    {
      if(inspect::isa_freevar(node) && !has_generator(node))
        unbound.insert(obj_id(node));
    }
    if(!unbound.empty())
      // FIXME: return unbound set
      return E_RESIDUAL;
    else
      return rv;
  }

  SStatus applyhnf_step(RuntimeState * rts, Configuration * C)
  {
    auto && headnormalize = [](RuntimeState * rts, Configuration * C, Variable * var)
      { return rts->hnf(C, var); };
    return _applyspecial(rts, C, headnormalize);
  }
}}

namespace sprite
{
  InfoTable const apply_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*typetag*/    OPERATOR
    , /*flags*/      NO_FLAGS
    , /*name*/       "$"
    , /*format*/     "pp"
    , /*step*/       apply_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const applygnf_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*typetag*/    OPERATOR
    , /*flags*/      NO_FLAGS
    , /*name*/       "$##"
    , /*format*/     "pp"
    , /*step*/       applygnf_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const applyhnf_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*typetag*/    OPERATOR
    , /*flags*/      NO_FLAGS
    , /*name*/       "$!"
    , /*format*/     "pp"
    , /*step*/       applyhnf_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const applynf_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*typetag*/    OPERATOR
    , /*flags*/      NO_FLAGS
    , /*name*/       "$!!"
    , /*format*/     "pp"
    , /*step*/       applynf_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const cond_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "cond"
    , /*format*/     "pp"
    , /*step*/       cond_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };
}
