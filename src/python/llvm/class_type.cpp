#include <boost/python.hpp>
#include <boost/format.hpp>
#include <boost/python/raw_function.hpp>
#include "python/llvm/_llvm.hpp"
#include "sprite/llvm/type.hpp"
#include "sprite/llvm/value.hpp"
#include "sprite/misc/python_conversions.hpp"
#include <vector>

using namespace boost::python;
using sprite::llvm::type_error;
using sprite::llvm::type;
using sprite::llvm::value;

namespace
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

  type type__call__(tuple args, dict kwds)
  {
    assert(len(args) > 0);
    sprite::llvm::type self = extract<sprite::llvm::type>(args[0]);

    object kw;
    object pop = kwds.attr("pop");
    try { kw = pop("varargs"); }
    catch(error_already_set const &) { PyErr_Clear(); }
    int is_varargs = (kw.ptr() == Py_None) ? -1
        : bool(extract<bool>(kw)) ? 1 : 0;
    reject_kwds(kwds);

    std::vector<::llvm::Type*> types;
    for(size_t i=1, n=len(args); i<n; ++i)
    {
      object arg = args[i];
      try
      {
        sprite::llvm::type ty = extract<sprite::llvm::type>(arg);
        types.push_back(ty.ptr());
      }
      catch(error_already_set const &)
      {
        if(arg.attr("__class__").attr("__name__") == "ellipsis")
        {
          if(i != n-1)
            throw type_error("An ellipsis must be the final argument.");
          if(is_varargs != -1)
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

  type py_common_type(tuple args, dict kwds)
  {
    reject_kwds(kwds);
    using iterator = stl_input_iterator<type>;
    auto begin = iterator(args);
    auto end = iterator();
    std::vector<type> types(begin, end);

    return sprite::llvm::common_type(types);
  }
}

namespace sprite { namespace python
{
  void register_type()
  {
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
      .def("__call__", raw_function(type__call__, 0)
        , "Creates a function type.  Keyword 'varargs' may be supplied or "
          "the Ellipsis object may be passed as the final positional argument "
          "to indicate a variadic function."
        )
      .def("__call__"
        , (value (type::*)(value, bool, bool) const)(&type::operator())
        , (arg("value"), arg("src_is_signed")=true, arg("dst_is_signed")=true)
        )
      .add_property("array_extents", sprite::llvm::array_extents)
      .add_property("decay", sprite::llvm::decay)
      .add_property("is_array", sprite::llvm::is_array)
      .add_property("is_floating_point", sprite::llvm::is_floating_point)
      .add_property("is_function", sprite::llvm::is_function)
      .add_property("is_integer", sprite::llvm::is_integer)
      .add_property("is_pointer", sprite::llvm::is_pointer)
      .add_property("is_struct", sprite::llvm::is_struct)
      .add_property("is_vector", sprite::llvm::is_vector)
      .add_property("is_void", sprite::llvm::is_void)
      .add_property("sizeof", sprite::llvm::sizeof_)
      .add_property("struct_name", sprite::llvm::struct_name)
      .add_property("subtypes", sprite::llvm::subtypes)
      ;
    def("common_type", raw_function(py_common_type, 0));
  }
}}
