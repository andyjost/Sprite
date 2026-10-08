#include <algorithm>
#include <cstring>
#include "cyrt/builtins.hpp"
#include "cyrt/currylib/prelude.hpp"
#include "cyrt/currylib/setfunctions.hpp"
#include "cyrt/graph/infotable.hpp"
#include "cyrt/icurry.hpp"
#include "cyrt/module.hpp"
#include "cyrt/state/configuration.hpp"
#include <dlfcn.h>
#include <iostream>
#include <stdexcept>
#include <unordered_map>

using namespace cyrt;

namespace
{
  struct BuiltinModuleData
  {
    TypeTable   types;
    SymbolTable symbols;
  };

  std::unordered_map<std::string, std::weak_ptr<Module>> g_modules;
  std::unordered_map<std::string, BuiltinModuleData> g_builtin_modules;

  // The tables and types kept when a module with interpreted functions was
  // cleared (Module::clear), by module name and symbol name.  A module of the
  // same name made later takes them back (Module::create_infotable,
  // Module::create_type), so a symbol keeps its address across a reload of
  // the interpreter: the shim of tiered execution names the tables by
  // address (cyrt/tiered.hpp).
  std::unordered_map<std::string, SymbolTable> g_kept_symbols;
  std::unordered_map<std::string, TypeTable> g_kept_types;
  // The compiled objects of the modules whose tables were kept: the kept
  // tables hold their steps and their names, so an object bound over a shim
  // stays loaded for the life of the process.
  std::vector<std::shared_ptr<SharedCurryModule>> g_kept_libraries;
}

namespace cyrt
{
  struct Module::Impl
  {
    SymbolTable symbols;
    TypeTable types;
    std::shared_ptr<SharedCurryModule> shlib;
    bool keep = false;
    // The tables and types made at run time by this module, which clear
    // frees or keeps.  The flags do not tell them apart from the static
    // tables of an object: the load of an object over a shim writes the
    // flags of its static tables into these (see adopt).
    std::vector<InfoTable *> owned_tables;
    std::vector<DataType *> owned_types;
  };

  void Module::register_builtin_module(
      std::string const & name, TypeTable && types, SymbolTable && symbols
    )
  {
    assert(g_builtin_modules.count(name) == 0);
    BuiltinModuleData data{std::move(types), std::move(symbols)};
    auto rv = g_builtin_modules.try_emplace(name, std::move(data));
    (void) rv;
    assert(rv.second);
  }

  std::shared_ptr<Module> Module::find_or_create(std::string name)
  {
    auto & slot = g_modules[name];
    if(auto handle = slot.lock())
      return handle;
    auto handle = std::make_shared<Module>(name);
    slot = handle;
    return handle;
  }

  std::shared_ptr<Module> Module::find(std::string const & name)
  {
    auto p = g_modules.find(name);
    if(p == g_modules.end())
      return nullptr;
    return p->second.lock();
  }

  InfoTable const * Module::find_symbol(
      std::string const & modulename, std::string const & name
    )
  {
    auto module = Module::find(modulename);
    return module ? module->get_infotable(name) : nullptr;
  }

  std::map<std::string, std::shared_ptr<Module>> Module::getall()
  {
    std::map<std::string, std::shared_ptr<Module>> out;
    for(auto && item: g_modules)
    {
      if(auto p = item.second.lock())
        out[item.first] = p;
    }
    return out;
  }

  Module::Module(std::string name)
    : name(name), impl(new Impl)
  {
    auto bi = g_builtin_modules.find(name);
    if(bi != g_builtin_modules.end())
    {
      this->impl->types = bi->second.types;
      this->impl->symbols = bi->second.symbols;
    }
  }

  Module::~Module()
  {
    this->clear();
  }

  void Module::link(std::shared_ptr<SharedCurryModule> const & shlib)
  {
    if(shlib)
    {
      if(this->impl->shlib)
      {
        assert(this->impl->shlib->bom() == shlib->bom());
        return;
      }
      this->impl->shlib = shlib;
      for(auto && typedef_: shlib->info()->bom->types)
      {
        DataType const * ty = std::get<2>(typedef_);
        this->impl->types[ty->name] = ty;
        for(size_t i=0; i<ty->size; ++i)
        {
          InfoTable const * info = ty->ctors[i];
          this->impl->symbols[info->name] = info;
        }
      }
      for(auto && funcdef: shlib->info()->bom->functions)
      {
        InfoTable const * info = std::get<2>(funcdef);
        // The table is keyed by the name of the info table, which is the
        // Curry name of the function; a primitive behind an external must
        // carry its Curry name as well, or it shadows the function that
        // wraps it (prim_error against error).
        auto found = this->impl->symbols.find(info->name);
        assert(found == this->impl->symbols.end() || found->second == info);
        this->impl->symbols[info->name] = info;
      }
    }
  }

