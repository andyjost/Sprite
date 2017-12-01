#include "sprite/llvm/exceptions.hpp"
#include "sprite/llvm/module.hpp"
#include "sprite/llvm/scope.hpp"
#include "sprite/llvm/type.hpp"
#include "sprite/llvm/value.hpp"
#include "llvm/IR/Constants.h"
#include <string>
#include <vector>

namespace sprite { namespace llvm
{
  type element_type(type const & ty)
  {
    if(auto * ST = dyn_cast<::llvm::SequentialType>(ty.ptr()))
      return ST->getElementType();
    else if(auto * PT = dyn_cast<PointerType>(ty.ptr()))
      return PT->getElementType();
    throw type_error(boost::format("no element_type for type '%s'") % ty);
  }

  std::vector<type> subtypes(type const & ty)
    { return std::vector<type>(ty->subtype_begin(), ty->subtype_end()); }

  type type::operator*() const
    { return this->ptr()->getPointerTo(); }

  type type::operator*(size_t size) const
    { return VectorType::get(this->ptr(), size); }

  type operator*(size_t size, type ty)
    { return ty * size; }

  type type::operator[](size_t size) const
  {
    return type(ArrayType::get(this->ptr(), size));
  }

  type type::make_function(
      std::vector<::llvm::Type*> const & args, bool is_varargs
    ) const
  {
    return type(FunctionType::get(this->ptr(), args, is_varargs));
  }

  bool operator==(type const & lhs, type const & rhs)
    { return lhs.ptr() == rhs.ptr(); }

  bool operator!=(type const & lhs, type const & rhs)
    { return !(lhs == rhs); }

  std::ostream & operator<<(std::ostream & os, type const & ty)
    { return os << typename_(*ty.ptr()); }

  type decay(type ty)
  {
    if(ty->isArrayTy())
      return ty->getContainedType(0)->getPointerTo();
    else if (ty->isFunctionTy())
      return ty->getPointerTo();
    else
      return ty;
  }

  type common_type(type a, type b)
  {
    if(a == b) return a;

    type a_ = decay(a);
    type b_ = decay(b);
    if(a != a_ || b != b_)
      return common_type(a_, b_);

    if(a->isIntegerTy())
    {
      if(b->isIntegerTy())
        return a->getPrimitiveSizeInBits() < b->getPrimitiveSizeInBits()
          ? b : a;
      else if(b->isFloatingPointTy())
        return b;
    }
    else if(a->isFloatingPointTy())
    {
      if(b->isIntegerTy())
        return a;
      else if(b->isFloatingPointTy())
        return a->getPrimitiveSizeInBits() < b->getPrimitiveSizeInBits()
          ? b : a;
    }
    else if(a->isPointerTy() && b->isPointerTy())
    {
      // Different pointer types.
      if(a->getPointerElementType()->isVoidTy())
        return b;
      if(b->getPointerElementType()->isVoidTy())
        return a;
    }
    throw type_error(boost::format("no common type for '%s' and '%s'") % a % b);
  }

  bool is_array(type ty) { return ty->isArrayTy(); }
  bool is_floating_point(type ty) { return ty->isFloatingPointTy(); }
  bool is_function(type ty) { return ty->isFunctionTy(); }
  bool is_integer(type ty) { return ty->isIntegerTy(); }
  bool is_pointer(type ty) { return ty->isPointerTy(); }
  bool is_struct(type ty) { return ty->isStructTy(); }
  bool is_vector(type ty) { return ty->isVectorTy(); }
  bool is_void(type ty) { return ty->isVoidTy(); }

  std::vector<size_t> array_extents(type const & ty)
  {
    if(!is_array(ty))
      throw type_error(boost::format("expected an array, got '%s'.") % ty);
    std::vector<size_t> v;
    for(Type * TY=ty.ptr(); TY->isArrayTy(); TY=TY->getArrayElementType())
      v.push_back(TY->getArrayNumElements());
    return v;
  }

  size_t sizeof_(type const & tp)
  {
    if(!tp->isSized())
      throw type_error(boost::format("type '%s' is unsized.") % tp);
    ::llvm::DataLayout const layout(scope::current_module().ptr());
    return layout.getTypeAllocSize(tp.ptr());
  }

  std::string struct_name(type const & ty)
  {
    if(!is_struct(ty))
      throw type_error(boost::format("expected a struct, got '%s'.") % ty);
    return ty->getStructName();
  }
}}

namespace sprite { namespace llvm { namespace types
{
  type int_(size_t numBits)
  {
    auto & cxt = scope::current_context();
    return type(IntegerType::get(cxt, numBits));
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
            "unsupported floating-point width (" + std::to_string(numBits) +
            " bits): expected 32/64/128 bits."
          );
      }
    }
  }

  type float_()
  {
    auto & cxt = scope::current_context();
    auto const p = Type::getFloatTy(cxt);
    return type(reinterpret_cast<FPType*>(p));
  }

  type double_()
  {
    auto & cxt = scope::current_context();
    auto const p = Type::getDoubleTy(cxt);
    return type(reinterpret_cast<FPType*>(p));
  }

  type longdouble()
  {
    auto & cxt = scope::current_context();
    auto const p = Type::getFP128Ty(cxt);
    return type(reinterpret_cast<FPType*>(p));
  }

  type void_()
  {
    auto & cxt = scope::current_context();
    return type(Type::getVoidTy(cxt));
  }

  #ifdef TEMPORARILY_DISABLED
  type label()
  {
    auto & cxt = scope::current_context();
    return type(Type::getLabelTy(cxt));
  }
  #endif

  type struct_(std::vector<type> const & elements)
  {
    auto & cxt = scope::current_context();
    std::vector<Type*> tmp;
    for(auto e: elements)
    {
      if(!::llvm::StructType::isValidElementType(e.ptr()))
        throw type_error("invalid struct element type.");
      tmp.emplace_back(e.ptr());
    }
    return type(StructType::get(cxt, tmp));
  }

  type struct_(std::string const & name)
  {
    module const mod = scope::current_module();
    StructType * ST = mod->getTypeByName(name);
    if(!ST)
      ST = StructType::create(mod.context(), name);
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
    ST->setBody(body, /*isPacked*/ false);
    return ty;
  }
}}}
