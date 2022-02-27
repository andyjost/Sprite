/**
 * @file
 * @brief Defines class @p llvmobj.
 */

#pragma once
#include "cyrt/llvm/fwd.hpp"
#include <cstddef>
#include <iosfwd>
#include "llvm/Support/raw_os_ostream.h"
#include <memory>
#include <type_traits>
#include <unordered_map>

#include <iostream>

namespace cyrt { namespace llvm
{
  /**
   * @brief Base class used to wrap an LLVM API object.
   *
   * It is assumed LLVM will manage the lifetime of the raw pointer.  An
   * instance of this type can be created directly, though normally it's easier
   * to use one of the module::wrap methods.
   *
   * The policy is used to implement resource management, which varies by type
   * T.  It must conform to the following interface.
   *
   *     struct Policy
   *     {
   *       // Called after an llvmobj is constructed.
   *       static void onConstruct(llvmobj<T, Policy> &, Deleter=Deleter());
   *
   *       // Called after an llvmobj is copied.
   *       template<typename U>
   *       static void onCopy(llvmobj<T, Policy> & copy, llvmobj<U, Policy> const & copied);
   *
   *       // Called before an llvmobj is destroyed.
   *       static void onDestroy(llvmobj<T, Policy> &);
   *     };
   */
  template<typename T, typename Policy> struct llvmobj
  {
  protected:

    /// The wrapped pointer to an LLVM object.
    T * px;

    /// Used by derived classes to avoid repeating template parameters.
    using llvmobj_base_type = llvmobj<T, Policy>;

  public:

    /// The underlying LLVM type.
    typedef T element_type;

    /// Explicit null construction.
    llvmobj(std::nullptr_t) : px(nullptr)
      { Policy::onConstruct(*this); }

    /// Regular constructor to capture an LLVM API object.
    template<
        typename U
      , typename = typename std::enable_if<std::is_base_of<T,U>::value>::type
      >
    llvmobj(U * p) : px(p)
      { Policy::onConstruct(*this); }

    /// Copy.
    llvmobj(llvmobj const & arg) : px(arg.ptr())
      { Policy::onCopy(*this, arg); }

    template<
        typename U
      , typename = typename std::enable_if<std::is_base_of<T,U>::value>::type
      >
    llvmobj(llvmobj<U, Policy> const & arg) : px(arg.ptr())
      { Policy::onCopy(*this, arg); }

    /// Assignment.
    llvmobj & operator=(llvmobj const & arg)
    {
      if(ptr() != arg.ptr())
      {
        this->~llvmobj();
        new(this) llvmobj(arg);
      }
      return *this;
    }

    template<
        typename U
      , typename = typename std::enable_if<std::is_base_of<T,U>::value>::type
      >
    llvmobj & operator=(llvmobj<U, Policy> const & arg)
    {
      if(ptr() != arg.ptr())
      {
        this->~llvmobj();
        new(this) llvmobj(arg);
      }
      return *this;
    }

    // Move.
    llvmobj(llvmobj && arg) : px(arg.ptr())
      { arg.px = nullptr; }

    template<
        typename U
      , typename = typename std::enable_if<std::is_base_of<T,U>::value>::type
      >
    llvmobj(llvmobj<U, Policy> && arg) : px(arg.ptr())
      { arg.px = nullptr; }

    // Destructor.
    ~llvmobj() { Policy::onDestroy(*this); }

    /// Conversion to the LLVM object.
    operator T *() const { return px; }

    /// Named conversion to the LLVM object.
    T * ptr() const { return px; }

    /// Member access for the LLVM object.
    T * operator->() const { assert(px); return px; }

    /// Returns the object pointer as an integer.
    size_t id() const { return (size_t) px; }
  };

  struct empty_object_policy
  {
    static void onConstruct(...) {}
    static void onCopy(...) {}
    static void onDestroy(...) {}
  };

  /// The count of extant objects associated with @p Tag.
  template<typename Tag> struct object_count { static size_t num; };
  template<typename Tag> size_t object_count<Tag>::num = 0;

