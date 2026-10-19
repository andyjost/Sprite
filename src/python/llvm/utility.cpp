#include "python/llvm/utility.hpp"
#include "curryrt/llvm/exceptions.hpp"

using namespace boost::python;
using namespace curryrt::llvm;

namespace curryrt { namespace python
{
  void reject_kwds(dict kwds)
  {
    if(len(kwds) != 0)
    {
      std::string arg = extract<std::string>(
          kwds.attr("__iter__")().attr("next")()
        );
      throw type_error(
          boost::format(
              "'%s' is an invalid keyword argument for this function."
            ) % arg
        );
    }
  }
}}


