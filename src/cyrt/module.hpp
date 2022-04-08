#pragma once
#include <map>
#include <memory>
#include "cyrt/fwd.hpp"
#include "cyrt/graph/infotable.hpp"
#include <string>
#include <vector>

namespace cyrt
{
  struct Module
  {
    Module(std::string);
    Module(Module const &) = delete;
    Module(Module &&) = delete;
    Module & operator=(Module const &) = delete;
    Module & operator=(Module &&) = delete;
    ~Module();

    static std::shared_ptr<Module> find_or_create(std::string);
    static std::map<std::string, std::shared_ptr<Module>> getall();

    InfoTable const * create_infotable(
        std::string const & name
      , index_type          arity
      , tag_type            tag
      , flag_type           flags
      );
    InfoTable const * get_infotable(std::string const &) const;

    Type const * create_type(
        std::string const & name
      , std::vector<InfoTable const *> constructors
      , flag_type flags = NO_FLAGS
      );
    Type const * get_type(std::string const & name) const;

    InfoTable const * get_builtin_symbol(std::string const &) const;
    Type const * get_builtin_type(std::string const &) const;

    struct Impl;
    std::string name;
    std::unique_ptr<Impl> impl;
  };
}
