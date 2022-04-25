#pragma once
#include "cyrt/fwd.hpp"
#include "cyrt/graph/infotable.hpp"
#include <map>
#include <vector>
#include <memory>
#include <dlfcn.h>

namespace cyrt
{
  struct ModuleBOM
  {
    using Imports            = std::vector<std::string>;
    using Aliases            = std::map<std::string, std::string>;
    using TypeDefinition     = std::tuple<Metadata const *, std::vector<Metadata const*>, Type const *>;
    using Types              = std::vector<TypeDefinition>;
    using FunctionDefinition = std::tuple<bool, Metadata const *, InfoTable const *>;
    using Functions          = std::vector<FunctionDefinition>;

    std::string fullname;
    std::string filename;
    Imports     imports;
    Metadata    metadata;
    Aliases     aliases;
    Types       types;
    Functions   functions;
  };

  struct SharedLib
  {
    SharedLib(std::string const & sofile);
    void * handle() const { return _handle.get(); }
    operator void *() const { return _handle.get(); }
  private:
    using Handle = std::shared_ptr<void>;
    Handle _handle;
  public:
    std::string const name;
  };

  struct SharedCurryModule : SharedLib
  {
    SharedCurryModule(std::string const & sofile);
    ModuleBOM const * bom = nullptr;
  };
}
