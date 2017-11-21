#include "memory.hpp"
#include "memory/cymps.h"

namespace sprite
{
  MemoryManager::MemoryManager(void * top_of_stack)
    { init_memory_system(top_of_stack); }

	MemoryManager::~MemoryManager() { destroy_memory_system(); }
}
