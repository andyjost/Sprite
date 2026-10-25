#pragma once
#include <cstdint>
#include "curryrt/fwd.hpp"
#include <string>

// The argument slot of a node.  The union stands in a header of its own so
// that it is complete wherever a node type with a member Arg data[N] is
// instantiated (curryrt/builtins.hpp instantiates them in its inline
// functions, before curryrt/graph/node.hpp is included).  Clang instantiates
// a function template at its first point of instantiation, where GCC uses
// the end of the translation unit, so the completeness of Arg must not
// depend on the order of the later includes.  The constructor from a
// Cursor, the assignment and repr are defined with Cursor (cursor.hpp).
namespace curryrt
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
    // The 64-bit integer under both of its names: int64_t is long on Linux
    // and long long on macOS, and a literal of the other type would have no
    // exact match.
    Arg(long value)              : ub_int(value)   {}
    Arg(long long value)         : ub_int(value)   {}
    Arg(xid_type value)          : cid(value)      {}
    Arg(float value)             : ub_float(value) {}
    Arg(double value)            : ub_float(value) {}
    // A char holds one byte; a Char node holds a code point.  The byte is
    // taken unsigned, so that a value above 127 does not sign-extend.
    Arg(char value)              : ub_char((unsigned char) value) {}
    Arg(signed char value)       : ub_char((unsigned char) value) {}
    Arg(unsigned char value)     : ub_char(value)  {}
    Arg(char32_t value)          : ub_char(value)  {}
    Arg(InfoTable const * value) : xinfo(value)    {}
    template<typename T>
    Arg(T const * value)         : blob(value)     {}
    Arg(std::nullptr_t)          : blob(nullptr)   {}
    Arg(Cursor const &);
    Arg(Variable const &);

    template<typename T> Arg & operator=(T &&);
    std::string repr() const;
  };

}
