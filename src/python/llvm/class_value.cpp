#include <boost/python.hpp>
#include <boost/preprocessor/seq/for_each.hpp>
#include <boost/python/enum.hpp>
#include <boost/python/raw_function.hpp>
#include "python/llvm/_llvm.hpp"
#include "sprite/llvm/isa.hpp"
#include "python/llvm/utility.hpp"
#include "sprite/llvm/value.hpp"
#include <memory>
#include <string>

using namespace boost::python;
using namespace sprite::llvm;
using namespace sprite::python;

namespace
{
  std::string value_repr(value v)
    { return (boost::format("%s(%s)") % typeof_(v) % v).str(); }

  object value__init__(tuple args, dict kwds)
  {
    reject_kwds(kwds);
    if(len(args) != 2)
      type_error(boost::format("expected 2 arguments, got %d") % len(args));

    object self = args[0];
    object arg = args[1];

    // Convert Numpy numbers to native Python.
    try
      { arg = arg.attr("item")(); }
    catch(error_already_set const &)
      { PyErr_Clear(); }

    if(PyInt_Check(arg.ptr()))
    {
      int64_t v = extract<int64_t>(arg);
      return self.attr("__init__")(value::from_int64(v));
    }
    if(PyFloat_Check(arg.ptr()))
    {
      double v = extract<double>(arg);
      return self.attr("__init__")(value::from_double(v));
    }
    auto cls = arg.attr("__class__");
    std::string argtype = extract<std::string>(cls.attr("__name__"));
    std::string modname = extract<std::string>(cls.attr("__module__"));
    throw type_error(
        boost::format("cannot construct a value from this object of type '%s.%s'.")
            % modname % argtype
      );
  }
}

namespace sprite { namespace python
{
  void register_value()
  {
    using self_ns::str;
    class_<value>("value", no_init)
      .def(init<int64_t>())
      .def(init<double>())
      .def("__init__", raw_function(value__init__))
      .def(init<value>())
      .def(str(self))
      .def("__repr__", value_repr)
      // .def(self == other<value>())
      // .def(self != other<value>())
      .add_property("id", &value::id)
      .add_property("typeof", &sprite::llvm::typeof_)
      .def("isa", (bool(*)(value, ValueTy))(isa))
      ;

    implicitly_convertible<int64_t, value>();
    implicitly_convertible<double, value>();

    enum_<ValueTy>("ValueTy")
        #define OP(r,_,name) .value(BOOST_PP_STRINGIZE(name), ValueTy::name)
        BOOST_PP_SEQ_FOR_EACH(OP,,SPRITE_LLVM_VALUES)
        #undef OP
        .export_values();
  }
}}
