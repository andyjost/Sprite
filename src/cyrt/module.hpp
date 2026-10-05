#pragma once
#include <map>
#include <memory>
#include "cyrt/fwd.hpp"
#include "cyrt/dynload.hpp"
#include "cyrt/graph/infotable.hpp"
#include <string>
#include <memory>
#include <vector>

namespace cyrt
{
  using TypeTable = std::unordered_map<std::string, DataType const *>;
  using SymbolTable = std::unordered_map<std::string, InfoTable const *>;

  struct Module
  {
    Module(std::string);
    Module(Module const &) = delete;
    Module(Module &&) = delete;
    Module & operator=(Module const &) = delete;
    Module & operator=(Module &&) = delete;
    ~Module();

    void link(std::shared_ptr<SharedCurryModule> const &);
    void clear();

    // Tiered execution (cyrt/tiered.hpp).  Links the compiled object of a
    // module whose functions the interpreter runs, and gives every function
    // in ``steps`` (the symbol of its step function in the object, and the
    // table the interpreter made) the compiled step.  A table whose step is
    // not the interpreter, and a symbol the object lacks, are skipped.
    // Returns the number of functions that run compiled.  The shim of the
    // module must be loaded first, so that the object binds its table
    // references to the tables of this registry.
    size_t adopt(
        std::shared_ptr<SharedCurryModule> const &
      , std::vector<std::pair<std::string, InfoTable const *>> const & steps
      );
    // The compiled object linked to this module, or null.
    std::shared_ptr<SharedCurryModule> shlib() const;
    // Keeps the tables made at run time for the life of the process (see
    // clear).  The materializer calls this for a module it interprets.
    void keep_tables();

    static void register_builtin_module(
        std::string const & name, TypeTable && types, SymbolTable && symbols
      );

    static std::shared_ptr<Module> find_or_create(std::string);
    // The loaded module of that name, or null.
    static std::shared_ptr<Module> find(std::string const &);
    // The info table ``name`` of the loaded module ``modulename``, or null.
    // The runtime looks a symbol of the Prelude up this way, so that it
    // finds the table whether the Prelude came from its compiled library
    // or was interpreted from its ICurry (cyrt/icurry.hpp).
    static InfoTable const * find_symbol(
        std::string const & modulename, std::string const & name
      );
    static std::map<std::string, std::shared_ptr<Module>> getall();

    InfoTable const * create_infotable(
        std::string const & name
      , index_type          arity
      , tag_type            tag
      , flag_type           flags
      );
    InfoTable const * get_infotable(std::string const &) const;

    DataType const * create_type(
        std::string const & name
      , std::vector<InfoTable const *> constructors
      , flag_type flags = NO_FLAGS
      );
    DataType const * get_type(std::string const & name) const;

    InfoTable const * get_builtin_symbol(std::string const &) const;
    DataType const * get_builtin_type(std::string const &) const;

    struct Impl;
    std::string name;
    std::unique_ptr<Impl> impl;
  };
}
