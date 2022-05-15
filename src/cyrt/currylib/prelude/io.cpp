#include <cassert>
#include <cstdio>
#include <cstring>
#include "cyrt/cyrt.hpp"
#include "cyrt/dynload.hpp"

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

  static tag_type catch_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = _0[0];
    auto tag = rts->hnf(C, &_1);
    if(tag < T_CTOR)
    {
      if(tag != E_ERROR)
        return tag;
      Variable _2 = _0[1];
      Node * replacement = Node::create(&apply_Info, _2, _1);
      _0->forward_to(replacement);
    }
    else
      _0->forward_to(_1);
    return T_FWD;
  }

  static tag_type getChar_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    assert(_0->info->alloc_size >= IO_Info.alloc_size);
    char ch = (char) std::getchar();
    _0->info = &IO_Info;
    ((IONode *) _0.arg->node)->value = char_(ch);
    return T_CTOR;
  }

  // prim_ioError :: IOError -> IO _
  static tag_type ioError_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = _0[0];
    InfoTable const * show_Info = SharedCurryModule::symbol(
        "Prelude", "CyI7Prelude45__impl_hshow_hPrelude_dShow_hPrelude_dIOError"
      );
    assert(show_Info);
    // (error2 err) $## (show err)
    Node * error_msg = Node::create(show_Info, _1);
    Node * lhs = Node::create_partial(&error2_Info, _1.target);
    Node * replacement = Node::create(&applynf_Info, lhs, error_msg);
    _0->forward_to(replacement);
    return T_FWD;
  }

  static tag_type putChar_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = _0[0];
    auto tag = rts->hnf(C, &_1);
    if(tag < T_CTOR) return tag;
    auto rv = std::putchar(NodeU{_1}.char_->value);
    Node * replacement = (rv == EOF)
        ? Node::create(&error_Info, cstring(std::strerror(errno)))
        : io(unit());
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

  InfoTable const catch_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "catch"
    , /*format*/     "pp"
    , /*step*/       catch_step
    , /*type*/       nullptr
    };

  InfoTable const getChar_Info {
      /*tag*/        T_FUNC
    , /*arity*/      0
    , /*alloc_size*/ sizeof(FwdNode)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "getChar"
    , /*format*/     ""
    , /*step*/       getChar_step
    , /*type*/       nullptr
    };

  InfoTable const ioError_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "ioError"
    , /*format*/     "p"
    , /*step*/       ioError_step
    , /*type*/       nullptr
    };

  InfoTable const putChar_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "putChar"
    , /*format*/     "p"
    , /*step*/       putChar_step
    , /*type*/       nullptr
    };

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
