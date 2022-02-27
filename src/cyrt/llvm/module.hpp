/**
 * @file
 * @brief Defines the module class.
 */

#pragma once
#include "llvm/IR/DataLayout.h"
#include "llvm/IR/DerivedTypes.h"
#include "llvm/IR/GlobalValue.h"
#include "llvm/IR/LLVMContext.h"
#include "llvm/IR/Module.h"
#include "cyrt/llvm/array_ref.hpp"
#include "cyrt/llvm/config.hpp"
#include "cyrt/llvm/fwd.hpp"
#include "cyrt/llvm/globalname.hpp"
#include "cyrt/llvm/llvmobj.hpp"
#include <string>

namespace cyrt { namespace llvm
{
  using LinkageTypes = ::llvm::GlobalValue::LinkageTypes;

  /// Get the LLVM context.
  LLVMContext & getContext();

  using module_policy = count_objects<Module, custodian<Module>>;

  /// An LLVM module.
  struct module : llvmobj<Module, module_policy>
  {
    // Inherit constructors.
    using llvmobj_base_type::llvmobj;

    /// Creates a new module.
    explicit module(
        std::string const & name
      , LLVMContext & context = getContext()
      )
      : llvmobj_base_type(new Module(name, context))
    {
    }

    // Default copy, assignment, and destructor are fine.

    /// Gets the associated LLVM context.
    LLVMContext & context() const
      { return px ? px->getContext() : getContext(); }

    /// Declare a global variable.
    value def(std::string const &, type, bool, LinkageTypes, value);
  };

  inline bool operator==(module const & lhs, module const & rhs)
    { return lhs.ptr() == rhs.ptr(); }

  inline bool operator!=(module const & lhs, module const & rhs)
    { return !(lhs == rhs); }
}}

