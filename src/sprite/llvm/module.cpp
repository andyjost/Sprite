#include "sprite/llvm/module.hpp"


namespace sprite { namespace llvm
{
  ::llvm::LLVMContext & getContext()
  {
    static thread_local ::llvm::LLVMContext context;
    return context;
  }
}}
