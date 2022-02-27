#pragma once
#include "cyrt/llvm/config.hpp"
#include "llvm/IR/DerivedTypes.h"

namespace cyrt { namespace llvm
{
  template<typename T, typename Policy> struct llvmobj;
  struct module;
  struct type;
  struct value;
  template<typename T=Constant> struct constobj;
  template<typename T=GlobalValue> struct globalobj;

  // Globals (anything the linker sees, even symbols marked private).
  using global = globalobj<GlobalValue>;
  using function = globalobj<Function>;
  using globalvar = globalobj<GlobalVariable>;

  // Values and references.
  // using value = valueobj<>;
  // using instruction = valueobj<Instruction>;
  // using switch_instruction = valueobj<SwitchInst>;
  // using metadata = valueobj<MDNode>;
  // struct label;
  // template<typename AddressType=value, typename ValueType=value>
  //   struct basic_reference;
  // using ref = basic_reference<>;

  // Constants.
  // using constant = constobj<>;
  // using constexpr_ = constobj<ConstantExpr>;
  // using nullptr_ = constobj<ConstantPointerNull>;
  // using constant_array = constobj<ConstantArray>;
  // using constant_fp = constobj<ConstantFP>;
  // using constant_int = constobj<ConstantInt>;
  // using constant_struct = constobj<ConstantStruct>;
  // using globalvaraddr = constobj<GlobalVariable>;
  // using block_address = constobj<BlockAddress>;


  // ==========================================================================
  // Constructs related to flags.
  // ==========================================================================

  #ifdef SPRITE3
  namespace aux
  {
    struct operator_flags;
    template<typename Arg> struct arg_with_flags;
  }

  // Convenience names.
  template<typename T>
  using typeobj_with_flags = aux::arg_with_flags<typeobj<T>>;

  template<typename T>
  using valueobj_with_flags = aux::arg_with_flags<valueobj<T>>;

  // Types with sign flags.
  using type_with_flags = typeobj_with_flags<Type>;
  using array_type_with_flags = typeobj_with_flags<ArrayType>;
  using integer_type_with_flags = typeobj_with_flags<IntegerType>;
  #endif

  // ==========================================================================
  // Support constructs.
  // ==========================================================================
  struct any_array_ref;
  struct any_tuple_ref;
  template<typename T, typename Extent=std::integral_constant<size_t,0>>
    struct array_ref;
}}
