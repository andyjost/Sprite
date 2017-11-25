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
  pointer_type type::operator*() const
    { return pointer_type(SPRITE_APICALL(this->ptr()->getPointerTo())); }

  array_type type::operator[](size_t size) const
  {
    auto const size_ = static_cast<uint64_t>(size);
    return array_type(SPRITE_APICALL(ArrayType::get(this->ptr(), size_)));
  }

  function_type type::make_function(
      std::vector<::llvm::Type*> const & args, bool is_varargs
    ) const
  {
    return function_type(SPRITE_APICALL(
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
  integer_type int_(unsigned numBits)
  {
    auto & cxt = scope::current_context();
    return integer_type(SPRITE_APICALL(IntegerType::get(cxt, numBits)));
  }

  integer_type long_() { return int_(sizeof(long) * 8); }
  integer_type long_long() { return int_(sizeof(long long) * 8); }
  integer_type char_() { return int_(8); }
  integer_type bool_() { return int_(1); }

  fp_type float_(size_t numBits)
  {
    switch(numBits)
    {
      case 32: return float_();
      case 64: return double_();
      case 128: return long_double();
      default:
      {
        throw type_error(
            "Unsupported floating-point width (" + std::to_string(numBits) +
            " bits): expected 32/64/128 bits."
          );
      }
    }
  }

  fp_type float_()
  {
    auto & cxt = scope::current_context();
    auto const p = SPRITE_APICALL(Type::getFloatTy(cxt));
    return fp_type(reinterpret_cast<FPType*>(p));
  }

  fp_type double_()
  {
    auto & cxt = scope::current_context();
    auto const p = SPRITE_APICALL(Type::getDoubleTy(cxt));
    return fp_type(reinterpret_cast<FPType*>(p));
  }

  fp_type long_double()
  {
    auto & cxt = scope::current_context();
    auto const p = SPRITE_APICALL(Type::getFP128Ty(cxt));
    return fp_type(reinterpret_cast<FPType*>(p));
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

  struct_type struct_(array_ref<type> const & elements)
  {
    auto & cxt = scope::current_context();
    std::vector<Type*> tmp;
    for(auto e: elements)
    {
      if(!::llvm::StructType::isValidElementType(e.ptr()))
        throw type_error("Invalid struct element type.");
      tmp.emplace_back(e.ptr());
    }
    return struct_type(SPRITE_APICALL(StructType::get(cxt, tmp)));
  }

  struct_type struct_(string_ref const & name)
  {
    module const mod = scope::current_module();
    if(!mod.ptr())
    {
      throw compile_error(
          "No current module (needed to lookup named struct)."
        );
    }
    StructType * ty = mod->getTypeByName(name);
    if(!ty)
      ty = SPRITE_APICALL(StructType::create(mod.context(), name));
    return struct_type(ty);
  }

  struct_type struct_(
      string_ref const & name, array_ref<type> const & elements
    )
  {
    struct_type const tp = struct_(name);
    std::vector<Type*> body;
    for(auto e: elements) { body.emplace_back(e.ptr()); }
    SPRITE_APICALL(tp->setBody(body, /*isPacked*/ false));
    return tp;
  }
  #endif
}}}
