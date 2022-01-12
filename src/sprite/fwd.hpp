#pragma once
#include <cstdint>
#include <limits>
#include <unordered_map>
#include <unordered_set>

namespace sprite
{
  struct Cursor;
  struct Expr;
  struct Node;
  union Arg;

  struct InfoTable;
  struct Typedef;

  class Fingerprint;
  struct Bindings;
  struct Configuration;
  struct InterpreterState;
  struct Residuals;
  struct RuntimeState;
  struct SetFunctionEval;
  struct StrictConstraints;
  struct Queue;

  using cid_type = size_t;
  using flag_type = std::uint8_t;
  using hash_type = std::size_t;
  using index_type = std::uint16_t;
  using memo_type = std::unordered_map<void *, Arg>;
  using qid_type = size_t;
  using sid_type = size_t;
  using std::size_t;
  using stepfunc_type = void (*)(RuntimeState *, Node *);
  using tag_type = int16_t;
  using typecheckfunc_type = void (*)(Node *);
  using unboxed_char_type = signed char;
  using unboxed_float_type = double;
  using unboxed_int_type = int64_t;
  using vid_type = size_t;

  struct Head { InfoTable const * info; };

  static constexpr index_type NOINDEX = std::numeric_limits<index_type>::max();
  static constexpr sid_type   NOSID = std::numeric_limits<sid_type>::max();
  static constexpr sid_type   NOQID = std::numeric_limits<qid_type>::max();
  static constexpr size_t     NOLIMIT = std::numeric_limits<size_t>::max();
  static constexpr tag_type   NOTAG = std::numeric_limits<tag_type>::min();

  static constexpr tag_type T_SETGRD = -7;
  static constexpr tag_type T_FAIL   = -6;
  static constexpr tag_type T_CONSTR = -5;
  static constexpr tag_type T_FREE   = -4;
  static constexpr tag_type T_FWD    = -3;
  static constexpr tag_type T_CHOICE = -2;
  static constexpr tag_type T_FUNC   = -1;
  static constexpr tag_type T_CTOR   =  0;
}
