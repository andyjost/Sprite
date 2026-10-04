#include "cyrt/smallvec.hpp"
#include <new>

namespace cyrt
{
  void * smallvec_alloc(size_t bytes)
  {
    return ::operator new(bytes);
  }

  void smallvec_free(void * block)
  {
    ::operator delete(block);
  }
}
