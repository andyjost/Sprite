/**
 * @brief Used by CPP files to get the current ::llvm::IRBuilder.
 *
 * Clients of the main interface do not need to depend on IRBuilder.h.
 */
#pragma once
#include "cyrt/llvm/scope.hpp"
#include "llvm/IR/IRBuilder.h"

namespace cyrt { namespace llvm
{
  // Returns the current ::llvm::IRBuilder<> or raises an exception if none is
  // available.
  ::llvm::IRBuilder<> & current_builder();
}}
