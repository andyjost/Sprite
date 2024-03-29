#include <cassert>
#include <cstdio>
#include <cstring>
#include "cyrt/cyrt.hpp"
#include "cyrt/dynload.hpp"
#include <fstream>
#include <sstream>

using namespace cyrt;

namespace cyrt
{
  static char const * _make_io_error_msg(IOErrorKind error_kind, std::string const & filename)
  {
    std::stringstream ss;
    if(error_kind == IO_ERROR && errno)
    {
      ss << std::strerror(errno);
      if(!filename.empty())
        ss << ": ";
    }
    if(!filename.empty())
      ss << filename;
    char const * error_msg = intern_message(ss.str());
    return error_msg;
  }

  static Node * _make_io_error(char const * error_msg, IOErrorKind error_kind=IO_ERROR)
  {
    Node * error_object = Node::create(
        ioerror_info(error_kind), cstring(error_msg)
      );
    return Node::create(&prim_ioError_Info, error_object);
  }

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
    auto ch = std::getchar();
    if(ch == EOF)
    {
      Node * replacement = _make_io_error("EOF");
      std::clearerr(stdin);
      _0->forward_to(replacement);
      return T_FWD;
    }
    else
    {
      assert(_0->info->alloc_size == IO_Info.alloc_size);
      _0->info = &IO_Info;
      ((IONode *) _0.arg->node)->value = char_(ch);
      return T_CTOR;
    }
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
    Node * lhs = Node::create_partial(&prim_error2_Info, _1.target);
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
    auto rv = std::putchar(NodeU{_1.target}.char_->value);
    if(rv == EOF)
    {
      Node * replacement = _make_io_error("EOF");
      std::clearerr(stdout);
      _0->forward_to(replacement);
      return T_FWD;
    }
    else
    {
      assert(_0->info->alloc_size == IO_Info.alloc_size);
      _0->info = &IO_Info;
      ((IONode *) _0.arg->node)->value = unit();
      return T_CTOR;
    }
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

  static tag_type readFile_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable vFilename = _0[0];
    std::string filename = extract_string(vFilename.target);
    Node * head = nil();
    Node ** tail = &head;
    std::ifstream stream(filename);
    if(!stream) goto return_error;
    char ch;
    while(stream.get(ch))
    {
      *tail = cons(char_(ch), nil());
      tail = &NodeU{*tail}.cons->tail;
    }
    _0->forward_to(head);
    return T_FWD;
  return_error:
    char const * error_msg = _make_io_error_msg(IO_ERROR, filename);
    Node * replacement = _make_io_error(error_msg, IO_ERROR);
    _0->forward_to(replacement);
    return T_FWD;
  }


  static tag_type writeFile_step_impl(
      RuntimeState * rts, Configuration * C, std::ios_base::openmode mode
    )
  {
    Cursor _0 = C->cursor();
    Variable vFilename = _0[0];
    Variable vChar;
    std::string filename = extract_string(vFilename.target);
    IOErrorKind error_kind = IO_ERROR;
    std::ofstream stream(filename, mode);
    if(!stream) goto return_error;
    while(true)
    {
      Variable vSpine = _0[1];
      auto tag = rts->hnf(C, &vSpine, &List_Type);
      switch(tag)
      {
        case T_CONS:   vChar = vSpine[0];
                       tag = rts->hnf(C, &vChar);
                       if(tag < T_CTOR) return tag;
                       stream.put(NodeU{vChar.target}.char_->value);
                       if(!stream) goto return_error;
                       *vSpine.target = NodeU{vSpine.target}.cons->tail;
                       break;
        case T_NIL:    _0->forward_to(io(unit()));
                       return T_FWD;
        case T_CHOICE: error_kind = NONDET_ERROR;
                       goto return_error;
        case T_FAIL:   error_kind = FAIL_ERROR;
                       goto return_error;
        default:       return tag;
      }
    }
  return_error:
    char const * error_msg = _make_io_error_msg(error_kind, filename);
    Node * replacement = _make_io_error(error_msg, error_kind);
    _0->forward_to(replacement);
    return T_FWD;
  }

  static tag_type writeFile_step(RuntimeState * rts, Configuration * C)
  {
    return writeFile_step_impl(rts, C, std::ios_base::out);
  }

  static tag_type appendFile_step(RuntimeState * rts, Configuration * C)
  {
    return writeFile_step_impl(rts, C, std::ios_base::app);
  }
}

extern "C"
{
  InfoTable const prim_appendFile_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "appendFile"
    , /*format*/     "pp"
    , /*step*/       appendFile_step
    , /*type*/       nullptr
    };

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

  InfoTable const prim_ioError_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "ioError"
    , /*format*/     "p"
    , /*step*/       ioError_step
    , /*type*/       nullptr
    };

  InfoTable const prim_putChar_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "putChar"
    , /*format*/     "p"
    , /*step*/       putChar_step
    , /*type*/       nullptr
    };

  InfoTable const prim_readFile_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "readFile"
    , /*format*/     "p"
    , /*step*/       readFile_step
    , /*type*/       nullptr
    };

  #define SPEC (prim_readFileContents, 2)
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

  InfoTable const prim_writeFile_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "writeFile"
    , /*format*/     "pp"
    , /*step*/       writeFile_step
    , /*type*/       nullptr
    };
}
