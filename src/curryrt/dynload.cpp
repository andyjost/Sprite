#include <cassert>
#include "curryrt/dynload.hpp"
#include "curryrt/exceptions.hpp"
#include "curryrt/module.hpp"
#include "curryrt/platform.hpp"
#include <iostream>
#include <sstream>
#include <unordered_map>

namespace
{
  using namespace curryrt;

  // The runtime library itself, opened once more with RTLD_GLOBAL at its
  // load.  The name is the one the toolchain links against (libcurryrt.so,
  // or .dylib on macOS); the file is the one this code was loaded from,
  // found through dladdr, so the dynamic linker opens the mapped copy by
  // its path and no search by name is needed on either platform.
  #if defined(__APPLE__)
  static char const * const CURRYRT_LIBRARY = "libcurryrt.dylib";
  #elif defined(_WIN32)
  static char const * const CURRYRT_LIBRARY = "libcurryrt.dll";
  #else
  static char const * const CURRYRT_LIBRARY = "libcurryrt.so";
  #endif
  static std::string curryrt_library_path()
  {
    std::string const path = platform::path_of_object_holding((void const *) &curryrt_library_path);
    return path.empty() ? std::string(CURRYRT_LIBRARY) : path;
  }
  static SharedLib const libcurryrt(CURRYRT_LIBRARY, curryrt_library_path());
  std::unordered_map<std::string, std::weak_ptr<SharedCurryModuleInfo const>> registry;

  // The decoder of one module record.  It memoizes the metadata by the
  // address of the record, so a record shared between symbols gives one
  // Metadata object.
  struct Decoder
  {
    ModuleBOM & out;
    std::unordered_map<bom::Metadata const *, Metadata const *> seen;

    static std::string text(char const * s)
    {
      return s ? std::string(s) : std::string();
    }

    static MDValue value(bom::Entry const & entry)
    {
      switch(entry.kind)
      {
        case bom::STRING:
          return MDValue(std::in_place_type<std::string>, text(entry.text));
        case bom::INTEGER:
          return MDValue(std::in_place_type<int>, entry.number);
        case bom::BOOLEAN:
          return MDValue(std::in_place_type<bool>, entry.number != 0);
      }
      std::stringstream ss;
      ss << "bad kind " << int(entry.kind) << " of metadata entry "
         << text(entry.key);
      throw DynloadError(ss.str());
    }

    static void fill(Metadata & md, bom::Metadata const * table)
    {
      if(!table)
        return;
      for(unsigned i=0; i<table->size; ++i)
      {
        bom::Entry const & entry = table->entries[i];
        md.emplace(text(entry.key), value(entry));
      }
    }

    Metadata const * metadata(bom::Metadata const * table)
    {
      auto found = this->seen.find(table);
      if(found != this->seen.end())
        return found->second;
      Metadata & md = this->out.metadata_store.emplace_back();
      fill(md, table);
      this->seen[table] = &md;
      return &md;
    }

    void run(bom::Module const & record)
    {
      this->out.fullname = text(record.fullname);
      this->out.filename = text(record.filename);
      for(unsigned i=0; i<record.n_imports; ++i)
        this->out.imports.push_back(text(record.imports[i]));
      fill(this->out.metadata, record.metadata);
      for(unsigned i=0; i<record.n_aliases; ++i)
        this->out.aliases.emplace(
            text(record.aliases[i].name), text(record.aliases[i].target)
          );
      // The bound tables (see the binding in dynload.hpp): the slots were
      // filled before the record is decoded.
      for(unsigned i=0; i<record.n_types; ++i)
      {
        bom::Type const & type = record.types[i];
        std::vector<Metadata const *> ctors;
        if(type.type)
          for(index_type j=0; j<type.type->size; ++j)
            ctors.push_back(this->metadata(type.constructors[j]));
        this->out.types.emplace_back(
            this->metadata(type.metadata), std::move(ctors), *type.slot
          );
      }
      for(unsigned i=0; i<record.n_functions; ++i)
      {
        bom::Function const & function = record.functions[i];
        this->out.functions.emplace_back(
            bool(function.visibility), this->metadata(function.metadata)
          , *function.slot
          );
      }
    }
  };

  // The binder of one module record; see the binding in dynload.hpp.  The
  // tables of the symbols the module defines come from the module of its
  // name in the registry (Module::bind_infotable, Module::bind_type), when
  // one is loaded: the Python side makes it before it loads an object over
  // the tables the interpreter made (loader.py and tiered.py); the load of
  // a module nobody interprets, the Prelude at the start of a process, say,
  // finds none and takes the tables of the object.  The tables of the
  // other symbols come from the modules that define them, or from the
  // built-ins of the runtime.
  struct Binder
  {
    std::string const & sofilename;
    bom::Module const & record;
    std::shared_ptr<Module> owner;

    Binder(std::string const & sofilename, bom::Module const & record)
      : sofilename(sofilename), record(record)
      , owner(Module::find(record.fullname))
    {}

    [[noreturn]] void unresolved(
        char const * what, char const * module, char const * name
      )
    {
      std::stringstream ss;
      ss << "cannot load " << sofilename << ": the " << what << " "
         << (name ? name : "") << " of module " << (module ? module : "")
         << " is not loaded";
      throw DynloadError(ss.str());
    }

