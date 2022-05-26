#pragma once
#include <cassert>
#include "cyrt/fwd.hpp"
#include <string>
#include <vector>

namespace cyrt
{
  union Arg
  {
    Node *             node;
    unboxed_int_type   ub_int;
    unboxed_float_type ub_float;
    unboxed_char_type  ub_char;
    xid_type           cid;
    void const *       blob;
    Head *             head;
    InfoTable const *  xinfo;

    Arg(Node * value=nullptr)    : node(value)     {}
    Arg(int16_t value)           : ub_int(value)   {}
    Arg(int32_t value)           : ub_int(value)   {}
    Arg(int64_t value)           : ub_int(value)   {}
    Arg(xid_type value)          : cid(value)      {}
    Arg(float value)             : ub_float(value) {}
    Arg(double value)            : ub_float(value) {}
    Arg(char value)              : ub_char(value)  {}
    Arg(signed char value)       : ub_char(value)  {}
    Arg(unsigned char value)     : ub_char(value)  {}
    Arg(InfoTable const * value) : xinfo(value)    {}
    template<typename T>
    Arg(T const * value)         : blob(value)     {}
    Arg(std::nullptr_t)          : blob(nullptr)   {}
    Arg(Cursor const &);
    Arg(Variable const &);

    template<typename T> Arg & operator=(T &&);
    std::string repr() const;
  };

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
    Cursor(unboxed_ptr_type   & value) : arg((Arg *) &value), kind('x')  {}

    friend bool operator==(Cursor lhs, Cursor rhs) { return lhs.arg == rhs.arg; }
    friend bool operator!=(Cursor lhs, Cursor rhs) { return !(lhs==rhs); }
    explicit operator bool() const { return arg; }
    Node * operator->() const { return this->arg->node; }
    Node *& operator*() const { return this->arg->node; }
    operator Node *&() const { assert(arg && kind=='p'); return **this; }
    void * id() const
        { return kind=='p' ? (void *) this->arg->node : (void *) this->arg; }
    Cursor & skipfwd(); // inspect.hxx
    Cursor fwd_chain_target() const; // inspect.hxx
    Variable operator[](index_type) const;
    std::string str() const;
    std::string str(SubstFreevars, ShowMonitor * = nullptr) const;
    std::string str(Variable const &) const;
    std::string str(Variable const &, SubstFreevars) const;
    std::string repr() const;
  };

  struct Variable
  {
    mutable Cursor          target;
    std::vector<index_type> realpath;
    std::vector<Set *>      guards;

    Variable() {}
    Variable(Node *, index_type, bool update_fwd_nodes=true); // indexing.cpp
    Variable operator[](index_type) const;
    Node * rvalue() const;

    void update_escape_sets();

    std::string str() const;
    std::string str(SubstFreevars) const;
  };


  struct Expr
  {
    Arg  arg;
    char kind; // 'p': pointer (i.e., Node *)
               // 'i': unboxed integer
               // 'f': unboxed float
               // 'c': unboxed char
               // 'x': unboxed pointer
               // 'u': undefined

    Expr()                         : arg((Node *) nullptr), kind('u') {}
    Expr(Cursor cur)               : arg(*cur.arg), kind(cur.kind) {}
    Expr(Arg arg, char kind)       : arg(arg), kind(kind) {}
    Expr(Node * node)              : arg(node), kind('p') {}
    Expr(unboxed_int_type   value) : arg(value), kind('i') {}
    Expr(unboxed_float_type value) : arg(value), kind('f') {}
    Expr(unboxed_char_type  value) : arg(value), kind('c') {}
    Expr(unboxed_ptr_type  value)  : arg(value), kind('x') {}

    explicit operator bool() const { return kind != 'u'; }
  };
}

#include "cyrt/graph/cursor.hxx"
