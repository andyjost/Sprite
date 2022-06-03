#include <algorithm>
#include <cstring>
#include "cyrt/builtins.hpp"
#include "cyrt/currylib/prelude.hpp"
#include "cyrt/currylib/setfunctions.hpp"
#include "cyrt/graph/infotable.hpp"
#include "cyrt/module.hpp"
#include <iostream>
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
}

namespace cyrt
{
  struct Module::Impl
  {
    SymbolTable symbols;
    TypeTable types;
    std::shared_ptr<SharedCurryModule> shlib;
  };

  void Module::register_builtin_module(
      std::string const & name, TypeTable && types, SymbolTable && symbols
    )
  {
    assert(g_builtin_modules.count(name) == 0);
    BuiltinModuleData data{std::move(types), std::move(symbols)};
    auto rv = g_builtin_modules.try_emplace(name, std::move(data));
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
        this->impl->symbols[info->name] = info;
      }
    }
  }

  void Module::clear()
  {
    for(auto & p_symbol: this->impl->symbols)
      if(!is_static(*p_symbol.second))
        delete[] (char *) p_symbol.second;
    this->impl->symbols.clear();

    for(auto & p_type: this->impl->types)
      if(!is_static(*p_type.second))
        delete[] (char *) p_type.second;
    this->impl->types.clear();
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
    std::strcpy(info_name, name.c_str());
    index_type i=0;
    for(; i<arity; ++i)
      format[i] = 'p';
    format[i] = '\0';
    assert(&format[i+1] == mem.get() + bytes);
    assert(this->impl->symbols.count(name) == 0);
    this->impl->symbols[name] = (InfoTable const *) mem.release();
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
}

