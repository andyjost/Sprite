#include "cyrt/llvm/config.hpp"
#include "llvm/Support/raw_ostream.h"

namespace cyrt { namespace llvm
{
  std::string typename_(Type const & tp)
  {
    std::string buf;
    ::llvm::raw_string_ostream sbuf(buf);
    sbuf << tp;
    return sbuf.str();
  }
}}
