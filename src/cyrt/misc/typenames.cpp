#include "cyrt/misc/typenames.hpp"


namespace cyrt { namespace llvm
{
  std::string demangle(std::string const & mangled)
  {
    int status;
    std::unique_ptr<char[], void (*)(void*)> result(
        abi::__cxa_demangle(mangled.c_str(), 0, 0, &status), std::free);
    return result.get() ? std::string(result.get()) : mangled;
  }
}}