    void run()
    {
      for(unsigned i=0; i<record.n_types; ++i)
      {
        bom::Type const & type = record.types[i];
        DataType const * bound = owner ? owner->bind_type(type.type)
                                       : type.type;
        *type.slot = bound;
        for(index_type j=0; j<type.type->size; ++j)
        {
          assert(std::string(bound->ctors[j]->name) == type.type->ctors[j]->name);
          *type.ctor_slots[j] = bound->ctors[j];
        }
      }
      for(unsigned i=0; i<record.n_functions; ++i)
      {
        bom::Function const & function = record.functions[i];
        *function.slot = owner ? owner->bind_infotable(function.info)
                               : function.info;
      }
      for(unsigned i=0; i<record.n_info_slots; ++i)
      {
        bom::InfoSlot const & slot = record.info_slots[i];
        InfoTable const * info = nullptr;
        if(auto module = Module::find(slot.module))
          info = module->get_infotable(slot.name);
        if(!info)
          info = Module::builtin_symbol(slot.module, slot.name);
        if(!info)
          this->unresolved("symbol", slot.module, slot.name);
        *slot.slot = info;
      }
      for(unsigned i=0; i<record.n_type_slots; ++i)
      {
        bom::TypeSlot const & slot = record.type_slots[i];
        DataType const * type = nullptr;
        if(auto module = Module::find(slot.module))
          type = module->get_type(slot.name);
        if(!type)
          type = Module::builtin_type(slot.module, slot.name);
        if(!type)
          this->unresolved("type", slot.module, slot.name);
        *slot.slot = type;
      }
    }
  };
}

namespace curryrt
{
  std::unique_ptr<ModuleBOM> ModuleBOM::decode(bom::Module const & record)
  {
    auto out = std::make_unique<ModuleBOM>();
    Decoder decoder{*out, {}};
    decoder.run(record);
    return out;
  }

  SharedLib::SharedLib(std::string const & sofilename)
    : SharedLib(sofilename, sofilename)
  {}

  SharedLib::SharedLib(
      std::string const & sofilename, std::string const & loadpath
    )
    : _handle(nullptr), _sofilename(sofilename)
  {
    std::string error;
    this->_handle = platform::load(loadpath, &error);
    if(!this->_handle)
      throw DynloadError(error);
  }

  SharedLib::~SharedLib()
  {
    std::string error;
    if(!platform::unload(this->_handle, &error))
      std::cerr << error << std::endl;
  }

  SharedCurryModule::SharedCurryModule(std::string const & sofilename)
    : SharedLib(sofilename), _info()
  {
    this->init(false);
  }

  SharedCurryModule::SharedCurryModule(
      std::string const & sofilename, std::string const & loadpath
    )
    : SharedLib(sofilename, loadpath), _info()
  {
    this->init(true);
  }

  // Reads the record of the module, binds its slots, runs its initializer
  // and registers the library.  With ``fresh`` the library never joins the
  // entry of its name.  A library that joins an entry was bound at its own
  // load (dlopen of a mapped file gives the mapped library), and its slots
  // are bound again all the same, against the registry of the moment: a
  // table of the module that an incarnation interpreted since then takes
  // the step of the object back, so the load of an object is the swap
  // whether or not a library of the name is mapped.  The initializer runs
  // once: the nodes of the literals exist.
  void SharedCurryModule::init(bool fresh)
  {
    std::string const & sofilename = this->sofilename();
    auto addr = platform::symbol(this->handle(), "_bom_");
    if(!addr)
      throw DynloadError("no symbol _bom_ in " + sofilename);
    bom::Module const * record = (bom::Module const *) addr;
    if(record->version != bom::VERSION)
    {
      std::stringstream ss;
      ss << "cannot load " << sofilename << ": its bill of materials has "
         << "layout version " << record->version << ", and this runtime "
         << "reads version " << bom::VERSION << ".  Compile the module again.";
      throw DynloadError(ss.str());
    }
    if(!record->fullname)
      throw DynloadError(
          "cannot load " + sofilename + ": the module has no name"
        );

    auto pinfo = registry.find(record->fullname);
    if(pinfo != registry.end() && !fresh)
      this->_info = pinfo->second.lock();
    Binder binder(sofilename, *record);
    binder.run();
    if(!this->_info)
    {
      // The initializer makes the nodes of the literals of the module from
      // the bound tables (see backends/cxx/compiler.py).  A library without
      // one (a record written by hand) makes no nodes.
      if(auto init = platform::symbol(this->handle(), "_sprite_init_"))
        ((void (*)()) init)();
      this->_info = std::make_shared<SharedCurryModuleInfo>(
          record->fullname, sofilename, ModuleBOM::decode(*record)
        , this->handle()
        );
      if(pinfo == registry.end())
      {
        auto rv = registry.emplace(record->fullname, this->_info);
        (void) rv;
        assert(rv.second);
      }
      else
        pinfo->second = this->_info;
    }
    assert(this->_info);
  }

  SharedCurryModuleInfo const * SharedCurryModule::info() const
  {
    return this->_info.get();
  }

  ModuleBOM const * SharedCurryModule::bom() const
  {
    return this->_info->bom.get();
  }

  SharedCurryModuleInfo const * SharedCurryModule::find(char const * module_fullname)
  {
    auto pinfo = registry.find(module_fullname);
    if(pinfo != registry.end())
      if(auto ptr = pinfo->second.lock())
        return ptr.get();
    return nullptr;
  }

  InfoTable const * SharedCurryModule::symbol(
      char const * module_fullname, char const * symbolname
    )
  {
    auto * info = SharedCurryModule::find(module_fullname);
    if(info)
      return (InfoTable const *) platform::symbol(info->dlhandle, symbolname);
    else
      return nullptr;
  }
}
