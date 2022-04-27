#include <cassert>
#include "cyrt/dynload.hpp"
#include "cyrt/exceptions.hpp"
#include <iostream>
#include <sstream>
#include <dlfcn.h>

namespace
{
  using namespace cyrt;

  static SharedLib const libcyrt("libcyrt.so");

  struct dlcloser
  {
    void operator()(void * handle) const
    {
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
  }
}
