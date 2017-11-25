/**
 * @file
 * @brief Contains common bootstrapping code for the Sprite LLVM module.
 */

#pragma once
#include "sprite/misc/typenames.hpp"
#include "llvm/IR/Type.h"
#include <array>

/**
 * @brief Calls to the LLVM C++-API are wrapped in this macro.
 *
 * If the program is compiled with @p -MSPRITE_SHOW_LLVM_API_CALLS, then the
 * calls are printed to the output.
 */
// #define SPRITE_SHOW_LLVM_API_CALLS
#ifdef SPRITE_SHOW_LLVM_API_CALLS
#include <iostream>
namespace sprite { namespace llvm { namespace aux {
  inline std::string _location(std::string const & file, size_t line)
    { return " at " + file + ":" + std::to_string(line) + "\n"; }
}}}
#define SPRITE_APICALL(...)                                     \
    (                                                           \
        (std::cout << "LLVM-API CALL: " << #__VA_ARGS__         \
          << ::sprite::llvm::aux::_location(__FILE__, __LINE__) \
          )                                                     \
      , __VA_ARGS__                                             \
      )                                                         \
  /**/
#else
#define SPRITE_APICALL(...) __VA_ARGS__
#endif

/// Defines the metadata used to tag implicit continuation targets added by sprite.
#define SPRITE_IMPLIED_METADATA "sprite.implied"

namespace sprite { namespace llvm
{
  /// Metadata used to indicate how an implicit branch is used.
  enum MdBranchType {
      MD_CONT /// The associated implied branch instruction is a continuation.
    , MD_LOOP /// The associated implied branch instruction is a loopback.
  };
}}

/// Defines the metadata used to tag loop back edges.
#define SPRITE_LOOP_METADATA "sprite.loop"

// Forward-declare some LLVM types that will be used.
namespace llvm
{
  // Modules.
  class Module;
  class LLVMContext;

  // Types.
  class Type;
  class ArrayType;
  class FunctionType;
  class IntegerType;
  class PointerType;
  class StructType;

  // Constants.
  class Constant;
  class ConstantAggregateZero;
  class ConstantArray;
  class ConstantExpr;
  class ConstantFP;
  class ConstantInt;
  class ConstantPointerNull;
  class ConstantStruct;
  class BlockAddress;

  // Values.
  class Value;
  class BasicBlock;
  class Function;
  class GlobalValue;
  class GlobalVariable;
  class MDNode;
  class Instruction;
  class SwitchInst;

  // ADTs.
  class StringRef;
  class Twine;
}

namespace sprite { namespace llvm
{
  // A unique type for use with enable_if.
  struct En_ {};

  // Modules.
  using ::llvm::Module;
  using ::llvm::LLVMContext;

  // Types.
  using ::llvm::Type;
  using ::llvm::ArrayType;
  using ::llvm::FunctionType;
  using ::llvm::IntegerType;
  using ::llvm::PointerType;
  using ::llvm::StructType;

  SPRITE_SPECIALIZE_TYPENAME(Type)
  SPRITE_SPECIALIZE_TYPENAME(ArrayType)
  SPRITE_SPECIALIZE_TYPENAME(FunctionType)
  SPRITE_SPECIALIZE_TYPENAME(IntegerType)
  SPRITE_SPECIALIZE_TYPENAME(PointerType)
  SPRITE_SPECIALIZE_TYPENAME(StructType)

  /// Overload typename_ to return human-readable LLVM type names.
  std::string typename_(::llvm::Type const &);

  /**
   * @brief Represents a floating-point type.
   *
   * LLVM does not define a type class for floating-point types as it does for
   * other types such as @p IntegerType.  Instead, floating-point types are
   * handled using the generic class @p Type.  That poses a real problem for @p
   * typeobj, which uses the type of the wrapped object to activate the
   * relevant operators.
   *
   * To work around that problem, this type is invented.  When a floating-point
   * type is produced, this library will cast its <tt>Type *</tt> to a
   * <tt>FPType *</tt> before applying the wrapping.  In that way, it is
   * possible to carry the type information.  When the type is ultimately used
   * (by an LLVM API function), it will be converted back to <tt>Type *</tt>,
   * since, obviously, no function defined by LLVM accepts this type.
   */
  struct FPType : ::llvm::Type
  {
    static bool classof(Type const * tp)
      { return tp->isFloatingPointTy(); }
  };

  SPRITE_SPECIALIZE_TYPENAME(FPType)

  // Constants.
  using ::llvm::Constant;
  using ::llvm::ConstantAggregateZero;
  using ::llvm::ConstantArray;
  using ::llvm::ConstantExpr;
  using ::llvm::ConstantFP;
  using ::llvm::ConstantInt;
  using ::llvm::ConstantPointerNull;
  using ::llvm::ConstantStruct;
  using ::llvm::BlockAddress;

  SPRITE_SPECIALIZE_TYPENAME(ConstantAggregateZero);
  SPRITE_SPECIALIZE_TYPENAME(ConstantArray);
  SPRITE_SPECIALIZE_TYPENAME(ConstantExpr);
  SPRITE_SPECIALIZE_TYPENAME(ConstantFP);
  SPRITE_SPECIALIZE_TYPENAME(ConstantInt);
  SPRITE_SPECIALIZE_TYPENAME(ConstantPointerNull);
  SPRITE_SPECIALIZE_TYPENAME(ConstantStruct);
  SPRITE_SPECIALIZE_TYPENAME(BlockAddress);

  // Values.
  using ::llvm::Value;
  using ::llvm::BasicBlock;
  using ::llvm::Function;
  using ::llvm::GlobalValue;
  using ::llvm::GlobalVariable;
  using ::llvm::MDNode;
  using ::llvm::Instruction;
  using ::llvm::SwitchInst;

  SPRITE_SPECIALIZE_TYPENAME(Value)
  SPRITE_SPECIALIZE_TYPENAME(BasicBlock)
  SPRITE_SPECIALIZE_TYPENAME(Function)
  SPRITE_SPECIALIZE_TYPENAME(GlobalValue)
  SPRITE_SPECIALIZE_TYPENAME(GlobalVariable)
  SPRITE_SPECIALIZE_TYPENAME(Instruction)
  SPRITE_SPECIALIZE_TYPENAME(SwitchInst)
  SPRITE_SPECIALIZE_TYPENAME(MDNode)

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
}}
