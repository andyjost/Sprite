#include <boost/python.hpp>
#include "sprite/llvm/type.hpp"

using namespace boost::python;

BOOST_PYTHON_MODULE(_types)
{
  scope().attr("void") = sprite::llvm::types::void_();
  scope().attr("bool_") = sprite::llvm::types::bool_();
  scope().attr("char") = sprite::llvm::types::char_();
  scope().attr("i1") = sprite::llvm::types::int_(1);
  scope().attr("i8") = sprite::llvm::types::int_(8);
  scope().attr("i16") = sprite::llvm::types::int_(16);
  scope().attr("i32") = sprite::llvm::types::int_(32);
  scope().attr("i64") = sprite::llvm::types::int_(64);
  scope().attr("i128") = sprite::llvm::types::int_(128);
  scope().attr("f32") = sprite::llvm::types::float_(32);
  scope().attr("f64") = sprite::llvm::types::float_(64);
  scope().attr("f128") = sprite::llvm::types::float_(128);
}
