/**
 * @file
 * @brief Defines the module class.
 */

#pragma once
#include "sprite/llvm/config.hpp"
#include "sprite/llvm/object.hpp"
#include "sprite/llvm/array_ref.hpp"
#include "llvm/IR/DataLayout.h"
#include "llvm/IR/DerivedTypes.h"
#include "llvm/IR/LLVMContext.h"
#include "llvm/IR/Module.h"

namespace sprite { namespace llvm
{
  /// Get the LLVM context.
  LLVMContext & getContext();

  /**
   * @brief
   * Represents an LLVM module.
   *
   * @details
   * Among other things, provides a convenient interface for building LLVM
   * types.  LLVM types are created using named type-creation methods.
   *
   * Example:
   *
   * @snippet types.cpp Creating basic types
   */
  struct module : object<Module>
  {
    typedef object<Module> base_type;

  public:

    using object<Module>::object;

    /// Creates a new module.
    explicit module(
        string_ref const & name
      , LLVMContext & context = getContext()
      )
      : base_type(SPRITE_APICALL(new Module(name, context)))
    {}

    // Default copy, assignment, and destructor are fine.

    /// Gets the associated LLVM context.
    LLVMContext & context() const
      { return px ? px->getContext() : getContext(); }

    /**
     * Returns the named global value.  Raises value_error if the global does
     * not exist.
     */
    global getglobal(string_ref) const;

    /// True if the named global value exists in this module.
    bool hasglobal(string_ref) const;

    friend bool operator==(module const & lhs, module const & rhs)
      { return lhs.ptr() == rhs.ptr(); }

    friend bool operator!=(module const & lhs, module const & rhs)
      { return !(lhs == rhs); }
  };
}}

