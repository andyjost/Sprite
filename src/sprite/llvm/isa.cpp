#include "sprite/llvm/config.hpp"
#include "sprite/llvm/fwd.hpp"
#include "sprite/llvm/isa.hpp"
#include "llvm/IR/Constants.h"
#include "llvm/IR/Instruction.h"
#include "llvm/IR/Operator.h"
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

