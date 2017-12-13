#include <boost/python.hpp>
#include <boost/python/enum.hpp>
#include <boost/format.hpp>
#include <boost/preprocessor/seq/for_each.hpp>
#include <boost/python/raw_function.hpp>
#include "python/llvm/conversions.hpp"
#include "python/llvm/_llvm.hpp"
#include "python/llvm/utility.hpp"
#include "sprite/llvm/isa.hpp"
#include "sprite/llvm/type.hpp"
#include "sprite/llvm/value.hpp"
#include <vector>

using namespace boost::python;
using namespace sprite::llvm;
using namespace sprite::python;

namespace
{
  type py_type__call__(tuple args, dict kwds)
  {
    assert(len(args) > 0);
    type self = extract<type>(args[0]);
    object kw;
    object pop = kwds.attr("pop");
    size_t const nargs = len(args);
    try { kw = pop("varargs"); }
    catch(error_already_set const &) { PyErr_Clear(); }
    int is_varargs = (kw.ptr() == Py_None) ? -1
        : bool(extract<bool>(kw)) ? 1 : 0;
    reject_kwds(kwds);

    std::vector<::llvm::Type*> types;
    for(size_t i=1; i<nargs; ++i)
    {
      object arg = args[i];
      try
      {
        type ty = extract<type>(arg);
        types.push_back(ty.ptr());
      }
      catch(error_already_set const &)
      {
        if(arg.attr("__class__").attr("__name__") == "ellipsis")
        {
          if(i != nargs-1)
            throw type_error("An ellipsis must be the final argument.");
          else if(is_varargs != -1)
          {
            throw type_error(
                "Got both an Ellipsis and 'varargs' keyword argument."
              );
          }
          is_varargs = 1;
        }
        else throw;
      }
    }
    return self.make_function(types, is_varargs==1);
  }
  
  value py_type_cast(type dst_ty, value v, bool src_is_signed, bool dst_is_signed)
    { return cast_(v, dst_ty, src_is_signed, dst_is_signed); }

  type py_common_type(tuple args, dict kwds)
  {
    reject_kwds(kwds);
    using iterator = stl_input_iterator<type>;
    auto begin = iterator(args);
    auto end = iterator();
    std::vector<type> types(begin, end);
    return common_type(types);
  }
}

namespace sprite { namespace python
{
  void register_type()
  {
    NoneConversion::init();
    VectorConversion<type>::init();
    VectorConversion<size_t>::init();

    using self_ns::str;
    class_<type>("type_", no_init)
      .def(str(self))
      .def(repr(self))
      .add_property("id", &type::id)
      .add_property("p", (type(type::*)() const)(&type::operator*)
        , "Creates a pointer type."
        )
      .def(other<size_t>() * self)
      .def(self * other<size_t>())
      .def(self == other<type>())
      .def(self != other<type>())
      .def("__getitem__", &type::operator[], "Creates an array type.")
      .def("__call__", raw_function(py_type__call__, 0)
        , "Creates a function type.  Keyword 'varargs' may be supplied or "
          "the Ellipsis object may be passed as the final positional argument "
          "to indicate a variadic function."
        )
      .def("__call__", py_type_cast
        , (arg("value"), arg("src_is_signed")=true, arg("dst_is_signed")=true)
        )
      .add_property("array_extents", array_extents)
      .add_property("bitwidth", bitwidth)
      .add_property("decay", decay)
      .add_property("null_value", null_value)
      .add_property("kind", (TypeTy(*)(type))(kind))
      .add_property("sizeof", sizeof_)
      .add_property("struct_name", struct_name)
      .add_property("subtypes", subtypes)
      .def("isa", (bool(*)(type, TypeTy))(isa))
      ;
    def("bitcast", bitcast_, (arg("value"), arg("type")));
    def("cast", cast_
      , (arg("value"), arg("type"), arg("src_is_signed")=true, arg("dst_is_signed")=true)
      );
    def("is_bitcastable", is_bitcastable);
    def("is_castable", is_castable);
    def("common_type", raw_function(py_common_type, 0));

    enum_<TypeTy>("TypeTy")
        #define OP(r,_,name) .value(BOOST_PP_STRINGIZE(name), TypeTy::name)
        BOOST_PP_SEQ_FOR_EACH(OP,,SPRITE_LLVM_TYPES)
        #undef OP
        .export_values();
  }
}}
