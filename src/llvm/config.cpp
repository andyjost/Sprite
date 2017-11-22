#include "sprite/llvm/config.hpp"
#include "llvm/Support/raw_ostream.h"

namespace sprite { namespace llvm
{
  std::string typename_(Type const & tp)
  {
    std::string buf;
    ::llvm::raw_string_ostream sbuf(buf);
    sbuf << tp;
    return sbuf.str();
  }
}}
