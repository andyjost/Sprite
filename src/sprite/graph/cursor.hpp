#pragma once
#include <cassert>
#include "sprite/fwd.hpp"

namespace sprite
{
  union Arg
  {
    Node *             node;
    unboxed_int_type   ub_int;
    unboxed_float_type ub_float;
    unboxed_char_type  ub_char;
    void *             blob;
    Head *             head;

    Arg(Node * value=nullptr) : node(value) {}
    Arg(int16_t value)        : ub_int(value) {}
    Arg(int32_t value)        : ub_int(value) {}
    Arg(int64_t value)        : ub_int(value) {}
    Arg(float value)          : ub_float(value) {}
    Arg(double value)         : ub_float(value) {}
    Arg(char value)           : ub_char(value) {}
    Arg(signed char value)    : ub_char(value) {}
    Arg(unsigned char value)  : ub_char(value) {}

    template<typename T> Arg & operator=(T &&);
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

    friend bool operator==(Cursor lhs, Cursor rhs) { return lhs.arg == rhs.arg; }
    friend bool operator!=(Cursor lhs, Cursor rhs) { return !(lhs==rhs); }
    explicit operator bool() const { return arg; }
    Arg * operator->() const { return this->arg; }
    Arg & operator*() const { return *this->arg; }
    operator Node *&() const { assert(arg && kind=='p'); return this->arg->node; }
    void * id() const { return kind=='p' ? (void *) arg->node : (void *) arg; }
    InfoTable const * info() const;
    Cursor & skipfwd();
  };
}

#include "sprite/graph/cursor.hxx"
