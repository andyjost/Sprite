#pragma once
#include <cassert>
#include <cstdint>
#include "sprite/graph/infotable.hpp"
#include "sprite/types.hpp"
#include <string>

namespace sprite
{
  using unboxed_int_type = int64_t;
  using unboxed_float_type = double;
  using unboxed_char_type = signed char;

  // Defines the fundamental data that may appear in a node.
  union Arg
  {
    Node *             node;
    unboxed_int_type   ub_int;
    unboxed_float_type ub_float;
    unboxed_char_type  ub_char;

    Arg(Node * value=nullptr) : node(value) {}
    Arg(int16_t value)        : ub_int(value) {}
    Arg(int32_t value)        : ub_int(value) {}
    Arg(int64_t value)        : ub_int(value) {}
    Arg(float value)          : ub_float(value) {}
    Arg(double value)         : ub_float(value) {}
    Arg(char value)           : ub_char(value) {}
    Arg(signed char value)    : ub_char(value) {}
    Arg(unsigned char value)  : ub_char(value) {}

    template<typename T>
    Arg & operator=(T const & value)
    {
      Arg tmp{value};
      this->node = tmp.node;
      return *this;
    }
  };
  static_assert(sizeof(Arg) == sizeof(Node *));

  // // A Curry expression, including its C type (not the type in Curry).
  // struct Expr
  // {
  //   Arg & arg;
  //   char kind;

  //   Expr(Arg & arg, char kind) : arg(arg), kind(kind) {}
  //   Expr(Node *& value)        : 

  //   Expr & operator=(Node * v)        { assert(kind=='p'); arg.node=v; return *this; }
  //   Expr & operator=(int16_t v)       { assert(kind=='i'); arg.ub_int=v; return *this; }
  //   Expr & operator=(int32_t v)       { assert(kind=='i'); arg.ub_int=v; return *this; }
  //   Expr & operator=(int64_t v)       { assert(kind=='i'); arg.ub_int=v; return *this; }
  //   Expr & operator=(float v)         { assert(kind=='f'); arg.ub_float=v; return *this; }
  //   Expr & operator=(double v)        { assert(kind=='f'); arg.ub_float=v; return *this; }
  //   Expr & operator=(char v)          { assert(kind=='c'); arg.ub_char=v; return *this; }
  //   Expr & operator=(signed char v)   { assert(kind=='c'); arg.ub_char=v; return *this; }
  //   Expr & operator=(unsigned char v) { assert(kind=='c'); arg.ub_char=v; return *this; }

  //   void * id() const { return &this->arg; }
  //   Node *& operator->() const { return arg.node; }
  // };

  // A position in a Curry expression.
  struct Cursor
  {
    Arg * arg;
    char  kind;

    Cursor() : arg(nullptr), kind('u') {}
    Cursor(Arg & value, char kind)     : arg(&value)        , kind(kind) {}
    Cursor(Node *& value)              : arg((Arg *) &value), kind('p')  {}
    Cursor(unboxed_int_type   & value) : arg((Arg *) &value), kind('i')  {}
    Cursor(unboxed_float_type & value) : arg((Arg *) &value), kind('f')  {}
    Cursor(unboxed_char_type  & value) : arg((Arg *) &value), kind('c')  {}

    friend bool operator==(Cursor lhs, Cursor rhs) { return lhs.arg == rhs.arg; }
    friend bool operator!=(Cursor lhs, Cursor rhs) { return !(lhs==rhs); }
    explicit operator bool() const { return arg; }
    Arg * operator->() const { return this->arg; }
    // Expr operator*() const { assert(this->arg); return Expr(*arg, kind); }
    operator Node *&() const { assert(arg && kind=='p'); return this->arg->node; }
    void * id() const { return arg; }
    InfoTable const * info() const;
  };

  static bool constexpr PARTIAL = true;

  struct Node
  {
    InfoTable const * info;

    static Node * create(
        InfoTable const *, Arg *, bool partial=false, Node * target=nullptr
      );
    static Node * rewrite(Node *, InfoTable const *, Arg *, bool partial=false);

    Arg * successors();
    Cursor successor(index_type i);

    std::string str(Node *);
    std::string repr(Node *);

    // copy
    Node * copy(Node *);
    Node * deepcopy(Node *);

    // getitem
    Cursor getitem(Node *, index_type);

    // equality/hash
    // static bool eq(Node *, Node *);
    // static bool ne(Node *, Node *);
    // hash_type hash(Node *);
  };

  inline InfoTable const * Cursor::info() const
    { return arg && arg->node ? arg->node->info : nullptr; }

  struct Node1 : Node
  {
    Arg arg;
  };

  struct SetGrdNode : Node
  {
    sid_type sid;
    Node *   value;
  };

  using FailNode = Node;

  struct ConstrNode : Node
  {
    Node * value;
    Node * pair;
  };

  struct FreeNode : Node
  {
    cid_type cid;
    Node *   genexpr;
  };

  struct FwdNode : Node
  {
    Node * target;
  };

  struct ChoiceNode : Node
  {
    unboxed_int_type id;
    Node * lhs;
    Node * rhs;
  };

  struct IntNode : Node
  {
    unboxed_int_type value;
  };

  struct FloatNode : Node
  {
    unboxed_float_type value;
  };

  struct CharNode : Node
  {
    unboxed_char_type value;
  };

  struct ConsNode : Node
  {
    Node * head;
    Node * tail;
  };

  struct NilNode : Node {};

  union NodeU
  {
    Node       * head;
    Node1      * node1;
    SetGrdNode * setgrd;
    FailNode   * fail;
    ConstrNode * constr;
    FreeNode   * free;
    FwdNode    * fwd;
    ChoiceNode * choice;
    IntNode    * int_;
    FloatNode  * float_;
    CharNode   * char_;
    ConsNode   * cons;
    NilNode    * nil;
  };
}

