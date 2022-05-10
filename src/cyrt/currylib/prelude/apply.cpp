#include "cyrt/cyrt.hpp"
#include "cyrt/graph/walk.hpp"

using namespace cyrt;

namespace cyrt { inline namespace
{
  static tag_type cond_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = _0[0];
    auto tag = rts->hnf(C, &_1, &Bool_Type);
    switch(tag)
    {
      case T_FALSE: _0->forward_to(Fail);
                    return T_FWD;
      case T_TRUE : _0->forward_to(_0->successor(1));
                    return T_FWD;
      default: return tag;
    }
  }

  static tag_type apply_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = _0[0];
    auto tag = rts->hnf(C, &_1);
    if(tag != T_CTOR)
      return tag;
    PartApplicNode * partial = NodeU{_1.target}.partapplic;
    Node * arg = _0->successor(1);
    Node * replacement = partial->complete(arg)
        ? Node::from_partial(partial, arg)
        : Node::create(
              &PartApplic_Info
            , partial->missing - 1
            , partial->head_info
            , cons(arg, partial->terms)
            );
    _0->forward_to(replacement);
    return T_FWD;
  }

  template<typename Action>
  static tag_type _applyspecial(
      RuntimeState * rts, Configuration * C, Action const & action
    )
  {
    Cursor _0 = C->cursor();
    Variable _1 = _0[0];
    auto tag = rts->hnf(C, &_1);
    if(tag != T_CTOR)
      return tag;
    // TODO: catch nondeterminism in IO
    Variable _2 = _0[1];
    tag = action(rts, C, &_2);
    if(_2.target->info->tag < T_CTOR)
      return tag;
    Node * replacement = Node::create(
        &apply_Info, _1.target, _2.target
      );
    _0->forward_to(replacement);
    return T_FWD;
  }

  static tag_type applynf_step(RuntimeState * rts, Configuration * C)
  {
    auto && normalize = [](RuntimeState * rts, Configuration * C, Variable * var)
    {
      Cursor root = C->cursor();
      C->scan.push(var);
    redo:
      tag_type tag = rts->procN(C, root);
      if(tag == E_RESTART)
        goto redo;
      C->scan.pop();
      return tag;
    };
    return _applyspecial(rts, C, normalize);
  }

  static tag_type applygnf_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    auto rv = applynf_step(rts, C);
    std::unordered_set<xid_type> unbound;
    auto node_visitor = visit_unique(_0);
    while(Node * node = node_visitor.next())
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

  static tag_type applyhnf_step(RuntimeState * rts, Configuration * C)
  {
    auto && headnormalize = [](RuntimeState * rts, Configuration * C, Variable * var)
      { return rts->hnf(C, var); };
    return _applyspecial(rts, C, headnormalize);
  }

  static tag_type ensureNotFree_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = _0[0];
    auto tag = rts->hnf_or_free(C, &_1);
    if(tag < T_CTOR)
    {
      if(tag == T_FREE)
      {
        if(!has_generator(_1))
        {
          xid_type gid = C->grp_id(obj_id(_1));
          if(!C->has_binding(gid) && !rts->is_narrowed(C, gid))
            return E_RESIDUAL; // TODO verify this
        }
      }
      return tag;
    }
    else
    {
      _0->forward_to(_1);
      return T_FWD;
    }
  }
}}

extern "C"
{
  InfoTable const apply_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "apply"
    , /*format*/     "pp"
    , /*step*/       apply_step
    , /*type*/       nullptr
    };

  InfoTable const applygnf_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_OPERATOR | F_STATIC_OBJECT
    , /*name*/       "$##"
    , /*format*/     "pp"
    , /*step*/       applygnf_step
    , /*type*/       nullptr
    };

  InfoTable const applyhnf_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_OPERATOR | F_STATIC_OBJECT
    , /*name*/       "$!"
    , /*format*/     "pp"
    , /*step*/       applyhnf_step
    , /*type*/       nullptr
    };

  InfoTable const applynf_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_OPERATOR | F_STATIC_OBJECT
    , /*name*/       "$!!"
    , /*format*/     "pp"
    , /*step*/       applynf_step
    , /*type*/       nullptr
    };

  InfoTable const cond_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "cond"
    , /*format*/     "pp"
    , /*step*/       cond_step
    , /*type*/       nullptr
    };

  InfoTable const ensureNotFree_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "ensureNotFree"
    , /*format*/     "p"
    , /*step*/       ensureNotFree_step
    , /*type*/       nullptr
    };
}
