#include "curryrt/smallvec.hpp"
#include <new>

namespace curryrt
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
