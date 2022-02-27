#pragma once
#include "cyrt/builtins.hpp"

namespace cyrt
{
  // prelude/constr.cpp
  extern InfoTable const concurrentAnd_Info;
  extern InfoTable const constrEq_Info;
  extern InfoTable const nonstrictEq_Info;
  extern InfoTable const seq_Info;

  // prelude/apply.cpp
  extern InfoTable const apply_Info;
  extern InfoTable const applygnf_Info;
  extern InfoTable const applyhnf_Info;
  extern InfoTable const applynf_Info;
  extern InfoTable const cond_Info;

  // prelude/testing.cpp -- OK TO REMOVE
  extern InfoTable const not_Info;
}
