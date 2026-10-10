#pragma once
#include <cstdint>
#include <limits>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <variant>
#include <vector>

namespace cyrt
{
  struct Checker;
  struct Configuration;
  struct Cursor;
  struct DataType;
  struct Expr;
  struct Fingerprint;
  struct InfoTable;
  struct InterpreterState;
  struct Node;
  struct PartApplicNode;
  struct Queue;
  struct RuntimeState;
  struct Set;
  struct ShowMonitor;
  struct Trace;
  struct UnionFind;
  struct Variable;
  struct Walk;
  struct Walk2;
  union Arg;

  enum Visibility : bool { PUBLIC = true, PRIVATE = false };
  enum TraceOpt : bool { TRACE = true, NOTRACE = false };
  enum ShowStyle { SHOW_STR, SHOW_STR_SUBST_FREEVARS, SHOW_REPR };
  enum SubstFreevars : bool { SUBST_FREEVARS=true, PLAIN_FREEVARS=false };
  enum SetFStrategy { SETF_EAGER, SETF_LAZY };
  // What a failure that comes from an argument of a set function does when
  // the capsule demands it (the interpreter flag setfunction_failures):
  // drops its alternative, or fails the set function.  See
  // RuntimeState::failure_escapes.
  enum SetFFailures { SETF_FAILURES_ENCAPSULATE, SETF_FAILURES_ESCAPE };
  using tag_type = int16_t;

  using flag_type = std::uint8_t;
  using hash_type = std::size_t;
  using index_type = std::uint16_t;
  using memo_type = std::unordered_map<void *, Arg>;
  using std::size_t;
  using stepfunc_type = tag_type (*)(RuntimeState *, Configuration *);
  using generator_next_type = Node * (*)(void *);
  // Takes or releases the reference a generator node owns (see
  // biGeneratorNode in builtins.hpp).
  using generator_hold_type = void (*)(void *);
  // A Char holds one Unicode code point.  Text crosses the boundary of the
  // runtime as UTF-8; see cyrt/utf8.hpp.
  using unboxed_char_type = char32_t;
  using unboxed_float_type = double;
  using unboxed_int_type = int64_t;
  using unboxed_ptr_type = void *;
  using xid_type = size_t;
  using MDValue     = std::variant<std::string, int, bool>;
  using Metadata    = std::unordered_map<std::string, MDValue>;

  struct Head { InfoTable const * info; };

  static constexpr index_type NOINDEX = std::numeric_limits<index_type>::max();
  static constexpr size_t     NOLIMIT = std::numeric_limits<size_t>::max();
  static constexpr tag_type   NOTAG   = std::numeric_limits<tag_type>::min();
  static constexpr xid_type   NOXID   = std::numeric_limits<xid_type>::max();

  static constexpr tag_type E_DIVERGE  = -18; // a capsule read a binding of an enclosing configuration; see RuntimeState::diverge
  static constexpr tag_type E_SETFAIL  = -17; // a boxed failure fails the set function; see RuntimeState::fail_capsule
  static constexpr tag_type E_TERMINATE = -16; // the step limit was reached; see RuntimeState::step_limit
  static constexpr tag_type E_UNWIND   = -15; // C-stack limit reached; unwind to procD
  static constexpr tag_type E_GC       = -14; // time to run GC
  static constexpr tag_type E_ROTATE   = -13; // time to rotate the queu
  static constexpr tag_type E_ERROR    = -12;
  static constexpr tag_type E_RESIDUAL = -11;
  static constexpr tag_type E_RESTART  = -10;
  static constexpr tag_type T_PAD      = -9;
  static constexpr tag_type T_UNBOXED  = -8;
  static constexpr tag_type T_SETGRD   = -7;
  static constexpr tag_type T_FAIL     = -6;
  static constexpr tag_type T_CONSTR   = -5;
  static constexpr tag_type T_FREE     = -4;
  static constexpr tag_type T_FWD      = -3;
  static constexpr tag_type T_CHOICE   = -2;
  static constexpr tag_type T_FUNC     = -1;
  static constexpr tag_type T_CTOR     =  0;

  enum ChoiceState { UNDETERMINED=0, LEFT=-1, RIGHT=1 };
  enum ConstraintType { STRICT_CONSTRAINT, NONSTRICT_CONSTRAINT, VALUE_BINDING };
}
