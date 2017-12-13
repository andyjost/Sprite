/**
 * @file
 * @brief Defines class @p llvmobj.
 */

#pragma once
#include "sprite/llvm/fwd.hpp"
#include <cstddef>
#include <type_traits>
#include <iosfwd>
#include "llvm/Support/raw_os_ostream.h"

namespace sprite { namespace llvm
{
  /**
   * @brief Base class used to wrap an LLVM API object.
   *
   * It is assumed LLVM will manage the lifetime of the raw pointer.  An
   * instance of this type can be created directly, though normally it's easier
   * to use one of the module::wrap methods.
   */
  template<typename T> class llvmobj
  {
  protected:

    /// The wrapped pointer to an LLVM object.
    T * px;

  public:

    /// The underlying LLVM type.
    typedef T element_type;

    /// Explicit null construction.
    llvmobj(std::nullptr_t) : px(nullptr) {}

    /// Regular constructor to capture an LLVM API object.
    template<
        typename U
      , typename = typename std::enable_if<std::is_base_of<T,U>::value>::type
      >
    llvmobj(U * p) : px(p)
    {}

    /// Implicitly-converting constructor.
    template<
        typename U
      , typename = typename std::enable_if<std::is_base_of<T,U>::value>::type
      >
    llvmobj(llvmobj<U> const & arg) : px(arg.ptr())
    {}

    // Default copy and assignment are OK.

    /// Conversion to the LLVM object.
    operator T *() const { return px; }

    /// Named conversion to the LLVM object.
    T * ptr() const { return px; }

    /// Member access for the LLVM object.
    T * operator->() const { assert(px); return px; }

    /// Returns the object pointer as an integer.
    size_t id() const { return (size_t) px; }
  };

  // ptr() extracts an LLVM API pointer from any suitable object.
  template<typename T> T * ptr(llvmobj<T> const & tp) { return tp.ptr(); }
  template<typename T> T * ptr(T * t) { return t; }
  // This version allows more flexibilty with constant expressions (cf.
  // is_constarg, which needs to match a function signature for arguments it
  // will eventually reject).  There is no definition.
  void * ptr(...);

  /// Streams the LLVM representation of an object.
  template<typename T>
  std::ostream & operator<<(std::ostream & os, llvmobj<T> const & obj)
  {
    auto && out = ::llvm::raw_os_ostream(os);
    out << *obj.ptr();
    return os;
  }
}}

