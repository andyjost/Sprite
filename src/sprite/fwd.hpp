#pragma once
#include <cstdint>
#include <limits>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace sprite
{
  class Fingerprint;
  struct Configuration;
  struct Cursor;
  struct Expr;
  struct InfoTable;
  struct InterpreterState;
  struct Node;
  struct Queue;
  struct Redex;
  struct RuntimeState;
  struct SetFunctionEval;
  struct Typedef;
  struct UnionFind;
  struct Variable;
  union Arg;

  enum StepStatus { E_OK, E_UNWIND, E_RESIDUAL, E_RESTART };

  using flag_type = std::uint8_t;
  using hash_type = std::size_t;
  using id_type = size_t;
  using index_type = std::uint16_t;
  using memo_type = std::unordered_map<void *, Arg>;
  using qid_type = size_t;
  using sid_type = size_t;
  using vid_type = size_t;
  using std::size_t;
  using stepfunc_type = StepStatus (*)(RuntimeState *, Configuration *, Redex const *);
  using tag_type = int16_t;
  using typecheckfunc_type = void (*)(Node *);
  using unboxed_char_type = signed char;
  using unboxed_float_type = double;
  using unboxed_int_type = int64_t;

  struct Head { InfoTable const * info; };

  static constexpr id_type    NOCID = std::numeric_limits<sid_type>::max();
  static constexpr index_type NOINDEX = std::numeric_limits<index_type>::max();
  static constexpr qid_type   NOQID = std::numeric_limits<qid_type>::max();
  static constexpr sid_type   NOSID = std::numeric_limits<sid_type>::max();
  static constexpr sid_type   NOVID = std::numeric_limits<vid_type>::max();
  static constexpr size_t     NOLIMIT = std::numeric_limits<size_t>::max();
  static constexpr tag_type   NOTAG = std::numeric_limits<tag_type>::min();

  static constexpr tag_type T_UNBOXED = -8;
  static constexpr tag_type T_SETGRD  = -7;
  static constexpr tag_type T_FAIL    = -6;
  static constexpr tag_type T_CONSTR  = -5;
  static constexpr tag_type T_FREE    = -4;
  static constexpr tag_type T_FWD     = -3;
  static constexpr tag_type T_CHOICE  = -2;
  static constexpr tag_type T_FUNC    = -1;
  static constexpr tag_type T_CTOR    =  0;

  enum ChoiceState { UNDETERMINED=0, LEFT=-1, RIGHT=1 };
  enum ConstraintType { STRICT_CONSTRAINT, NONSTRICT_CONSTRAINT, VALUE_BINDING };
}
