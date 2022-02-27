#pragma once
#include "cyrt/llvm/config.hpp"
#include "cyrt/llvm/fwd.hpp"
#include "cyrt/llvm/llvmobj.hpp"
#include "cyrt/llvm/array_ref.hpp"
#include "cyrt/llvm/special_values.hpp"
#include "cyrt/llvm/type_traits.hpp"
#include "llvm/IR/DerivedTypes.h"
#include <iostream>
#include <vector>

namespace cyrt { namespace llvm
{
  /**
   * @brief Wrapper for @p Type objects.
   *
   * Elaborated types can be created by using the @p * operator (to create
   * pointers), the @p [] operator (to create arrays), or the @p () operator
   * (to create functions).
   *
   * Constant values can be created using the call operator, as in
   * <tt>i32(42)</tt> to create a 32-bit integer constant with value @p 42
   * (assuming @p i32 is a type wrapper for the 32-bit integer type).
   */
  struct type : llvmobj<Type, custodian<Type, no_delete>>
  {
    // Inherit constructors.
    using llvmobj_base_type::llvmobj;

    /// Creates a pointer type.
    type operator*() const;

    /// Creates a vector type.
    type operator*(size_t) const;
    friend type operator*(size_t, type);

    /// Creates an array type.
    type operator[](size_t) const;

    /// Creates a function type.
    type make_function(
        std::vector<Type*> const &, bool is_varargs = false
      ) const;

    #ifdef TEMPORARILY_DISABLED
    template<
        typename... Args
      , SPRITE_ENABLE_FOR_ALL_FUNCTION_PROTOTYPES(Args...)
      >
    type operator()(Args &&... argtypes) const;

    /**
     * @brief Creates a constant of the type represented by @p this, using @p
     * arg as the initializer.
     *
     * Synonymous with @p get_constant.  Implemented in get_constant.hpp.
     */
    template<
        typename Arg
      , SPRITE_ENABLE_FOR_ALL_CONSTANT_INITIALIZERS(Arg)
      >
    constant operator()(Arg &&) const;

    /**
     * @brief Creates a constant of the (array) type represented by @p this,
     * using @p arg as the initializer.
     *
     * Synonymous with @p get_constant.  Implemented in get_constant.hpp.  This
     * needs to be mentioned explicitly so that @p std::initializer_list will
     * be accepted.
     */
    constant operator()(any_array_ref const &) const;
    #endif
  };

  bool operator==(type const &, type const &);
  bool operator!=(type const &, type const &);
}}

namespace cyrt { namespace llvm { namespace types
{
  /// Creates an integer type of the specified bit width.
  type int_(size_t numBits);

  /// Creates an integer type the width of a native int.
  type int_();

  /// Creates an integer type the width of a native long.
  type long_();

  /// Creates an integer type the width of a native long long.
  type longlong();

  /// Creates a char type.
  type char_();

  /// Creates a bool type.
  type bool_();

  /**
   * @brief Creates a floating-point type (32-bit, by default).
   *
   * @p numBits should be 32, 64 or 128.
   */
  type float_(size_t numBits);

  /// Creates the 32-bit floating-point type.
  type float_();

  /// Creates the 64-bit floating-point type.
  type double_();

  /// Creates the 128-bit floating-point type.
  type longdouble();

  /// Creates the void type.
  type void_();

  #ifdef TEMPORARILY_DISABLED
  /// Creates the label type (for holding a @p block_address).
  type label();
  #endif

  /// Creates an anonymous struct (uniqued by structural equivalence).
  type struct_(std::vector<type> const & elements);

  /**
   * @brief Gets a struct by name.
   *
   * If the struct has not been created, a new opaque struct will be created.
   */
  type struct_(std::string const & name);

  /**
   * @brief Defines a struct.
   *
   * The struct must not already have a body (though, it may exist and be
   * opaque).
   */
  type struct_(
      std::string const & name, std::vector<type> const & elements
    );
}}}

namespace cyrt { namespace llvm
{
  /// Returns the array extents.
  std::vector<size_t> array_extents(type const &);

  /// Indicates whether the specified cast is permitted.
  bool is_castable(type src, type dst);

  /// Indicates whether the specified bitcast is permitted.
  bool is_bitcastable(type src, type dst);

  /**
   * @brief Applies type transformations as when passing a value to a function.
   *
   * See std::type_traits::decay.
   */

  type decay(type);

  /**
   * @brief Determines the common type of a group of types.
   *
   * See std::type_traits::common_type.
   */
  type common_type(std::vector<type> const &);

  /// Returns the size in bytes (with alignment padding).
  size_t sizeof_(type const &);

  /// Returns the size in bits (without padding).
  size_t bitwidth(type const &);

  /// Returns the name for struct types.
  std::string struct_name(type const &);

  /// Returns the subtypes, as defined by LLVM.
  std::vector<type> subtypes(type const &);
}}

