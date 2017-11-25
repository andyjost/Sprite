#include "sprite/llvm/module.hpp"
#include "sprite/llvm/scope.hpp"
#include "sprite/llvm/type.hpp"
#include "sprite/llvm/exceptions.hpp"
// #include "llvm/IR/DataLayout.h"
#include "llvm/IR/Constants.h"
#include <string>
#include <vector>

namespace sprite { namespace llvm
{
  type type::operator*() const
    { return type(SPRITE_APICALL(this->ptr()->getPointerTo())); }

  type type::operator[](size_t size) const
  {
    auto const size_ = static_cast<uint64_t>(size);
    return type(SPRITE_APICALL(ArrayType::get(this->ptr(), size_)));
  }

  type type::make_function(
      std::vector<::llvm::Type*> const & args, bool is_varargs
    ) const
  {
    return type(SPRITE_APICALL(
        FunctionType::get(this->ptr(), args, is_varargs)
      ));
  }

  uint64_t sizeof_(type const & tp)
  {
    ::llvm::DataLayout const layout(scope::current_module().ptr());
    return SPRITE_APICALL(layout.getTypeAllocSize(tp.ptr()));
  }
}}

namespace sprite { namespace llvm { namespace types
{
  type int_(unsigned numBits)
  {
    auto & cxt = scope::current_context();
    return type(SPRITE_APICALL(IntegerType::get(cxt, numBits)));
  }

  type int_() { return int_(sizeof(int) * 8); }
  type long_() { return int_(sizeof(long) * 8); }
  type longlong() { return int_(sizeof(long long) * 8); }
  type char_() { return int_(8); }
  type bool_() { return int_(1); }

  type float_(size_t numBits)
  {
    switch(numBits)
    {
      case 32: return float_();
      case 64: return double_();
      case 128: return longdouble();
      default:
      {
        throw type_error(
            "Unsupported floating-point width (" + std::to_string(numBits) +
            " bits): expected 32/64/128 bits."
          );
      }
    }
  }

  type float_()
  {
    auto & cxt = scope::current_context();
    auto const p = SPRITE_APICALL(Type::getFloatTy(cxt));
    return type(reinterpret_cast<FPType*>(p));
  }

  type double_()
  {
    auto & cxt = scope::current_context();
    auto const p = SPRITE_APICALL(Type::getDoubleTy(cxt));
    return type(reinterpret_cast<FPType*>(p));
  }

  type longdouble()
  {
    auto & cxt = scope::current_context();
    auto const p = SPRITE_APICALL(Type::getFP128Ty(cxt));
    return type(reinterpret_cast<FPType*>(p));
  }

  type void_()
  {
    auto & cxt = scope::current_context();
    return type(SPRITE_APICALL(Type::getVoidTy(cxt)));
  }

  #ifdef TEMPORARILY_DISABLED
  type label()
  {
    auto & cxt = scope::current_context();
    return type(SPRITE_APICALL(Type::getLabelTy(cxt)));
  }
  #endif

  type struct_(std::vector<type> const & elements)
  {
    auto & cxt = scope::current_context();
    std::vector<Type*> tmp;
    for(auto e: elements)
    {
      if(!::llvm::StructType::isValidElementType(e.ptr()))
        throw type_error("Invalid struct element type.");
      tmp.emplace_back(e.ptr());
    }
    return type(SPRITE_APICALL(StructType::get(cxt, tmp)));
  }

  type struct_(std::string const & name)
  {
    module const mod = scope::current_module();
    if(!mod.ptr())
    {
      throw compile_error(
          "No current module (needed to lookup named struct)."
        );
    }
    StructType * ST = mod->getTypeByName(name);
    if(!ST)
      ST = SPRITE_APICALL(StructType::create(mod.context(), name));
    return type(ST);
  }

  type struct_(
      std::string const & name, std::vector<type> const & elements
    )
  {
    type ty = struct_(name);
    auto * ST = ::llvm::cast<StructType>(ty.ptr());
    std::vector<Type*> body;
    for(auto e: elements) { body.emplace_back(e.ptr()); }
    SPRITE_APICALL(ST->setBody(body, /*isPacked*/ false));
    return ty;
  }
}}}
