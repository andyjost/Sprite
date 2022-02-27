/**
 * @file
 * @brief Defines a global variables list and configures MPS to scan it.
 */
#include <cassert>
#include <iostream>
#include <list>
#include <stdexcept>
#include "cyrt/gc/globals.h"
#include "cyrt/gc/defs.h"

extern "C"
{
  #include "mpsavm.h"  // for virtual memory arena
  #include "mpscamc.h" // for automatic mostly-copying pool
}

#define error(what) throw std::runtime_error(what)
#define ASADDR(addr) (*({mps_addr_t * tmp = (mps_addr_t*)(&addr); tmp;}))
#define ASOBJ(addr) (*({heapobj_t** tmp = (heapobj_t**)(&addr); tmp;}))
#define SIZE_BOUND (1<<16)
struct heapobj_t;

namespace
{
  static std::list<heapobj_t *> globals;
}

extern "C"
{
  mps_res_t globals_scan(mps_ss_t ss, void *, size_t)
  {
    MPS_SCAN_BEGIN(ss)
      for(heapobj_t *& obj: globals) FIX(obj);
    MPS_SCAN_END(ss);
    return MPS_RES_OK;
  }

  void globals_clear() { globals.clear(); }
}

