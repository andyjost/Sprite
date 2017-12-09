#include "python/llvm/utility.hpp"
#include "sprite/llvm/exceptions.hpp"

using namespace boost::python;
using namespace sprite::llvm;

namespace sprite { namespace python
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


