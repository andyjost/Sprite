#pragma once
#include <map>
#include <memory>
#include "curryrt/fwd.hpp"
#include "curryrt/dynload.hpp"
#include "curryrt/graph/infotable.hpp"
#include <string>
#include <memory>
#include <vector>

namespace curryrt
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

    // Links a compiled object to the module and registers the tables of
    // its record.  A second object of the module (the compile on first use
    // of a module whose object was loaded before) takes the place of the
    // first, which stays mapped for the life of the process: the tables may
    // hold the steps of either.
    void link(std::shared_ptr<SharedCurryModule> const &);
    void clear();
    // Copies the tables the runtime registered under the name of this
    // module (register_builtin_module) into the module.  The constructor
    // and clear call it.
    void seed_builtins();

    // Tiered execution (curryrt/tiered.hpp).  Links the compiled object of a
    // module whose functions the interpreter runs, and gives every function
    // in ``steps`` (the symbol of its step function in the object, and the
    // table the interpreter made) the compiled step.  A table whose step is
    // not the interpreter, and a symbol the object lacks, are skipped.
    // Returns the number of functions that run compiled.  The load of the
    // object bound its slots to the tables of this module (the binding in
    // curryrt/dynload.hpp), so the compiled code names the tables the
    // interpreter made.
    size_t adopt(
        std::shared_ptr<SharedCurryModule> const &
      , std::vector<std::pair<std::string, InfoTable const *>> const & steps
      );
    // The binding of a compiled object of this module (the binding in
    // curryrt/dynload.hpp): the table the slot of a symbol the object
    // defines takes, given the table of the object.  The table of this
    // module when it has one of the name (made at run time by the
    // materializer, or registered from a library loaded before), which
    // takes the step of the object when it has no compiled code (the swap
    // of tiered execution); else a kept table of the same shape (see
    // clear), taken back with the step and the flags of the table of the
    // object, so that a Python object of an earlier incarnation of the
    // module holds the table of the symbol still; else the table of the
    // object.  bind_type takes a kept type back with all its constructors
    // or not at all, so a type and its constructors agree.  A module that
    // took a kept table back keeps its tables for the life of the process,
    // as the module that kept them did.  The object must be linked to the
    // module after the binding (adopt, or link), so that it stays mapped
    // while the tables hold its steps.
    InfoTable const * bind_infotable(InfoTable const * object);
    DataType const * bind_type(DataType const * object);
    // The compiled object linked to this module, or null.
    std::shared_ptr<SharedCurryModule> shlib() const;
    // Keeps the tables made at run time for the life of the process (see
    // clear).  The materializer calls this for a module it interprets.
    void keep_tables();
    // Hands the tables made at run time to the kept store and clears the
    // module, as the destructor of an interpreted module does.  A reset of
    // the interpreter calls this when a module leaves it while a Python
    // object of the module is still alive (issue #114): the registry gives
    // this object back to a module of the same name made later, which then
    // takes the tables back through create_infotable, without a step, and
    // runs its own code; before, it found the tables with the steps of the
    // old module.  The tables are kept whatever the state of the module:
    // the Python objects of the old module name them.
    void retire();

    static void register_builtin_module(
        std::string const & name, TypeTable && types, SymbolTable && symbols
      );

    static std::shared_ptr<Module> find_or_create(std::string);
    // The loaded module of that name, or null.
    static std::shared_ptr<Module> find(std::string const &);
    // The info table ``name`` of the loaded module ``modulename``, or null.
    // The runtime looks a symbol of the Prelude up this way, so that it
    // finds the table whether the Prelude came from its compiled library
    // or was interpreted from its ICurry (curryrt/icurry.hpp).
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

    // The table of a symbol or type the runtime registered as a built-in of
    // this module (register_builtin_module), or null.  A static table of a
    // compiled object is not a built-in: the compiler of curry.save writes
    // the step function of such a symbol again (issue #113).
    InfoTable const * get_builtin_symbol(std::string const &) const;
    DataType const * get_builtin_type(std::string const &) const;
    // The same, for a module of which no Module object is loaded: the
    // binding of a compiled object resolves a built-in this way (the
    // Prelude at the start of a process names its own built-ins).
    static InfoTable const * builtin_symbol(
        std::string const & modulename, std::string const & name
      );
    static DataType const * builtin_type(
        std::string const & modulename, std::string const & name
      );

    struct Impl;
    std::string name;
    std::unique_ptr<Impl> impl;
  };

  // The trap step.  A function table made at run time gets no code when the
  // interpreter flag ``interpret`` is 'off' (backends/cxx/materialize.py):
  // its module was imported from an ICurry object, which the plan of the
  // toolchain never compiles (issue #102).  The materializer gives such a
  // table this step instead of a null pointer.  When the step runs, it
  // calls the hook, which may give the table its code (the Python side
  // compiles the module and swaps the steps; see tiered_adopt in
  // tiered.hpp), and then runs the step the table has.  A table that still
  // has no code sets the error of the configuration, which names the
  // function and its module and the reason the hook gave, and returns
  // E_ERROR: the evaluation raises instead of calling a null pointer.
  //
  // The hook returns the empty string when it gave the table its code, or
  // the reason it did not.  It runs on the thread that evaluates, inside the
  // step.  The bindings install one that calls into Python; without a hook
  // the trap reports that.
  using trap_hook_type = std::string (*)(InfoTable const *);
  void set_trap_hook(trap_hook_type);
  tag_type trap_step(RuntimeState *, Configuration *);
  // Gives ``info`` the trap step.  ``info`` must be a function table made at
  // run time without a step, or with the trap already (then nothing
  // changes).  Throws std::invalid_argument otherwise.
  void install_trap(InfoTable *);
  inline bool is_trapped(InfoTable const * info)
    { return info && info->step == &trap_step; }
  // The name of the loaded module that owns a table, or the empty string.  A
  // scan of the loaded modules, for messages.
  std::string owner_of(InfoTable const *);
}