  // The tables made at run time are freed with the module, unless one of
  // its functions is interpreted (cyrt/icurry.hpp) or the materializer asked
  // to keep them (keep_tables).  The bytecode of an interpreted function
  // names the tables and types of the modules it uses by pointer, and so
  // does a compiled object loaded over a shim (cyrt/tiered.hpp), so a module
  // whose functions another module interprets must outlive that module.
  // Such tables are kept for the life of the process, as the static tables
  // of a compiled module are kept with its library, and a module of the same
  // name made later takes them back.  A kept table keeps its step: a swapped
  // table points into the object of the module, which is kept with it.  A
  // module without tables made at run time (one loaded from its object) has
  // nothing to keep, and its object goes with it.
  void Module::clear()
  {
    bool keep = this->impl->keep && !this->impl->owned_tables.empty();
    for(InfoTable * info: this->impl->owned_tables)
      if(info->aux)
        keep = true;
    if(keep)
    {
      auto & kept_symbols = g_kept_symbols[this->name];
      auto & kept_types = g_kept_types[this->name];
      for(InfoTable * info: this->impl->owned_tables)
        kept_symbols[info->name] = info;
      for(DataType * type: this->impl->owned_types)
        kept_types[type->name] = type;
      if(this->impl->shlib)
        g_kept_libraries.push_back(this->impl->shlib);
    }
    else
    {
      for(InfoTable * info: this->impl->owned_tables)
        delete[] (char *) info;
      for(DataType * type: this->impl->owned_types)
        delete[] (char *) type;
    }
    this->impl->owned_tables.clear();
    this->impl->owned_types.clear();
    this->impl->symbols.clear();
    this->impl->types.clear();
    this->impl->shlib.reset();
  }

  void Module::keep_tables()
  {
    this->impl->keep = true;
  }

  std::shared_ptr<SharedCurryModule> Module::shlib() const
  {
    return this->impl->shlib;
  }

  // The load of the object did most of the work already: the dynamic
  // initializer of a static table of the object constructs it at the address
  // the symbol resolves to, which the shim made the table the interpreter
  // uses.  So the table holds the step, the name, the format, and the flags
  // of the compiled module when dlopen returns, and its aux field is null;
  // the static table inside the object stays blank.  A table whose step is
  // still the interpreter (a symbol the shim does not name) takes the step
  // function of the object by its own symbol, and its aux field is cleared
  // as well, so a swapped table looks the same on both paths.  The bytecode
  // stays allocated (cyrt/icurry.cpp): a step in flight finishes on it.  A
  // table with the trap step (no code; see trap_step) is swapped the same
  // way: the compile on first use under interpret:off ends here.
  size_t Module::adopt(
      std::shared_ptr<SharedCurryModule> const & shlib
    , std::vector<std::pair<std::string, InfoTable const *>> const & steps
    )
  {
    assert(shlib);
    size_t swapped = 0;
    for(auto const & step: steps)
    {
      InfoTable * info = const_cast<InfoTable *>(step.second);
      if(!info)
        continue;
      if(info->step == &icurry_step || info->step == &trap_step)
      {
        auto compiled = (stepfunc_type) dlsym(
            shlib->handle(), step.first.c_str()
          );
        if(!compiled)
          continue;
        info->step = compiled;
        info->aux = nullptr;
      }
      if(info->step && info->step != &icurry_step
          && info->step != &trap_step)
        ++swapped;
    }
    // The initializers wrote the flags of the static tables, the static
    // object flag included.  These stay tables made at run time: clear
    // frees or keeps them, and the materializer must not take them for
    // built-ins.
    for(InfoTable * info: this->impl->owned_tables)
      info->flags &= ~F_STATIC_OBJECT;
    for(DataType * type: this->impl->owned_types)
      type->flags &= ~F_STATIC_OBJECT;
    this->link(shlib);
    return swapped;
  }

  InfoTable const * Module::get_infotable(std::string const & name) const
  {
    auto p = this->impl->symbols.find(name);
    return (p != this->impl->symbols.end()) ? p->second : nullptr;
  }

  InfoTable const * Module::create_infotable(
      std::string const & name
    , index_type          arity
    , tag_type            tag
    , flag_type           flags
    )
  {
    assert(!this->get_infotable(name));
    // A kept table of the same shape is taken back (see clear).
    auto kept_module = g_kept_symbols.find(this->name);
    if(kept_module != g_kept_symbols.end())
    {
      auto kept = kept_module->second.find(name);
      if(kept != kept_module->second.end())
      {
        InfoTable * info = const_cast<InfoTable *>(kept->second);
        if(info->tag == tag && info->arity == arity)
        {
          kept_module->second.erase(kept);
          info->flags = flags;
          info->step  = nullptr;
          info->type  = nullptr;
          info->aux   = nullptr;
          this->impl->symbols[name] = info;
          this->impl->owned_tables.push_back(info);
          return info;
        }
      }
    }
    size_t const bytes = sizeof(InfoTable) + name.size() + arity + 2;
    std::unique_ptr<char[]> mem(new char[bytes]);
    InfoTable * info = (InfoTable *) mem.get();
    char * info_name = (char *) (mem.get() + sizeof(InfoTable));
    char * format = info_name + name.size() + 1;
    info->tag        = tag;
    info->arity      = arity;
    info->alloc_size = sizeof(void *) * std::max(arity + 1, 2);
    info->flags      = flags;
    info->name       = info_name;
    info->format     = format;
    info->step       = nullptr;
    info->type       = nullptr;
    info->aux        = nullptr;
    std::strcpy(info_name, name.c_str());
    index_type i=0;
    for(; i<arity; ++i)
      format[i] = 'p';
    format[i] = '\0';
    assert(&format[i+1] == mem.get() + bytes);
    assert(this->impl->symbols.count(name) == 0);
    this->impl->symbols[name] = (InfoTable const *) mem.release();
    this->impl->owned_tables.push_back(info);
    return info;
  }

