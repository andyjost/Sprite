#pragma once
#include <boost/numeric/conversion/cast.hpp>
#include <boost/variant.hpp>
#include "llvm/IR/Value.h"
#include "sprite/llvm/config.hpp"
#include "sprite/llvm/fwd.hpp"
#include "sprite/llvm/param.hpp"
#include "sprite/llvm/type.hpp"
#include <type_traits>

namespace sprite { namespace llvm
{
  using literal_value = boost::variant<int64_t, double>;

  /// Wrapper for @p Value objects.
  struct value : llvmobj<Value>
  {
    using basic_type = Type;
    using llvmobj<Value>::llvmobj;

    /// Create an undef value (used for default initialization).
    value(boost::none_t);

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
    literal_value constexpr_value() const;
  };

  // bool operator==(value, value);
  // bool operator!=(value, value);

  value cast_(value, type, bool src_is_signed=true, bool dst_is_signed=true);
  value bitcast_(value, type);

  std::ostream & operator<<(std::ostream &, value const &);
  type typeof_(value);

  /// Produces a default-initialized value.
  value null_value(type);

}}
