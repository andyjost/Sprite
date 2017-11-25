#pragma once
#include "sprite/llvm/config.hpp"
#include "sprite/llvm/fwd.hpp"
#include "sprite/llvm/object.hpp"
// #include "sprite/llvm/core/operator_flags.hpp"
#include "sprite/llvm/array_ref.hpp"
#include "sprite/llvm/special_values.hpp"
#include "sprite/llvm/type_traits.hpp"
#include "llvm/IR/DerivedTypes.h"
#include <iostream>
#include <vector>

namespace sprite { namespace llvm
{
  /**
   * @brief Wrapper for @p ::llvm::Type objects.
   *
   * Elaborated types can be created by using the @p * operator (to create
   * pointers), the @p [] operator (to create arrays), or the @p () operator
   * (to create functions).
   *
   * Constant values can be created using the call operator, as in
   * <tt>i32(42)</tt> to create a 32-bit integer constant with value @p 42
   * (assuming @p i32 is a type wrapper for the 32-bit integer type).
   */
  struct type : object<::llvm::Type>
  {
    using basic_type = Type;
    using object<::llvm::Type>::object;

    /**
     * @brief Creates a pointer type.
     *
     * @snippet types.cpp Creating pointer types
     */
    type operator*() const;

    /**
     * @brief Creates an array type.
     *
     * @snippet types.cpp Creating array types
     */
    type operator[](size_t size) const;

    /// Creates a function type.
    type make_function(
        std::vector<::llvm::Type*> const &, bool is_varargs = false
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

    friend std::ostream & operator<<(std::ostream & os, type const & ty)
      { return os << typename_(*ty.ptr()); }

  private:

    #ifdef SPRITE3
    static_assert(
        std::is_base_of<basic_type, T>::value, "Expected an LLVM Type object"
      );
    #endif
  };

  inline bool operator==(type const & lhs, type const & rhs)
    { return lhs.ptr() == rhs.ptr(); }

  inline bool operator!=(type const & lhs, type const & rhs)
    { return !(lhs == rhs); }

  /// Returns the size in bytes.
  uint64_t sizeof_(type const &);

  #ifdef TEMPORARILY_DISABLED
  // Array query functions.
  // Returns the array element type.
  type element_type(type const &);
  type_with_flags element_type(type const &);

  /// Returns the array length.
  uint64_t len(type const &);
  /// Removes all array extents.
  type remove_all_extents(type const &);

  // Pointer query functions.
  // Returns the pointer element type.
  type element_type(type const &);

  // Function query functions.
  // Returns the function result type.
  type result_type(type const &);
  // Returns the type of function parameter i.
  type element_type(type const &, unsigned);
  // Returns the number of function parameters.
  unsigned len(type const &);

  // Struct query functions.
  /// Returns the number of elements in the struct.
  uint64_t len(type const &);
  /// Returns the type at index i.
  type element_type(type const &, unsigned i);

  // Generic query functions.
  type_with_flags element_type(type_with_flags const &);
  type element_type(type const &, unsigned);
  uint64_t len(type const &);
  type remove_all_extents(type const &);
  type result_type(type const &);
  #endif
}}

namespace sprite { namespace llvm { namespace types
{
  /// Creates an integer type of the specified bit width.
  type int_(unsigned numBits);

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

