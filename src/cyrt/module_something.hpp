#pragma once
#include "cyrt/graph/infotable.hpp"
#include <map>
#include <string>
#include <variant>
#include <vector>

namespace cyrt
{
  enum Visibility { PUBLIC, PRIVATE };
  using ImportList  = std::vector<std::string>;
  using MDValue     = std::variant<std::string, int>;
  using Metadata    = std::map<std::string, MDValue>;
  using Aliases     = std::map<std::string, std::string>;
  using Typedef     = std::tuple<Metadata const *, std::vector<Metadata const*>, Type const *>;
  using TypedefList = std::vector<Typedef>;
  using Funcdef     = std::tuple<Visibility, Metadata const *, InfoTable const *>;
  using FuncdefList = std::vector<Funcdef>;

  struct ModuleSomething // FIXME: the name
  {
    ModuleSomething(
        std::string    fullname
      , std::string    filename
      , ImportList &&  imports
      , Metadata &&    metadata
      , Aliases &&     aliases
      , TypedefList && types
      , FuncdefList && functions
      );
  };
}
