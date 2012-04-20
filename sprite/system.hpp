/**
 * @file
 * @brief Defines the system interface.
 */

#pragma once
#include "sprite/common.hpp"

namespace sprite
{
  /// The type of an H function.
  typedef tr1::function<void(Node &)> h_func_type;

  /// Interface to the module loader.
  struct Loader
  {
    /// Inserts a constructor into the associated program.
    virtual size_t insert_ctor(std::string const & name) = 0;

    /// Inserts an operation into the associated program.
    virtual size_t insert_oper(std::string const & name, h_func_type) = 0;

    virtual ~Loader() {}
  };

  /// Interface to a module.
  struct Module
  {
    /// Returns the ID of the named constructor in the associated program.
    virtual size_t find_ctor(std::string const & label) = 0;

    /// Returns the ID of the named operation in the associated program.
    virtual size_t find_oper(std::string const & label) = 0;

    virtual ~Module() {}
  };

}

