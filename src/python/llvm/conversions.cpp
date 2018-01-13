#include "python/llvm/conversions.hpp"
#include <iostream>

namespace sprite
{
  PyObject * NoneConversion::convert(boost::none_t const &)
    { return incref(Py_None); }
  void * NoneConversion::check(PyObject * obj)
    { return obj == Py_None ? obj : nullptr; }
  void NoneConversion::construct(
      PyObject * obj
    , converter::rvalue_from_python_stage1_data * data
    )
  {
    typedef converter::rvalue_from_python_storage<
        boost::none_t
      > * storage_type;
    void * storage = (reinterpret_cast<storage_type>(data))->storage.bytes;
    data->convertible = new(storage) boost::none_t(boost::none);
  }
}
