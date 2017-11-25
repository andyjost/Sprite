#include <boost/python.hpp>
#include <boost/python/raw_function.hpp>
#include "python/llvm/_llvm.hpp"
#include "sprite/llvm/type.hpp"
#include <boost/format.hpp>
#include <initializer_list>
#include <vector>

using namespace boost::python;
using sprite::llvm::type_error;

namespace
{
  sprite::llvm::function_type
  type__call__(tuple args, dict kwds)
  {
    assert(len(args) > 0);
    sprite::llvm::type self = extract<sprite::llvm::type>(args[0]);

    object kw;
    object pop = kwds.attr("pop");
    try { kw = pop("varargs"); }
    catch(error_already_set const &) { PyErr_Clear(); }
    int is_varargs = (kw.ptr() == Py_None) ? -1
        : bool(extract<bool>(kw)) ? 1 : 0;

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
    return self.make_function(types, is_varargs);
  }
}

namespace sprite { namespace python
{
  void register_type()
  {
    using self_ns::str;
    class_<sprite::llvm::type>("type", no_init)
      .def(str(self))
      .def(repr(self))
      .add_property("p", &sprite::llvm::type::operator*
        , "Creates a pointer type."
        )
      .def("__getitem__", &sprite::llvm::type::operator[]
        , "Creates an array type."
        )
      .def("__call__", raw_function(&type__call__, 0)
        , "Creates a function type.  Keyword 'varargs' may be supplied or "
          "the Ellipsis object may be passed as the final positional argument "
          "to indicate a variadic function."
        )
      .def("sizeof", sprite::llvm::sizeof_)
      ;

    // Module-level functions.
    def("int_", &sprite::llvm::types::int_, arg("numBits")
      , "Creates an integer type.");
    def("long", &sprite::llvm::types::long_
      , "Creates a long integer type.");
    def("long_long", &sprite::llvm::types::long_long
      , "Creates a long long integer type.");
    def("float_", (sprite::llvm::fp_type (*)())(&sprite::llvm::types::float_)
      , "Creates a 32-bit floating-point type.");
    def("double", &sprite::llvm::types::double_
      , "Creates a 64-bit floating-point type.");
    def("long_double", &sprite::llvm::types::long_double
      , "Creates a 128-bit floating-point type.");
  }
}}

