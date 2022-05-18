#pragma once
#include "cyrt/fwd.hpp"
#include "cyrt/graph/infotable.hpp"
#include <functional>
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

  struct SharedCurryModuleInfo
  {
    std::string fullname;
    std::string sofilename;
    ModuleBOM const * bom;
    void * dlhandle;

    SharedCurryModuleInfo(
        std::string fullname
      , std::string sofilename
      , ModuleBOM const * bom
      , void * dlhandle
      )
      : fullname(fullname), sofilename(sofilename)
      , bom(bom), dlhandle(dlhandle)
    {}
  };

  struct SharedLib
  {
    SharedLib(std::string const & sofilename);
    SharedLib(SharedLib const &)             = delete;
    SharedLib(SharedLib &&)                  = delete;
    SharedLib & operator=(SharedLib const &) = delete;
    SharedLib & operator=(SharedLib &&)      = delete;
    ~SharedLib();

    void * handle() const { return _handle; }
    operator void *() const { return _handle; }
    std::string const & sofilename() const { return _sofilename; }
  public:
    void * _handle;
    std::string _sofilename;
  };

  struct SharedCurryModule : SharedLib
  {
    SharedCurryModule(std::string const & sofilename);
    SharedCurryModuleInfo const * info() const;
    ModuleBOM const * bom() const;

    static SharedCurryModuleInfo const * find(char const * module_fullname);
    static InfoTable const * symbol(char const * module_fullname, char const * symbolname);
  private:
    std::shared_ptr<SharedCurryModuleInfo const> _info;
  };
}
