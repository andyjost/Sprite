#include "boost/python.hpp"
#include "boost/python/enum.hpp"
#include "sprite/llvm/module.hpp"
#include "sprite/llvm/type.hpp"
#include "sprite/llvm/value.hpp"
#include "llvm/IR/GlobalValue.h"
#include "llvm/IR/GlobalVariable.h"
#include <string>
#include <memory>

using namespace boost::python;
using namespace sprite::llvm;
// using namespace sprite::python;

using GlobalVariable = ::llvm::GlobalVariable;

#if 0
namespace
{
  // std::shared_ptr<GlobalVariable> globalvariable__init__(
  value make_global_variable(
      type ty, bool is_const, LinkageTypes linkage, value initializer
    )
  {
    if(auto * C = dyn_cast<Constant>(initializer.ptr()))
    {
      return new GlobalVariable(*ty, is_const, linkage, C);
      // return std::shared_ptr<GlobalVariable>(
      //     new GlobalVariable(*ty, is_const, linkage, C)
      //   , [](GlobalVariable *px) { if(px && !px->getParent()) { delete px; }}
      //   );
    }
    throw type_error(
        boost::format("global variable initializer must be a constant, not '%s'")
            % typename_(initializer)
      );
  }
}
#endif

namespace sprite { namespace python
{
  void register_globalvalues()
  {
    enum_<LinkageTypes>("LinkageTypes")
        .value("EXTERN", ::llvm::GlobalValue::ExternalLinkage)
        .value("INLINE", ::llvm::GlobalValue::LinkOnceAnyLinkage)
        .value("STATIC", ::llvm::GlobalValue::InternalLinkage)
        .value("PRIVATE", ::llvm::GlobalValue::PrivateLinkage)
        .export_values();

    // def("global_", make_global_variable);

    // class_<GlobalVariable, std::shared_ptr<GlobalVariable>, boost::noncopyable>
    //     ("globalvariable", no_init)
    //     .def("__init__", make_constructor(&globalvariable__init__))
    //   ;
  }
}}