  DataType const * Module::get_type(std::string const & name) const
  {
    auto p = this->impl->types.find(name);
    return (p != this->impl->types.end()) ? p->second : nullptr;
  }

  DataType const * Module::create_type(
      std::string const & name
    , std::vector<InfoTable const *> constructors
    , flag_type flags
    )
  {
    assert(!this->get_type(name));
    // A kept type with the same number of constructors is taken back (see
    // clear).
    auto kept_module = g_kept_types.find(this->name);
    if(kept_module != g_kept_types.end())
    {
      auto kept = kept_module->second.find(name);
      if(kept != kept_module->second.end())
      {
        DataType * type = const_cast<DataType *>(kept->second);
        if(type->size == constructors.size())
        {
          kept_module->second.erase(kept);
          InfoTable const ** ctor_list = const_cast<InfoTable const **>(type->ctors);
          type->flags = flags;
          for(size_t i=0; i<constructors.size(); ++i)
          {
            auto ctor = const_cast<InfoTable *>(constructors[i]);
            ctor_list[i] = ctor;
            ctor->type = type;
          }
          this->impl->types[name] = type;
          this->impl->owned_types.push_back(type);
          return type;
        }
      }
    }
    size_t const bytes = sizeof(DataType) + sizeof(void *) * constructors.size() + name.size() + 1;
    std::unique_ptr<char[]> mem(new char[bytes]);
    DataType * type = (DataType *) mem.get();
    InfoTable const ** ctor_list = (InfoTable const **) (type + 1);
    char * type_name = (char *) &ctor_list[constructors.size()];
    type->ctors = ctor_list;
    type->size = constructors.size();
    type->kind = 't';
    type->flags = flags;
    type->name = type_name;
    size_t i=0;
    for(; i<constructors.size(); ++i)
    {
      auto ctor = const_cast<InfoTable *>(constructors[i]);
      ctor_list[i] = ctor;
      ctor->type = type;
    }
    std::strcpy(type_name, name.c_str());
    assert(type_name + name.size() + 1 == mem.get() + bytes);
    this->impl->types[name] = (DataType const *) mem.release();
    this->impl->owned_types.push_back(type);
    return type;
  }

  DataType const * Module::get_builtin_type(std::string const & name) const
  {
    auto * ty = this->get_type(name);
    return (ty && is_static(*ty)) ? ty : nullptr;
  }

  InfoTable const * Module::get_builtin_symbol(std::string const & name) const
  {
    auto * info = this->get_infotable(name);
    return (info && is_static(*info)) ? info : nullptr;
  }

  // The trap step (see module.hpp).
  namespace
  {
    trap_hook_type g_trap_hook = nullptr;

    std::string trap_message(InfoTable const * info, std::string const & reason)
    {
      std::string const owner = owner_of(info);
      std::string text = "cannot evaluate function '";
      if(!owner.empty())
        text += owner + ".";
      text += info->name;
      text += "': the function has no compiled code (its module was imported "
              "from an ICurry object under interpret:off)";
      if(!reason.empty())
        text += ": " + reason;
      return text;
    }
  }

  void set_trap_hook(trap_hook_type hook)
  {
    g_trap_hook = hook;
  }

  std::string owner_of(InfoTable const * info)
  {
    if(info)
      for(auto && item: Module::getall())
        if(item.second->get_infotable(info->name) == info)
          return item.first;
    return {};
  }

  tag_type trap_step(RuntimeState * rts, Configuration * C)
  {
    InfoTable const * info = C->cursor()->info;
    std::string reason;
    if(g_trap_hook)
      reason = g_trap_hook(info);
    else
      reason = "no compile hook is installed";
    // The hook gave the table its code: run it on the same redex.
    if(info->step != &trap_step)
      return info->step(rts, C);
    C->set_error(trap_message(info, reason));
    return E_ERROR;
  }

  void install_trap(InfoTable * info)
  {
    if(!info)
      throw std::invalid_argument("install_trap: a null argument");
    if(info->tag != T_FUNC)
      throw std::invalid_argument(
          std::string("install_trap: ") + info->name + " is not a function"
        );
    if(is_static(*info))
      throw std::invalid_argument(
          std::string("install_trap: ") + info->name
          + " is a static info table (a built-in or a compiled module)"
        );
    if(info->step && info->step != &trap_step)
      throw std::invalid_argument(
          std::string("install_trap: ") + info->name + " has a step already"
        );
    info->step = &trap_step;
  }
}

