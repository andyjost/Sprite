#pragma once
#include <cstdint>
#include "sprite/graph/infotable.hpp"
#include "sprite/types.hpp"
#include <string>

namespace sprite
{
  using unboxed_int_type = int64_t;
  using unboxed_float_type = double;
  using unboxed_char_type = signed char;

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
  };

  struct Expr
  {
    char kind;
    Arg arg;

    Expr(Node * value=nullptr) : kind('p'), arg(value) {}
    Expr(int16_t value)        : kind('i'), arg(value) {}
    Expr(int32_t value)        : kind('i'), arg(value) {}
    Expr(int64_t value)        : kind('i'), arg(value) {}
    Expr(float value)          : kind('f'), arg(value) {}
    Expr(double value)         : kind('f'), arg(value) {}
    Expr(char value)           : kind('c'), arg(value) {}
    Expr(signed char value)    : kind('c'), arg(value) {}
    Expr(unsigned char value)  : kind('c'), arg(value) {}
  };

  static_assert(sizeof(Arg) == sizeof(Node *));
  static bool constexpr PARTIAL = true;

  struct Node
  {
    InfoTable const * info;

    static Node * create(
        InfoTable const *, Arg *, bool partial=false, Node * target=nullptr
      );
    static Node * rewrite(Node *, InfoTable const *, Arg *, bool partial=false);

    Arg * successors();
    Arg & successor(index_type i, char * kind_out=nullptr);

    std::string str(Node *);
    std::string repr(Node *);

    // copy
    Node * copy(Node *);
    Node * deepcopy(Node *);

    // getitem
    Arg getitem(Node *, index_type, char * kind=nullptr);

    // equality/hash
    bool eq(Node *, Node *);
    bool ne(Node *, Node *);
    hash_type hash(Node *);
  };

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

