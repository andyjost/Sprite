#include <boost/python.hpp>
#include "sprite/fingerprint.hpp"
#include "python/runtime/_runtime.hpp"
#include "sprite/misc/register_exception.hpp"

using namespace boost::python;
using namespace sprite::python;

BOOST_PYTHON_MODULE(_runtime)
{
  register_fingerprint();
}
