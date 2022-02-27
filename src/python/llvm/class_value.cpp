#include "boost/python.hpp"
#include "boost/preprocessor/seq/for_each.hpp"
#include "boost/python/enum.hpp"
#include "boost/python/raw_function.hpp"
#include "python/llvm/conversions.hpp"
#include "python/llvm/_llvm.hpp"
#include "cyrt/llvm/isa.hpp"
#include "cyrt/llvm/module.hpp"
#include "python/llvm/utility.hpp"
#include "cyrt/llvm/value.hpp"
#include <memory>
#include <string>

using namespace boost::python;
using namespace cyrt::llvm;
using namespace cyrt::python;

namespace
{
  object value__init__(tuple args, dict kwds)
  {
    char const * keywords[] = {"self", "value", nullptr};
    PyObject *arg1, *arg2;
    PyArg_ParseTupleAndKeywords(args.ptr(), kwds.ptr(), "OO:value", (char**)keywords, &arg1, &arg2)
        || (({throw error_already_set(); false;}));

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
      return self.attr("__init__")(value::from_int(v));
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

namespace cyrt { namespace python
{
  void register_value()
  {
    VariantConversion<literal_value>::init();
    VariantConversion<value::parent_type>::init();

    using self_ns::str;
    class_<value>("value", no_init)
      .def(init<boost::none_t>("creates an undefined value"))
      .def(init<int64_t>())
      .def(init<double>())
      .def("__init__", raw_function(value__init__))
      .def(init<value>())
      .add_property("id", &value::id)
      .add_property("type", &typeof_)
      .def("constexpr_value", &value::constexpr_value)
      .def("isa", (bool(*)(value, ValueTy))(isa))
      .def("erase", &value::erase)
      .add_property("name", &value::getName, &value::setName)
      .add_property("is_const", &value::getIsConst, &value::setIsConst)
      .add_property("linkage", &value::getLinkage, &value::setLinkage)
      .add_property("init", &value::getInitializer, &value::setInitializer)
      .add_property("parent", &value::parent)
      .def(repr(self))
      .def(str(self))
      ;

    implicitly_convertible<boost::none_t, value>();
    implicitly_convertible<int64_t, value>();
    implicitly_convertible<double, value>();

    enum_<ValueTy>("ValueTy")
        #define OP(r,_,name) .value(BOOST_PP_STRINGIZE(name), ValueTy::name)
        BOOST_PP_SEQ_FOR_EACH(OP,,SPRITE_LLVM_VALUES)
        #undef OP
        .export_values();
  }
}}
