#include "sprite/llvm/config.hpp"
#include "sprite/llvm/fwd.hpp"
#include "sprite/llvm/isa.hpp"
#include "llvm/IR/Constants.h"
#include "llvm/IR/Instruction.h"
#include "llvm/IR/Operator.h"
#include "llvm/IR/Type.h"
#include <boost/preprocessor/enum.hpp>
#include <boost/preprocessor/seq/elem.hpp>
#include <boost/preprocessor/seq/size.hpp>
#include <functional>
#include <unordered_map>

namespace sprite { namespace llvm
{
  bool isa(type ty, TypeTy tyty)
  {
    static std::unordered_map<TypeTy, std::function<bool(type)>> table = {
      #define EXPR(name) {TypeTy::name, [](type ty) { return isa<name>(ty.ptr());}}
      #define OP(z,i,_) EXPR(BOOST_PP_SEQ_ELEM(i,SPRITE_LLVM_TYPES))
      BOOST_PP_ENUM(BOOST_PP_SEQ_SIZE(SPRITE_LLVM_TYPES), OP,)
      #undef OP
      #undef EXPR
      };
    return table.at(tyty)(ty);
  }

  TypeTy kind(type ty)
  {
    using ::llvm::Type;
    switch(ty->getTypeID())
    {
      case Type::VoidTyID:      return TypeTy::VoidType;
      case Type::HalfTyID:
      case Type::FloatTyID:
      case Type::DoubleTyID:
      case Type::X86_FP80TyID:
      case Type::FP128TyID:
      case Type::PPC_FP128TyID: return TypeTy::FPType;
      case Type::IntegerTyID:   return TypeTy::IntegerType;
      case Type::FunctionTyID:  return TypeTy::FunctionType;
      case Type::StructTyID:    return TypeTy::StructType;
      case Type::ArrayTyID:     return TypeTy::ArrayType;
      case Type::PointerTyID:   return TypeTy::PointerType;
      case Type::VectorTyID:    return TypeTy::VectorType;
      case Type::LabelTyID:
      case Type::MetadataTyID:
      case Type::X86_MMXTyID:
      case Type::TokenTyID:     throw type_error("bad type kind");
      default:                  throw internal_error();
    }
  }

  bool isa(value val, ValueTy valty)
  {
    using namespace llvm;
    static std::unordered_map<ValueTy, std::function<bool(value)>> table = {
      #define EXPR(name) {ValueTy::name, [](value val) { return isa<name>(val.ptr());}}
      #define OP(z,i,_) EXPR(BOOST_PP_SEQ_ELEM(i,SPRITE_LLVM_VALUES))
      BOOST_PP_ENUM(BOOST_PP_SEQ_SIZE(SPRITE_LLVM_VALUES), OP,)
      #undef OP
      #undef EXPR
      };
    return table.at(valty)(val);
  }
}}