  /// An object policy that updates object_count.
  template<typename Tag, typename Base=empty_object_policy>
  struct count_objects
  {
    template<typename ... Args>
    static void onConstruct(Args && ... args)
    {
      ++object_count<Tag>::num;
      Base::onConstruct(std::forward<Args>(args)...);
    }

    template<typename ... Args>
    static void onCopy(Args && ... args)
    {
      ++object_count<Tag>::num;
      Base::onCopy(std::forward<Args>(args)...);
    }

    // Called before a handle is destroyed.
    template<typename ... Args>
    static void onDestroy(Args && ... args)
    {
      --object_count<Tag>::num;
      Base::onDestroy(std::forward<Args>(args)...);
    }
  };

  /**
   * @brief An object policy that performs simple reference counting and allows
   * a deleter to be specified.
   *
   * The LLVM memory model is simply a hierarchy of containers; e.g., a module
   * is a container of functions, a function is a container of basic blocks,
   * and a basic block is a container of instructions.  Handles (based on
   * llvmobj) complicate this picture somewhat.  What happens if a function is
   * deleted while a handle to one of its instructions around?  To avoid
   * dangling references, each handle holds a reference-counted pointer to the
   * LLVM object's parent.  Deletion only occurs when all references have
   * expired.
   */
  template<typename T, typename Deleter=std::default_delete<T>>
  struct custodian
  {
    // Called after a handle is constructed.
    template<typename Policy>
    static void onConstruct(llvmobj<T, Policy> & h, Deleter del=Deleter())
    {
      if(h.ptr())
      {
        auto sp = std::shared_ptr<T>();
        auto it = object_ledger().find(h.ptr());
        if(it == object_ledger().end() || !(sp = it->second.lock()))
        {
          sp = std::shared_ptr<T>(h.ptr(), WrappedDeleter(del));
          object_ledger()[h.ptr()] = sp;
        }
        handle_ledger()[&h] = sp;
      }
    }

    // Called after a handle is copied.
    template<typename Policy>
    static void onCopy(llvmobj<T, Policy> & copy, llvmobj<T, Policy> const & copied)
    {
      if(copied.ptr())
        handle_ledger()[&copy] = handle_ledger()[&copied];
    }

    // Called before a handle is destroyed.
    template<typename Policy>
    static void onDestroy(llvmobj<T, Policy> & h)
    {
      if(h.ptr())
        handle_ledger().erase(&h);
    }

  private:

    /// Wraps the provided deleter to clean up object_ledger.
    struct WrappedDeleter
    {
      WrappedDeleter(Deleter del) : del(del) {}
      Deleter del;
      void operator()(T * px) const
      {
        assert(px); // guarded in onConstruct.
        object_ledger().erase(px);
        del(px);
      }
    };

    /// The table of handles.
    static std::unordered_map<void const *, std::shared_ptr<T>> & handle_ledger()
    {
      static auto * L = new std::unordered_map<void const *, std::shared_ptr<T>>();
      return *L;
    }

    /// The table of T* objects managed by this custodian.
    static std::unordered_map<T const *, std::weak_ptr<T>> & object_ledger()
    {
      static auto * L = new std::unordered_map<T const *, std::weak_ptr<T>>();
      return *L;
    }
  };

  /// A deleter that does nothing.
  struct no_delete { template<typename T> void operator()(T *) const {} };

  // ptr() extracts an LLVM API pointer from any suitable object.
  template<typename T, typename Policy>
  T * ptr(llvmobj<T, Policy> const & tp)
    { return tp.ptr(); }

  template<typename T> T * ptr(T * t) { return t; }

  /// Streams the LLVM representation of an object.
  template<typename T, typename Policy>
  std::ostream & operator<<(std::ostream & os, llvmobj<T, Policy> const & obj)
  {
    if(obj.ptr())
    {
      auto && out = ::llvm::raw_os_ostream(os);
      out << *obj.ptr();
    }
    return os;
  }
}}

