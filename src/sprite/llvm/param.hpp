#pragma once
#include <iostream>

namespace sprite { namespace llvm
{
  // Implements parameter forwarding free of implicit conversions.
  template<typename From, typename To=From>
  struct param
  {
    template<
        typename U
      , typename = typename std::enable_if<std::is_same<U, From>::value>::type
      >
    param(U const & arg) : stored(arg)
    {}
    operator To const &() const { return stored; }
    To stored;
  };
}}

