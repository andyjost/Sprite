#pragma once
#include <memory>
#include "sprite/fwd.hpp"
#include <string>
#include <unordered_map>
#include <vector>

namespace sprite
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
      );
    Type const * get_type(std::string const & name) const;

    struct Impl;
    std::string name;
    std::unique_ptr<Impl> impl;
  };
}
