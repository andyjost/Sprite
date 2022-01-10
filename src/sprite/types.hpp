#pragma once
#include <unordered_map>
#include <unordered_set>
#include "sprite/fwd.hpp"

namespace sprite
{
  using std::size_t;

  using cid_type = size_t;
  using flag_type = std::uint16_t;
  using hash_type = std::size_t;
  using index_type = std::uint16_t;
  using qid_type = size_t;
  using sid_type = size_t;
  using stepfunc_type = void (*)(RuntimeState *, Node *);
  using tag_type = int16_t;
  using typecheckfunc_type = void (*)(Node *);

  using memo_type = std::unordered_map<void *, Arg>;
  using sid_set_type = std::unordered_set<sid_type>;

  static constexpr index_type NOINDEX = std::numeric_limits<index_type>::max();
  static constexpr sid_type NOSID = std::numeric_limits<sid_type>::max();
  static constexpr size_t NOLIMIT = std::numeric_limits<size_t>::max();
}
