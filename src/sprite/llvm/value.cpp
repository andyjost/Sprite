#include <boost/lexical_cast.hpp>
#include "llvm/ADT/SmallVector.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/GlobalAlias.h"
#include "llvm/IR/GlobalIFunc.h"
#include "llvm/IR/GlobalVariable.h"
#include "llvm/IR/InstrTypes.h"
#include "llvm/Support/raw_os_ostream.h"
#include "sprite/llvm/isa.hpp"
#include "sprite/llvm/module.hpp"
#include "sprite/llvm/value.hpp"

#include <iostream> // DEBUG

using namespace ::llvm;

namespace sprite { namespace llvm
{
  void value_custodian::onConstruct(llvmobj<Value, value_custodian> & h)
  {
    value const & val = static_cast<value const &>(h);
    // Hold the parent in the deleter to avoid early deletion.
    custodian<Value, value_deleter>::onConstruct(h, value_deleter(val.parent()));
  }

  void value_deleter::operator()(Value * px) const
  {
    if(!px)
      return;
    switch(px->getValueID())
    {
      #define HANDLE_MEMORY_VALUE(Name)     /* error */
      #define HANDLE_INLINE_ASM_VALUE(Name) /* error */
      #define HANDLE_METADATA_VALUE(Name)   /* error */
      #define HANDLE_GLOBAL_VALUE(Name)     HANDLE_VALUE(Name)
      #define HANDLE_INSTRUCTION(Name)      /* handled in default */
      #define HANDLE_FUNCTION(Name)         HANDLE_VALUE(Name)
      // If the handle to an unused value with no parent is destroyed, then it
      // can be deleted.
      #define HANDLE_VALUE(Name)                    \
          case Value::Name##Val:                    \
          {                                         \
            auto qx = static_cast<Name *>(px);      \
            if(!qx->getParent() && qx->use_empty()) \
              /*px->deleteValue()*/;                    \
            break;                                  \
          }                                         \
        /**/
      // Do not delete constant values (the LLVMContext owns them).
      #define HANDLE_CONSTANT(Name) case Value::Name##Val: break;
      #include "llvm/IR/Value.def"
      default:
        if(isa<Instruction>(px))
        {
          if(auto * qx = dyn_cast<Instruction>(px))
            if(!qx->getParent() && qx->use_empty())
              /*px->deleteValue()*/;
        }
        else
          throw internal_error("unknown value ID");
    }
  }

  value value::from_bool(bool v)
  {
    auto * TY = types::bool_().ptr();
    return v ? ConstantInt::getTrue(TY) : ConstantInt::getFalse(TY);
  }

  value value::from_int(int64_t v)
  {
    auto * TY = types::int_(64).ptr();
    return ConstantInt::getSigned(TY, v);
  }

  value value::from_double(double v)
  {
    auto * TY = types::double_().ptr();
    return ConstantFP::get(TY, v);
  }

  literal_value value::constexpr_value() const
  {
    if(auto * IV = dyn_cast_or_null<ConstantInt>(ptr()))
    {
      assert(IV->getBitWidth() <= 64);
      int64_t const value = IV->getValue().getLimitedValue();
      return value;
    }
    else if(auto * FV = dyn_cast_or_null<ConstantFP>(ptr()))
    {
      double const value = FV->getValueAPF().convertToDouble();
      return value;
    }
    else
    {
      throw value_error(
          boost::format("cannot get constexpr value from this '%s' object")
              % typeof_(*this)
        );
    }
  }

  static module parent_to_handle(Module * m) { return module(m); }
  static value parent_to_handle(Value * v) { return value(v); }

  value::parent_type value::parent() const
  {
    if(ptr())
    {
      switch(ptr()->getValueID())
      {
        #define HANDLE_MEMORY_VALUE(Name)     /* nothing */
        #define HANDLE_INLINE_ASM_VALUE(Name) /* nothing */
        #define HANDLE_METADATA_VALUE(Name)   /* nothing */
        #define HANDLE_GLOBAL_VALUE(Name)     HANDLE_VALUE(Name)
        #define HANDLE_INSTRUCTION(Name)      /* handled in default */
        #define HANDLE_FUNCTION(Name)         HANDLE_VALUE(Name)
        #define HANDLE_VALUE(Name)                      \
            case Value::Name##Val:                      \
            {                                           \
              auto qx = static_cast<Name *>(ptr());     \
              return parent_to_handle(qx->getParent()); \
              break;                                    \
            }                                           \
          /**/
        // Do not delete constant values (the LLVMContext owns them).
        #define HANDLE_CONSTANT(Name) case Value::Name##Val: break;
        #include "llvm/IR/Value.def"
        default:
          if(isa<Instruction>(ptr()))
          {
            if(auto * qx = dyn_cast<Instruction>(ptr()))
              return parent_to_handle(qx->getParent());
          }
      }
    }
    return boost::none;
  }

