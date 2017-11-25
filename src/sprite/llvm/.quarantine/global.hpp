#pragma once
#include "sprite/llvm/constant.hpp"
#include "sprite/llvm/label.hpp"
#include "sprite/llvm/ref.hpp"
#include "sprite/llvm/value.hpp"
#include "sprite/llvm/exceptions.hpp"
#include "sprite/llvm/type_erasures.hpp"
#include "llvm/IR/GlobalValue.h"
#include "llvm/IR/GlobalVariable.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/Instructions.h"
//

namespace sprite { namespace llvm
{
  // FIXME: becuase globalvar uses basic_reference as its base, but this class
  // uses constobj, there is no automatic conversion, and things like
  // operator[] do not easily forward.  Can globalobj use basic_reference, too
  // (i.e., even for functions?).
  template<typename T> struct globalobj : constobj<T>
  {
    using basic_type = GlobalValue;
    using constobj<T>::constobj;

    /// Sets the initializer for a global variable (excluding arrays).
    template<typename U, typename = DISABLE_IF_ARRAY_LIKE(U)>
    globalvar set_initializer(U const & value);

    /// Sets the initializer for a global array variable.
    globalvar set_initializer(any_array_ref const & value);

    /// Indicates whether an initializer is set.
    bool has_initializer() const
      { return this->as_globalvar().has_initializer(); }

    /// Returns the initializer, or an empty object.
    constant get_initializer() const
      { return this->as_globalvar().get_initializer(); }

    // FIXME: support/casting.hpp probably needs to understand basic_reference.
    globalvar as_globalvar() const;

    /**
     * @brief Takes the address of a global value.
     *
     * @snippet constexprs.cpp Computing addresses
     */
    constant operator&() const;

  private:

    static_assert(
        std::is_base_of<basic_type, T>::value
      , "Expected an LLVM GlobalValue object"
      );
  };

  // API: globalvar
  template<> struct globalobj<GlobalVariable> : basic_reference<globalvaraddr>
  {
    using basic_reference<globalvaraddr>::basic_reference;
    using basic_reference<globalvaraddr>::operator=;

    /// Sets the initializer for a global variable (excluding arrays).
    template<typename U, typename = DISABLE_IF_ARRAY_LIKE(U)>
    globalvar & set_initializer(U const & value);

    /// Sets the initializer for a global array variable.
    globalvar & set_initializer(any_array_ref const & value);

    /// Indicates whether an initializer is set.
    bool has_initializer() const;

    /// Returns the initializer, or an empty object.
    constant get_initializer() const;

    // FIXME: temporary until dyn_cast is fixed.
    globalvar as_globalvar() const { return *this; }
  };

  // API: function
  template<> struct globalobj<Function> : constobj<Function>
  {
    using basic_type = Function;
    using constobj<Function>::constobj;

    /**
     * @brief Inserts a call instruction in the current context.
     *
     * Each argument can be a value, or raw initializer.  A raw initializer is
     * any object -- such as a built-in integer or floating-point value, to
     * name two -- that can be used to initialize a constant.
     */
    template<
        typename... Args
      , SPRITE_ENABLE_FOR_ALL_VALUE_INITIALIZERS(Args...)
      >
    value operator()(Args &&... args) const;

    /**
     * @brief Takes the address of a function.
     *
     * @snippet defs.cpp Taking a function address
     */
    constant operator&() const;

    /// Returns the function entry point.
    label entry() const;

    /// Returns the function return type.
    type return_type() const
      { return type(SPRITE_APICALL(ptr()->getReturnType())); }

    /// Indicates whether the function has a body.
    bool empty() const { return SPRITE_APICALL(ptr()->empty()); }
  };

  inline global module::getglobal(string_ref name) const
  {
    ::llvm::GlobalValue * gv = ptr()->getNamedValue(name);
    if(!gv)
      throw value_error("global object not found");
    return global(gv);
  }

  inline bool module::hasglobal(string_ref name) const
    { return ptr()->getNamedValue(name); }


  /// Get an argument (by its position) for the function currently in scope.
  value arg(size_t);

  /// Get an argument (by its name) for the function currently in scope.
  value arg(string_ref const &);
}}

#include "sprite/llvm/global_impl.hpp"

