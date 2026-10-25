#pragma once
#include "curryrt/bom.hpp"
#include "curryrt/fwd.hpp"
#include "curryrt/graph/infotable.hpp"
#include <deque>
#include <functional>
#include <map>
#include <memory>
#include <vector>

namespace curryrt
{
  // The bill of materials of a loaded module.  The loader decodes it from
  // the plain-data record of the module (curryrt/bom.hpp, ModuleBOM::decode).
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
    // Opens the file ``loadpath`` and records ``sofilename`` as the name of
    // the library.  Tiered execution loads a file written over the path of
    // an object this process maps through a link of its own (see
    // curryrt/tiered.hpp), and the library keeps the name the toolchain knows.
    SharedLib(std::string const & sofilename, std::string const & loadpath);
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
  // _bom_ (curryrt/bom.hpp), refuses a record of another layout version,
  // binds the slots of the module, runs its initializer, and decodes the
  // record, unless a library of the same module name is loaded already:
  // then the module joins the registry entry of that library, whose slots
  // were bound at its load.  The constructor with a load path (see
  // SharedLib) never joins: its library gets an entry of its own, which
  // takes the place of the entry of the name, so that the registry names
  // the newest library of a module.
  //
  // The binding.  The code of a generated module reads every info table and
  // data type it names through a slot of the module (the slots in
  // curryrt/bom.hpp).  The load fills the slots, before any code of the
  // module runs.  A symbol the module defines takes the table of the
  // module of its name in the registry of the runtime (Module::bind_infotable
  // and Module::bind_type in curryrt/module.hpp): the table the interpreter
  // made when the module runs interpreted, or a table kept from an earlier
  // incarnation of the module, so that the nodes, the bytecode of other
  // modules and the Python objects that hold a table keep holding the one
  // table of the symbol, else the table of the object.  A symbol of another
  // module, or a built-in of the runtime, takes the table of that name in
  // the module that defines it, which the loader of the Python side imports
  // before it opens the object, or the built-in table of the runtime; a
  // symbol that neither has is an error of the load, DynloadError, which
  // names the symbol and its module.  Then the initializer of the module,
  // _sprite_init_, makes the nodes of its literals from the bound tables,
  // and the record is decoded with the bound tables, so that Module::link
  // registers them.  The bytecode of an interpreted function names the
  // same tables, so the swap of tiered execution (curryrt/tiered.hpp) is
  // the load of the object followed by Module::adopt, which writes the
  // compiled steps into the tables the interpreter made.
  struct SharedCurryModule : SharedLib
  {
    SharedCurryModule(std::string const & sofilename);
    SharedCurryModule(
        std::string const & sofilename, std::string const & loadpath
      );
    SharedCurryModuleInfo const * info() const;
    ModuleBOM const * bom() const;

    static SharedCurryModuleInfo const * find(char const * module_fullname);
    static InfoTable const * symbol(char const * module_fullname, char const * symbolname);
  private:
    void init(bool fresh);
    std::shared_ptr<SharedCurryModuleInfo const> _info;
  };
}
