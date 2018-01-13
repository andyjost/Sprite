#include "sprite/llvm/exceptions.hpp"
#include "sprite/llvm/module.hpp"
#include "sprite/llvm/value.hpp"

namespace sprite { namespace llvm
{
  ::llvm::LLVMContext & getContext()
  {
    static thread_local ::llvm::LLVMContext * context = new ::llvm::LLVMContext;
    return *context;
  }

  value module::def(
      std::string const & name, type ty, bool is_const, LinkageTypes linkage
    , value init
    )
  {
    if(ptr()->getNamedValue(name))
      throw value_error(boost::format("global '%s' exists") % name);
    if(init.ptr())
      init = cast(init, ty);
    auto * C = dyn_cast_or_null<Constant>(init.ptr());
    if(init.ptr() && !C)
      throw type_error(boost::format("initializer is not a constexpr"));
    return new GlobalVariable(*ptr(), ty, is_const, linkage, C, name);
  }
}}
