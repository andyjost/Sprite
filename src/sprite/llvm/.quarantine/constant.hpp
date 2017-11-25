#pragma once
#include "sprite/llvm/type.hpp"
#include "sprite/llvm/value.hpp"
#include "llvm/IR/Constants.h"

namespace sprite { namespace llvm
{
  // API: constant
  template<>
  struct constobj<::llvm::Constant> : valueobj<::llvm::Constant>
  {
    using basic_type = Constant;
    using valueobj<::llvm::Constant>::valueobj;

    /// Gets an element of a constant aggregate.
    constant operator[](size_t i) const
    {
      auto const ii = static_cast<unsigned>(i);
      return constant(SPRITE_APICALL((*this)->getAggregateElement(ii)));
    }

    #ifdef SPRITE3
    // Define in-place operators.
    #define SPRITE_LHS_TYPE constant
    #include "sprite/backend/core/detail/declare_class_operators.def"
    #endif
  };

  template<typename T>
  struct constobj : valueobj<T>
  {
    using basic_type = Constant;
    using valueobj<T>::valueobj;

    /// Gets an element of a constant aggregate.
    constant operator[](size_t i) const
    {
      auto const ii = static_cast<unsigned>(i);
      return constant(SPRITE_APICALL((*this)->getAggregateElement(ii)));
    }

  private:

    static_assert(
        std::is_base_of<basic_type, T>::value, "Expected an LLVM Constant object"
      );
  };
}}
