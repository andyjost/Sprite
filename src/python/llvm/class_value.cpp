#include <boost/python.hpp>
#include <boost/python/enum.hpp>
#include <boost/preprocessor/seq/for_each.hpp>
#include "python/llvm/_llvm.hpp"
#include "sprite/llvm/value.hpp"
#include "sprite/llvm/isa.hpp"
// #include "sprite/misc/python_conversions.hpp"

using namespace boost::python;
using namespace sprite::llvm;

namespace
{
  std::string value_repr(value v)
    { return (boost::format("%s(%s)") % typeof_(v) % v).str(); }
}

namespace sprite { namespace python
{
  void register_value()
  {
    using self_ns::str;
    class_<value>("value", no_init)
      .def(init<double>())
      .def(init<int64_t>())
      .def(str(self))
      .def("__repr__", value_repr)
      // .def(self == other<value>())
      // .def(self != other<value>())
      .add_property("id", &value::id)
      .add_property("typeof", &sprite::llvm::typeof_)
      .def("isa", (bool(*)(value, ValueTy))(isa))
      ;

    enum_<ValueTy>("ValueTy")
        #define OP(r,_,name) .value(BOOST_PP_STRINGIZE(name), ValueTy::name)
        BOOST_PP_SEQ_FOR_EACH(OP,,SPRITE_LLVM_VALUES)
        #undef OP
        .export_values();

    implicitly_convertible<int64_t, value>();
    implicitly_convertible<float, value>();
    implicitly_convertible<double, value>();
  }
}}
