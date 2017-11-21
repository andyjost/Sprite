/**
 * @file
 * @brief Master include for the Sprite memory system.
 */

namespace sprite
{
  /**
   * @brief The Sprite memory manager.
   *
	 * To initialize the memory manager, an object of this type should be placed
	 * on the stack inside the main function.  @p top_of_stack is the address of
	 * a stack variable above that object.
   */
  struct MemoryManager
  {
    MemoryManager(void * top_of_stack);
  	~MemoryManager();
  };
}

