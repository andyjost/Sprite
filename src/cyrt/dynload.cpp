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
  SharedLib::SharedLib(std::string const & sofile)
  {
    void * handle = dlopen(sofile.c_str(), RTLD_LAZY | RTLD_GLOBAL);
    if(!handle)
    {
      char const * msg = dlerror();
      assert(msg);
      throw DynloadError(msg);
    }
    this->_handle.reset(handle, dlcloser());
  }

  SharedCurryModule::SharedCurryModule(std::string const & sofile)
    : SharedLib(sofile)
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
