#pragma once
#include "cyrt/fwd.hpp"
#include "cyrt/graph/infotable.hpp"
#include <map>
#include <memory>
#include <vector>

namespace cyrt
{
  struct ModuleBOM
  {
    using Imports            = std::vector<std::string>;
    using Aliases            = std::map<std::string, std::string>;
    using TypeDefinition     = std::tuple<
        Metadata const *, std::vector<Metadata const*>, DataType const *
      >;
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
    SharedLib(std::string const & sofilename);
    void * handle() const { return _handle.get(); }
    operator void *() const { return _handle.get(); }
    std::string const & sofilename() const { return _sofilename; }
  private:
    using Handle = std::shared_ptr<void>;
    Handle _handle;
    std::string _sofilename;
  };

  struct SharedCurryModule : SharedLib
  {
    SharedCurryModule(std::string const & sofilename);
    ModuleBOM const * bom = nullptr;
  };
}
