#include <boost/python.hpp>
#include "sprite/llvm/type.hpp"
#include <boost/python/stl_iterator.hpp>

using namespace boost::python;
using sprite::llvm::type;

namespace
{
  type opaque_struct(object types)
  {
    stl_input_iterator<type> begin(types), end;
    return sprite::llvm::types::struct_(std::vector<type>(begin, end));
  }

  type complete_struct(std::string const & name, object types)
  {
    stl_input_iterator<type> begin(types), end;
    return sprite::llvm::types::struct_(name, std::vector<type>(begin, end));
  }
}

BOOST_PYTHON_MODULE(_types)
{
  def("int_", (type (*)(size_t))(&sprite::llvm::types::int_)
    , arg("numBits")=sizeof(int)*8, "Creates an integer type.");
  def("long", &sprite::llvm::types::long_
    , "Creates a long integer type.");
  def("longlong", &sprite::llvm::types::longlong
    , "Creates a long long integer type.");
  def("float_", (type (*)())(&sprite::llvm::types::float_)
    , "Creates a 32-bit floating-point type.");
  def("double", &sprite::llvm::types::double_
    , "Creates a 64-bit floating-point type.");
  def("longdouble", &sprite::llvm::types::longdouble
    , "Creates a 128-bit floating-point type.");
  def("struct", &opaque_struct);
  def("struct", &complete_struct);
  def("struct"
    , (type (*)(std::string const &))(&sprite::llvm::types::struct_)
    );

  scope().attr("void") = sprite::llvm::types::void_();
  scope().attr("bool_") = sprite::llvm::types::bool_();
  scope().attr("char") = sprite::llvm::types::char_();
  scope().attr("i1") = sprite::llvm::types::int_(1);
  scope().attr("i8") = sprite::llvm::types::int_(8);
  scope().attr("i16") = sprite::llvm::types::int_(16);
  scope().attr("i32") = sprite::llvm::types::int_(32);
  scope().attr("i64") = sprite::llvm::types::int_(64);
  scope().attr("i128") = sprite::llvm::types::int_(128);
  scope().attr("fp32") = sprite::llvm::types::float_(32);
  scope().attr("fp64") = sprite::llvm::types::float_(64);
  scope().attr("fp128") = sprite::llvm::types::float_(128);
}
