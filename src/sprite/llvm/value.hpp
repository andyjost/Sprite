#pragma once
#include "sprite/llvm/config.hpp"
#include "sprite/llvm/fwd.hpp"
#include "sprite/llvm/param.hpp"
#include "sprite/llvm/type.hpp"
#include "llvm/IR/Value.h"
#include <type_traits>
#include <boost/numeric/conversion/cast.hpp>
#include <boost/variant.hpp>

namespace sprite { namespace llvm
{
  using literal_value = boost::variant<int64_t, double>;

  /// Wrapper for @p Value objects.
  struct value : llvmobj<Value>
  {
    using basic_type = Type;
    using llvmobj<Value>::llvmobj;

    /// Create a value from any convertible type.
    // template<typename T> value(T);

    /// Create a value from a literal integer.
    static value from_bool(bool);
    value(param<bool> const & v) : value(from_bool(v)) {}

    /// Create a value from a literal Boolean.
    static value from_int(int64_t);
    value(param<signed char, int64_t> const & v) : value(from_int(v)) {}
    value(param<unsigned char, int64_t> const & v) : value(from_int(v)) {}
    value(param<int16_t, int64_t> const & v) : value(from_int(v)) {}
    value(param<int32_t, int64_t> const & v) : value(from_int(v)) {}
    value(param<int64_t> const & v) : value(from_int(v)) {}

    /// Create a value from a literal floating-point value.
    static value from_double(double);
    value(param<float> const & v) : value(from_double(v)) {}
    value(param<double> const & v) : value(from_double(v)) {}

    /// Evaluate constexprs, return the value.
    literal_value eval() const;

    /// Get the string representation.
    std::string str() const;
  };

  // bool operator==(value, value);
  // bool operator!=(value, value);
  std::ostream & operator<<(std::ostream &, value const &);
  type typeof_(value);
}}
