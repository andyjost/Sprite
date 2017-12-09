/**
 * @file
 * @brief Utilities for printing human-readable type names.
 */

#pragma once
#include <cstdlib>
#include <cxxabi.h>
#include <memory>
#include <string>
#include <typeinfo>

namespace sprite { namespace llvm
{
  /// Demangles a symbol name (e.g., one returned through std::typeinfo).
  std::string demangle(std::string const &);

  /// Returns a human-readable name for certain types.
  template<typename T> struct typename_impl
    { static std::string name() { return demangle(typeid(T).name()); } };

  /// Declares a specialization of @p typename_impl.
  #define SPRITE_SPECIALIZE_TYPENAME(name_)               \
      template<> struct typename_impl<name_>              \
        { static std::string name() { return #name_; } }; \
    /**/

  /// Returns a human-readable version of a type name.
  template<typename T>
  inline std::string typename_()
    { return demangle(typename_impl<T>::name()); }

  /// Returns a human-readable version of a type name.
  template<typename T>
  inline std::string typename_(T const &)
    { return demangle(typename_impl<T>::name()); }
}}

