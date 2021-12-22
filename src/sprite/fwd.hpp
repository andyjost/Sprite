#pragma once
#include <cstdint>
#include <limits>

namespace sprite
{
  class Fingerprint;
  class RuntimeState;
  struct Expr;
  struct InfoTable;
  struct Typedef;
  using Node = void *;

  using std::size_t;
  using arity_type = std::uint16_t;
  using flag_type = std::uint16_t;
  using formatfunc_type = void (*)(char const **);
  using typecheckfunc_type = void (*)(Node);
  using stepfunc_type = void (*)(RuntimeState *, Node);

  static constexpr arity_type NOINDEX = std::numeric_limits<arity_type>::max();
  static constexpr size_t NOLIMIT = std::numeric_limits<size_t>::max();
}
