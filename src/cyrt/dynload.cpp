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
}

namespace cyrt
{
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
    ModuleBOM const * bom = *(ModuleBOM const **) addr;

    auto pinfo = registry.find(bom->fullname);
    if(pinfo != registry.end())
      this->_info = pinfo->second.lock();
    if(!this->_info)
    {
      this->_info = std::make_shared<SharedCurryModuleInfo>(
          bom->fullname, sofilename, bom, this->handle()
        );
      if(pinfo == registry.end())
      {
        auto rv = registry.emplace(bom->fullname, this->_info);
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
    return this->_info->bom;
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
