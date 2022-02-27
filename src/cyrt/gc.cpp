#include "cyrt/gc.hpp"
#include "cyrt/gc/cymps.h"

namespace cyrt
{
  MemoryManager::MemoryManager(void * top_of_stack)
    { init_memory_system(top_of_stack); }

	MemoryManager::~MemoryManager() { destroy_memory_system(); }
}
