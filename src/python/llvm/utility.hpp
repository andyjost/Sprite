#pragma once
#include <boost/python.hpp>

namespace sprite { namespace python
{
  /// Raises an error if any keyword arguments are set.
  void reject_kwds(boost::python::dict);
}}
