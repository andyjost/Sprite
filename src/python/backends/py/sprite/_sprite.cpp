#include "boost/python.hpp"
//
#include "sprite/fingerprint.hpp"
#include "sprite/misc/register_exception.hpp"

using namespace boost::python;
using namespace sprite::python;

namespace sprite { namespace python
{
  void register_fingerprint();
}}

BOOST_PYTHON_MODULE(_sprite)
{
  sprite::python::register_fingerprint();
}
