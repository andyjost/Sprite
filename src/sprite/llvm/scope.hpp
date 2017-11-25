#pragma once
#include "sprite/llvm/fwd.hpp"
#include <memory>

namespace sprite { namespace llvm
{
  /**
   * @brief Used during function creation to specify which basic block is
   * currenty under construction.
   *
   * A basic block is created by defining a new lexical block, placing an
   * instance of Scope inside it, and, finally, specifying the commands as a
   * series of simple statements.
   *
   * @snippet hello_world.cpp Using scope
   */
  class scope
  {
  public:
    // Normal object management.  Movable but not copyable or
    // stack-constructible.
    scope(scope && arg);
    scope(scope const &) = delete;
    scope & operator=(scope const &) = delete;
    void * operator new(size_t) = delete;
    void operator delete(void *) = delete;
    ~scope();

    // Scope creation.
    scope(module);
    #ifdef TEMPORARILY_DISABLED
    scope(function);
    scope(label);
    #endif

    // Scope access.
    static module current_module();
    #ifdef TEMPORARILY_DISABLED
    static function current_function();
    static label current_label();

    /**
     * @brief Replaces the current label with a new one, following a branch
     * instruction.
     */
    static void update_current_label_after_branch(label const &);

    /// Sets the default continuation.
    static void set_continuation(
        label const & src, label const & tgt, MdBranchType = MD_CONT
      );
    #endif

    // The context comes from the current module, but exposing it in this way
    // may allow some compilation units to avoid a dependency on module.hpp.
    static ::llvm::LLVMContext & current_context();

    struct frame;

  private:

    std::unique_ptr<frame> m_frame;
  };
}}
