#pragma once
#include "cyrt/bom.hpp"
#include "cyrt/fwd.hpp"
#include "cyrt/graph/infotable.hpp"
#include <deque>
#include <functional>
#include <map>
#include <memory>
#include <vector>

namespace cyrt
{
  // The bill of materials of a loaded module.  The loader decodes it from
  // the plain-data record of the module (cyrt/bom.hpp, ModuleBOM::decode).
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

    // The metadata objects of the types, constructors, and functions.  The
    // definitions below point into this deque, which keeps the address of
    // an element as it grows.  A metadata record the generated code shares
    // between symbols is decoded once.
    std::deque<Metadata> metadata_store;

    std::string fullname;
    std::string filename;
    Imports     imports;
    Metadata    metadata;
    Aliases     aliases;
    Types       types;
    Functions   functions;

    // Decodes the record of a generated module.  The caller checked the
    // version of the record (see SharedCurryModule).
    static std::unique_ptr<ModuleBOM> decode(bom::Module const &);
  };

  struct SharedCurryModuleInfo
  {
    std::string fullname;
    std::string sofilename;
    std::unique_ptr<ModuleBOM const> bom;
    void * dlhandle;

    SharedCurryModuleInfo(
        std::string fullname
      , std::string sofilename
      , std::unique_ptr<ModuleBOM const> bom
      , void * dlhandle
      )
      : fullname(fullname), sofilename(sofilename)
      , bom(std::move(bom)), dlhandle(dlhandle)
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

  // A loaded module.  The constructor opens the library, finds its record
  // _bom_ (cyrt/bom.hpp), refuses a record of another layout version, and
  // decodes it, unless a library of the same module name is loaded already:
  // then the module joins the registry entry of that library.
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
