#include <cassert>
#include "cyrt/dynload.hpp"
#include "cyrt/exceptions.hpp"
#include <dlfcn.h>
#include <iostream>
#include <sstream>
#include <unordered_map>

namespace
{
  using namespace cyrt;
  static SharedLib const libcyrt("libcyrt.so");
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
      for(unsigned i=0; i<record.n_types; ++i)
      {
        bom::Type const & type = record.types[i];
        std::vector<Metadata const *> ctors;
        if(type.type)
          for(index_type j=0; j<type.type->size; ++j)
            ctors.push_back(this->metadata(type.constructors[j]));
        this->out.types.emplace_back(
            this->metadata(type.metadata), std::move(ctors), type.type
          );
      }
      for(unsigned i=0; i<record.n_functions; ++i)
      {
        bom::Function const & function = record.functions[i];
        this->out.functions.emplace_back(
            bool(function.visibility), this->metadata(function.metadata)
          , function.info
          );
      }
    }
  };
}

namespace cyrt
{
  std::unique_ptr<ModuleBOM> ModuleBOM::decode(bom::Module const & record)
  {
    auto out = std::make_unique<ModuleBOM>();
    Decoder decoder{*out, {}};
    decoder.run(record);
    return out;
  }

  SharedLib::SharedLib(std::string const & sofilename)
    : _handle(nullptr), _sofilename(sofilename)
  {
    this->_handle = dlopen(sofilename.c_str(), RTLD_LAZY | RTLD_GLOBAL);
    if(!this->_handle)
    {
      char const * msg = dlerror();
      assert(msg);
      throw DynloadError(msg);
    }
  }

  SharedLib::~SharedLib()
  {
    auto err = dlclose(this->_handle);
    if(err)
    {
      char const * msg = dlerror();
      assert(msg);
      std::cerr << msg << std::endl;
    }
  }

  SharedCurryModule::SharedCurryModule(std::string const & sofilename)
    : SharedLib(sofilename), _info()
  {
    auto addr = dlsym(this->handle(), "_bom_");
    if(!addr)
    {
      char const * msg = dlerror();
      assert(msg);
      throw DynloadError(msg);
    }
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
    if(pinfo != registry.end())
      this->_info = pinfo->second.lock();
    if(!this->_info)
    {
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
      return (InfoTable const *) dlsym(info->dlhandle, symbolname);
    else
      return nullptr;
  }
}
