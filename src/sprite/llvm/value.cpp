#include "llvm/ADT/SmallVector.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/InstrTypes.h"
#include "sprite/llvm/value.hpp"

using namespace ::llvm;

namespace sprite { namespace llvm
{
  value::value(int64_t v)
    : value(({
          auto * TY = types::int_(64).ptr();
          ConstantInt::getSigned(TY, v);
        }))
  {}

  value::value(double v)
    : value(({
          auto * TY = types::double_().ptr();
          ConstantFP::get(TY, v);
        }))
  {}

  std::string value::str() const
  {
    SmallVector<char, 64> buffer;
    if(auto * IV = dyn_cast<ConstantInt>(ptr()))
      IV->getValue().toString(buffer, /*radix*/ 10, /*signed*/ true);
    else if(auto * FV = dyn_cast<ConstantFP>(ptr()))
      FV->getValueAPF().toString(buffer);
    else
      return "<value?>";
    return std::string(&buffer[0], buffer.size());
  }

  value type::operator()(value v, bool src_is_signed, bool dst_is_signed) const
  {
    auto src_ty = typeof_(v);
    auto dst_ty = ptr();
    if(!CastInst::isCastable(src_ty, dst_ty))
    {
      throw type_error(
          boost::format("cannot cast '%s' to '%s'") % src_ty % dst_ty
        );
    }
    auto castop = CastInst::getCastOpcode(v, src_is_signed, dst_ty, dst_is_signed);
    if(auto * CV = dyn_cast<Constant>(v.ptr()))
      return value(ConstantExpr::getCast(castop, CV, dst_ty));
    else
    {
      throw type_error("not implemented");
      // CastInst::Create(castop, v.ptr(), dst_ty);
    }
  }

  // bool operator==(value lhs, value rhs);
  // bool operator!=(value lhs, value rhs);
  std::ostream & operator<<(std::ostream & os, value const & v)
    { return os << v.str(); }

  type typeof_(value v) { return type(v->getType()); }
}}
