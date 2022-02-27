#include <algorithm>
#include <cstring>
#include <iostream>
#include <unordered_map>
#include "sprite/builtins.hpp"
#include "sprite/cxx.hpp"
#include "sprite/graph/infotable.hpp"

using namespace sprite;
using SymbolTable = std::unordered_map<std::string, InfoTable const *>;
using TypeTable = std::unordered_map<std::string, Type const *>;

namespace
{
  std::unordered_map<std::string, std::weak_ptr<Module>> g_modules;
}

namespace sprite
{
  struct Module::Impl
  {
    SymbolTable symbols;
    TypeTable types;
  };

  SymbolTable const builtin_prelude_symbols{
      {"Char" , &Char_Info}
    , {"IO"   , &IO_Info}
    , {"Int"  , &Int_Info}
    , {"Float", &Float_Info}
    , {"False", &False_Info}
    , {"True" , &True_Info}
    , {":"    , &Cons_Info}
    , {"[]"   , &Nil_Info}
    , {"()"   , &Unit_Info}
    , {"(,)"  , &Pair_Info}
    };

  TypeTable const builtin_prelude_types{
      {"Bool" , &Bool_Type}
    , {"Char" , &Char_Type}
    , {"Float", &Float_Type}
    , {"IO"   , &IO_Type}
    , {"Int"  , &Int_Type}
    , {"List" , &List_Type}
    , {"Pair" , &Pair_Type}
    , {"Unit" , &Unit_Type}
    };

  SymbolTable const builtin_setfunction_symbols{
      {"PartialS", &PartialS_Info}
    , {"SetEval" , &SetEval_Info}
    };

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
    if(name == "Prelude")
    {
      this->impl->symbols = builtin_prelude_symbols;
      this->impl->types = builtin_prelude_types;
    }
    else if(name == "Control.SetFunctions")
      this->impl->symbols = builtin_setfunction_symbols;
  }

  Module::~Module()
  {
    for(auto & p: this->impl->symbols)
      if(!(p.second->flags & STATIC_OBJECT))
        delete[] (char *) p.second;
    for(auto & p: this->impl->types)
      if(!(p.second->flags & STATIC_OBJECT))
        delete[] (char *) p.second;
  }

  InfoTable const * Module::get_infotable(std::string const & name) const
  {
    auto p = this->impl->symbols.find(name);
    if(p != this->impl->symbols.end())
      return p->second;
    return nullptr;
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
    info->typetag    = (TypeTag) flags;
    info->flags      = flags >> 8 * sizeof(TypeTag);
    info->name       = info_name;
    info->format     = format;
    info->step       = nullptr;
    info->typecheck  = nullptr;
    info->type       = nullptr;
    std::strncpy(info_name, name.c_str(), name.size());
    index_type i=0;
    for(; i<arity; ++i)
      format[i] = 'p';
    format[i] = '\0';
    assert(&format[i+1] == mem.get() + bytes);
    this->impl->symbols[name] = (InfoTable const *) mem.release();
    return info;
  }

  Type const * Module::get_type(std::string const & name) const
  {
    auto p = this->impl->types.find(name);
    if(p != this->impl->types.end())
      return p->second;
    return nullptr;
  }

  Type const * Module::create_type(
      std::string const & name
    , std::vector<InfoTable const *> constructors
    )
  {
    assert(!this->get_type(name));
    size_t const bytes = sizeof(Type) + sizeof(void *) * constructors.size();
    std::unique_ptr<char[]> mem(new char[bytes]);
    Type * type = (Type *) mem.get();
    InfoTable const ** ctor_list = (InfoTable const **) (type + 1);
    type->ctors = ctor_list;
    type->size = constructors.size();
    size_t i=0;
    for(; i<constructors.size(); ++i)
    {
      auto ctor = const_cast<InfoTable *>(constructors[i]);
      ctor_list[i] = ctor;
      ctor->type = type;
    }
    assert((char *) &ctor_list[i] == mem.get() + bytes);
    this->impl->types[name] = (Type const *) mem.release();
    return type;
  }
}
