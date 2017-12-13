#include <boost/lexical_cast.hpp>
#include "llvm/ADT/SmallVector.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/InstrTypes.h"
#include "llvm/Support/raw_os_ostream.h"
#include "sprite/llvm/isa.hpp"
#include "sprite/llvm/value.hpp"

using namespace ::llvm;

namespace sprite { namespace llvm
{
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
    if(auto * IV = dyn_cast<ConstantInt>(ptr()))
    {
      assert(IV->getBitWidth() <= 64);
      int64_t const value = IV->getValue().getLimitedValue();
      return value;
    }
    else if(auto * FV = dyn_cast<ConstantFP>(ptr()))
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

  value cast_(value v, type dst_ty, bool src_is_signed, bool dst_is_signed)
  {
    auto src_ty = typeof_(v);
    if(!CastInst::isCastable(src_ty, dst_ty))
    {
      throw type_error(
          boost::format("cannot cast '%s' to '%s'") % src_ty % dst_ty
        );
    }
    auto const castop = CastInst::getCastOpcode(v, src_is_signed, dst_ty, dst_is_signed);
    // if(!CastInst::castIsValid(castop, v, dst_ty))
    //   throw internal_error();
    return CastInst::Create(castop, v, dst_ty);
  }

  value bitcast_(value v, type dst_ty)
  {
    auto src_ty = typeof_(v);
    if(!CastInst::isBitCastable(src_ty, dst_ty))
    {
      throw type_error(
          boost::format("cannot bitcast '%s' to '%s'") % src_ty % dst_ty
        );
    }
    auto const castop = Instruction::BitCast;
    // if(!CastInst::castIsValid(castop, v, dst_ty))
    //   throw internal_error();
    return CastInst::Create(castop, v, dst_ty);
  }

  value::value(boost::none_t)
    : value(UndefValue::get(types::void_()))
  {}

  // bool operator==(value lhs, value rhs)
  // bool operator!=(value lhs, value rhs);

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

  value operator+(value lhs, value rhs)
  {
    return lhs; // FIXME
  }
}}
