#pragma once
#include "sprite/llvm/config.hpp"

namespace sprite { namespace backend
{
  class module;
  template<typename T> class object;
  template<typename T=Type> class typeobj;
  template<typename T=Value> class valueobj;
  template<typename T=Constant> class constobj;
  template<typename T=GlobalValue> class globalobj;

  // Types.
  using type = typeobj<>;
  using array_type = typeobj<ArrayType>;
  using integer_type = typeobj<IntegerType>;
  using function_type = typeobj<FunctionType>;
  using fp_type = typeobj<FPType>;
  using pointer_type = typeobj<PointerType>;
  using struct_type = typeobj<StructType>;

  // Globals (anything the linker sees, even symbols marked private).
  using global = globalobj<GlobalValue>;
  using function = globalobj<Function>;
  using globalvar = globalobj<GlobalVariable>;

  // Values and references.
  using value = valueobj<>;
  using instruction = valueobj<Instruction>;
  using switch_instruction = valueobj<SwitchInst>;
  using metadata = valueobj<MDNode>;
  struct label;
  template<typename AddressType=value, typename ValueType=value>
    struct basic_reference;
  using ref = basic_reference<>;

  // Constants.
  using constant = constobj<>;
  using constexpr_ = constobj<ConstantExpr>;
  using nullptr_ = constobj<ConstantPointerNull>;
  using constant_array = constobj<ConstantArray>;
  using constant_fp = constobj<ConstantFP>;
  using constant_int = constobj<ConstantInt>;
  using constant_struct = constobj<ConstantStruct>;
  using globalvaraddr = constobj<GlobalVariable>;
  using block_address = constobj<llvm::BlockAddress>;


  // ==========================================================================
  // Constructs related to flags.
  // ==========================================================================

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

  // ==========================================================================
  // Support constructs.
  // ==========================================================================
  struct any_array_ref;
  struct any_tuple_ref;
  template<typename T, typename Extent=std::integral_constant<size_t,0>>
    struct array_ref;
}}
