/**
 * @file
 * @brief Contains exception code.
 */

#pragma once
#include <string>
#include <exception>
#include "boost/format.hpp"
#include "llvm/ADT/Twine.h"

namespace sprite { namespace llvm
{
  /// Base class for all error types defined in this module.
  struct exception : std::exception
  {
    /// Creates a error instance with optional message.
    exception(std::string const & type, std::string const & msg = "")
      : _msg()
    {
      if(msg.empty())
        _msg = type;
      else
        _msg = type + ": " + msg;

      // if(_msg.back() != '.') _msg.push_back('.');
    }

    /// Inherited what method.
    virtual char const * what() const throw() override
      { return _msg.c_str(); }

  private:

    /// Holds the error message.
    std::string _msg;
  };

  /// Declares a new exception type.
  #define SPRITE_DECLARE_ERROR_TYPE(name)                                     \
      struct name : exception                                                 \
      {                                                                       \
        name(::llvm::Twine const & msg = "") : exception(#name, msg.str()) {} \
        name(::boost::format const & fmt) : name(fmt.str()) {}                \
      };                                                                      \
    /**/

  SPRITE_DECLARE_ERROR_TYPE(internal_error)
  SPRITE_DECLARE_ERROR_TYPE(key_error)
  SPRITE_DECLARE_ERROR_TYPE(scope_error)
  SPRITE_DECLARE_ERROR_TYPE(type_error)
  SPRITE_DECLARE_ERROR_TYPE(value_error)
  SPRITE_DECLARE_ERROR_TYPE(index_error)
}}
