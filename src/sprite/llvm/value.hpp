#pragma once
#include <boost/any.hpp>
#include <boost/numeric/conversion/cast.hpp>
#include <boost/variant.hpp>
#include "llvm/IR/Value.h"
#include "llvm/IR/GlobalValue.h"
#include "sprite/llvm/config.hpp"
#include "sprite/llvm/fwd.hpp"
#include "sprite/llvm/param.hpp"
#include "sprite/llvm/type.hpp"
#include <type_traits>

#include <iostream> // DEBUG

namespace sprite { namespace llvm
{
  using literal_value = boost::variant<int64_t, double>;
  using LinkageTypes = ::llvm::GlobalValue::LinkageTypes;

  struct value_deleter
  {
    // A reference to the parent is held so that this value cannot be deleted
    // while its handle is extant.
    value_deleter(boost::any parent) : parent(parent) {}
    boost::any parent;
    void operator()(Value *) const;
  };

  struct value_custodian : custodian<Value, value_deleter>
  {
    static void onConstruct(llvmobj<Value, value_custodian> &);
    // Inherited onCopy and onDestroy are OK.
  };

  /// Wrapper for @p Value objects.
  // struct value : llvmobj<Value, custodian<Value, value_deleter>>
  struct value : llvmobj<Value, value_custodian>
  {
    // Inherit constructors.
    using llvmobj_base_type::llvmobj;

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

    // name
    std::string getName() const { return ptr()->getName(); }
    void setName(std::string const & name) { ptr()->setName(name); }

    // is_const
    bool getIsConst() const;
    void setIsConst(bool);

    // linkage
    LinkageTypes getLinkage() const;
    void setLinkage(LinkageTypes);

    // initializer
    value getInitializer() const;
    void setInitializer(value);

    /// Remove this value from its parent and delete it.
    void erase();

    friend value operator+(value, value);

    /// Evaluate constexprs, return the value.
    literal_value constexpr_value() const;

    using parent_type = boost::variant<boost::none_t, module, value>;

    /// Return a handle to the parent.
    parent_type parent() const;
  };

  value cast(value, type, bool src_is_signed=true, bool dst_is_signed=true);
  value bitcast(value, type);

  type typeof_(value);

  /// Produces a default-initialized value.
  value null_value(type);

}}
