#pragma once
#include "sprite/llvm/config.hpp"
#include "sprite/llvm/fwd.hpp"
#include "sprite/llvm/type.hpp"
#include "llvm/IR/Value.h"

namespace sprite { namespace llvm
{
  /// Wrapper for @p ::llvm::Value objects.
  struct value : object<::llvm::Value>
  {
    using basic_type = Type;
    using object<::llvm::Value>::object;

    /// Create a literal integer.
    value(int64_t);

    /// Create a literal floating-point value.
    value(double);

    /// Get a string representation.
    std::string str() const;
  };

  // bool operator==(value, value);
  // bool operator!=(value, value);
  std::ostream & operator<<(std::ostream &, value const &);
  type typeof_(value);

  bool is_constdata(value);
}}
