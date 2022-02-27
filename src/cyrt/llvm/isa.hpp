#pragma once
#include "cyrt/llvm/type.hpp"
#include "cyrt/llvm/value.hpp"
#include "boost/preprocessor/seq/enum.hpp"

namespace cyrt { namespace llvm
{
  // LLVM Type types.
  enum class TypeTy { BOOST_PP_SEQ_ENUM(SPRITE_LLVM_TYPES) };
  bool isa(type, TypeTy);
  TypeTy kind(type);

  // LLVM Value types.
  enum class ValueTy { BOOST_PP_SEQ_ENUM(SPRITE_LLVM_VALUES) };
  bool isa(value, ValueTy);
}}
