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

  std::unordered_map<std::string, SharedCurryModule const *> registry;

  void register_lib(SharedCurryModule const & lib)
  {
    assert(lib.bom);
    auto rv = registry.emplace(lib.bom->fullname, &lib);
    assert(rv.second);
  }

  void unregister_lib(char const * module_fullname)
  {
    if(module_fullname)
    {
      auto rv = registry.erase(module_fullname);
      assert(rv == 1);
    }
  }

  struct dlcloser
  {
    char const * module_fullname = nullptr;
    void operator()(void * handle) const
    {
      unregister_lib(this->module_fullname);
      auto err = dlclose(handle);
      if(err)
      {
        char const * msg = dlerror();
        assert(msg);
        std::cerr << msg << std::endl;
      }
    }
  };
}

namespace cyrt
{
  extern SharedCurryModule const * Prelude;

  SharedLib::SharedLib(std::string const & sofilename)
    : _sofilename(sofilename)
  {
    void * handle = dlopen(sofilename.c_str(), RTLD_LAZY | RTLD_GLOBAL);
    if(!handle)
    {
      char const * msg = dlerror();
      assert(msg);
      throw DynloadError(msg);
    }
    this->_handle.reset(handle, dlcloser());
  }

  SharedCurryModule::SharedCurryModule(std::string const & sofilename)
    : SharedLib(sofilename)
  {
    auto addr = dlsym(this->handle(), "_bom_");
    if(!addr)
    {
      char const * msg = dlerror();
      assert(msg);
      throw DynloadError(msg);
    }
    this->bom = *(ModuleBOM const **) addr;

    register_lib(*this);
    // Register the module name with the deleter so that it can be removed from
    // the registry when unloaded.
    auto * deleter = std::get_deleter<dlcloser>(this->_handle);
    assert(deleter);
    deleter->module_fullname = this->bom->fullname.c_str();
  }

  SharedCurryModule const * SharedCurryModule::find(char const * module_fullname)
  {
    auto rv = registry.find(module_fullname);
    return (rv == registry.end()) ? nullptr : rv->second;
  }

  InfoTable const * SharedCurryModule::symbol(
      char const * module_fullname, char const * symbolname
    )
  {
    auto * module = SharedCurryModule::find(module_fullname);
    if(module)
      return (InfoTable const *) dlsym(module->handle(), symbolname);
    else
      return nullptr;
  }
}
