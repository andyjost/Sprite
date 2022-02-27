/**
 * @file
 * @brief Contains common bootstrapping code for the Sprite LLVM module.
 */

#pragma once
#include <array>
#include "boost/preprocessor.hpp"
#include "llvm/IR/Type.h"
#include "cyrt/misc/typenames.hpp"

/**
 * @brief Calls to the LLVM C++-API are wrapped in this macro.
 *
 * If the program is compiled with @p -MSPRITE_SHOW_LLVM_API_CALLS, then the
 * calls are printed to the output.
 */
// #define SPRITE_SHOW_LLVM_API_CALLS
#ifdef SPRITE_SHOW_LLVM_API_CALLS
#include <iostream>
namespace cyrt { namespace llvm { namespace aux {
  inline std::string _location(std::string const & file, size_t line)
    { return " at " + file + ":" + std::to_string(line) + "\n"; }
}}}
#define SPRITE_APICALL(...)                                     \
    (                                                           \
        (std::cout << "LLVM-API CALL: " << #__VA_ARGS__         \
          << ::cyrt::llvm::aux::_location(__FILE__, __LINE__) \
          )                                                     \
      , __VA_ARGS__                                             \
      )                                                         \
  /**/
#else
#define SPRITE_APICALL(...) __VA_ARGS__
#endif

/// Defines the metadata used to tag implicit continuation targets added by cyrt.
#define SPRITE_IMPLIED_METADATA "cyrt.implied"

namespace cyrt { namespace llvm
{
  /// Metadata used to indicate how an implicit branch is used.
  enum MdBranchType {
      MD_CONT /// The associated implied branch instruction is a continuation.
    , MD_LOOP /// The associated implied branch instruction is a loopback.
  };
}}

/// Defines the metadata used to tag loop back edges.
#define SPRITE_LOOP_METADATA "cyrt.loop"

// Forward-declare some LLVM types that will be used.
namespace llvm
{
  // Modules.
  class Module;
  class LLVMContext;

  // Types.
  #define SPRITE_LLVM_TYPES \
      (Type)                \
      (ArrayType)           \
      (CompositeType)       \
      (FPType)              \
      (FunctionType)        \
      (IntegerType)         \
      (PointerType)         \
      (SequentialType)      \
      (StructType)          \
      (VectorType)          \
      (VoidType)            \
    /**/

  #define OP(r,_,name) class name;
  BOOST_PP_SEQ_FOR_EACH(OP,,SPRITE_LLVM_TYPES)
  #undef OP

  /// Extends llvm::isa for floating-point types.
  class FPType : public ::llvm::Type
  {
  public:
    static bool classof(Type const * tp)
      { return tp->isFloatingPointTy(); }
  };

  /// Extends llvm::isa for the void type.
  class VoidType : public ::llvm::Type
  {
  public:
    static bool classof(Type const * tp)
      { return tp->isVoidTy(); }
  };

  // Values.
  #define SPRITE_LLVM_VALUES       \
    (Value)                        \
    (Argument)                     \
    (BasicBlock)                   \
    (InlineAsm)                    \
    (MetadataAsValue)              \
    (User)                         \
      (Constant)                   \
        (BlockAddress)             \
        (ConstantAggregate)        \
          (ConstantArray)          \
          (ConstantStruct)         \
          (ConstantVector)         \
        (ConstantData)             \
          (ConstantAggregateZero)  \
          (ConstantDataSequential) \
            (ConstantDataArray)    \
            (ConstantDataVector)   \
          (ConstantFP)             \
          (ConstantInt)            \
          (ConstantPointerNull)    \
        (ConstantExpr)             \
        (GlobalValue)              \
          (Function)               \
          (GlobalVariable)         \
      (Instruction)                \
      (Operator)                   \
    /**/

  #define OP(r,_,name) class name;
  BOOST_PP_SEQ_FOR_EACH(OP,,SPRITE_LLVM_VALUES)
  #undef OP

  // Metadata.
  class MDNode;

  // ADTs.
  class StringRef;
  class Twine;
}

namespace cyrt { namespace llvm
{
  // A unique type for use with enable_if.
  struct En_ {};

  // Modules.
  using ::llvm::Module;
  using ::llvm::LLVMContext;
  using ::llvm::Type; // DEBUG

  // Bring the LLVM Types and Values into this namespace and specialize
  // typename_ to handle them.
  #define OP(r,_,name)                 \
      using ::llvm::name;              \
      SPRITE_SPECIALIZE_TYPENAME(name) \
    /**/
  BOOST_PP_SEQ_FOR_EACH(OP,,SPRITE_LLVM_TYPES SPRITE_LLVM_VALUES)
  #undef OP

  /// Overload typename_ to return human-readable LLVM type names.
  std::string typename_(::llvm::Type const &);

  // ADTs.
  using string_ref = ::llvm::StringRef;
  using twine = ::llvm::Twine;

  SPRITE_SPECIALIZE_TYPENAME(string_ref);
  SPRITE_SPECIALIZE_TYPENAME(twine);

  // Arbitrary-precision intrinsic types.
  using ::llvm::APInt;
  using ::llvm::APFloat;

  SPRITE_SPECIALIZE_TYPENAME(APInt);
  SPRITE_SPECIALIZE_TYPENAME(APFloat);

  using ::llvm::cast;
  using ::llvm::cast_or_null;
  using ::llvm::dyn_cast;
  using ::llvm::dyn_cast_or_null;
  using ::llvm::isa;
}}