  value cast(value v, type dst_ty, bool src_is_signed, bool dst_is_signed)
  {
    auto src_ty = typeof_(v);
    if(!is_castable(src_ty, dst_ty))
    {
      throw type_error(
          boost::format("cannot cast '%s' to '%s'") % src_ty % dst_ty
        );
    }
    if(src_ty == dst_ty)
      return v;
    auto const castop = CastInst::getCastOpcode(v, src_is_signed, dst_ty, dst_is_signed);
    if(auto * C = dyn_cast<Constant>(v.ptr()))
      return ConstantExpr::getCast(castop, C, dst_ty);
    else
      return CastInst::Create(castop, v, dst_ty);
  }

  value bitcast(value v, type dst_ty)
  {
    auto src_ty = typeof_(v);
    auto const castop = Instruction::BitCast;
    if(!is_bitcastable(src_ty, dst_ty))
    {
      throw type_error(
          boost::format("cannot bitcast '%s' to '%s'") % src_ty % dst_ty
        );
    }
    if(src_ty == dst_ty)
      return v;
    if(auto * C = dyn_cast<Constant>(v.ptr()))
      return ConstantExpr::getCast(castop, C, dst_ty);
    else
      return CastInst::Create(castop, v, dst_ty);
  }

  value::value(boost::none_t)
    : value(UndefValue::get(types::void_()))
  {}

  LinkageTypes value::getLinkage() const
  {
    if(auto * GV = dyn_cast_or_null<GlobalValue>(ptr()))
      return GV->getLinkage();
    else
      throw type_error("expected a GlobalValue");
  }

  void value::setLinkage(LinkageTypes linkage)
  {
    if(auto * GV = dyn_cast_or_null<GlobalValue>(ptr()))
      return GV->setLinkage(linkage);
    else
      throw type_error("expected a GlobalValue");
  }

  bool value::getIsConst() const
  {
    if(auto * GV = dyn_cast_or_null<GlobalVariable>(ptr()))
      return GV->isConstant();
    else
      throw type_error("expected a GlobalVariable");
  }

  void value::setIsConst(bool is_const)
  {
    if(auto * GV = dyn_cast_or_null<GlobalVariable>(ptr()))
      return GV->setConstant(is_const);
    else
      throw type_error("expected a GlobalVariable");
  }

  value value::getInitializer() const
  {
    if(auto * GV = dyn_cast_or_null<GlobalVariable>(ptr()))
      if(GV->hasInitializer())
        return GV->getInitializer();
      else
        return value(nullptr);
    else
      throw type_error("expected a GlobalVariable");
  }

  void value::setInitializer(value init)
  {
    if(auto * GV = dyn_cast_or_null<GlobalVariable>(ptr()))
      if(auto * C = dyn_cast_or_null<Constant>(init.ptr()))
        return GV->setInitializer(C);
      else
        type_error("initializer is not a constant");
    else
      throw type_error("expected a GlobalVariable");
  }

  type typeof_(value v) { return type(v->getType()); }

  value null_value(type ty)
  {
    switch(kind(ty))
    {
      case TypeTy::IntegerType:
      case TypeTy::FPType:
      case TypeTy::ArrayType:
      case TypeTy::StructType:
      case TypeTy::VectorType:
      case TypeTy::PointerType:  return Constant::getNullValue(ty);
      case TypeTy::FunctionType:
      case TypeTy::VoidType:     return UndefValue::get(ty);
      default:
        throw type_error(
            boost::format("cannot create a null value of type '%s'") % ty
          );
    }
  }

  void value::erase()
  {
    if(auto * GV = dyn_cast_or_null<GlobalVariable>(ptr()))
      GV->removeFromParent();
    else
      throw internal_error("unhandled type: "); // FIXME
  }

  value operator+(value lhs, value rhs)
  {
    return lhs; // FIXME
  }
}}
