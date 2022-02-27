#pragma once
#include "cyrt/backend/config.hpp"
#include "cyrt/backend/core/constant.hpp"
#include "cyrt/backend/core/scope.hpp"
#include "cyrt/backend/core/value.hpp"
#include "cyrt/backend/support/exceptions.hpp"
#include "cyrt/backend/support/type_traits.hpp"
#include "llvm/IR/BasicBlock.h"
#include <functional>

namespace cyrt { namespace backend
{
  /// Represents a branch target.
  struct label : valueobj<llvm::BasicBlock>
  {
    using valueobj<llvm::BasicBlock>::valueobj;

    /// Creates a new BasicBlock in the current function scope.
    explicit label(twine const & name = "")
      : valueobj<llvm::BasicBlock>(init(name)) // , m_next(nullptr)
    {}

    /// Creates a new BasicBlock and fills it by calling the function.
    // Implicit conversion is allowed.
    template<
        typename T
      , typename = typename std::enable_if<
            is_code_block_specifier<T>::value
          >::type
      >
    explicit label(T && body, twine const & name = "")
      : valueobj<llvm::BasicBlock>(init(name))
    {
      scope _ = *this;
      body();
    }

    /// Returns the label address.
    block_address operator&() const
      { return block_address(SPRITE_APICALL(llvm::BlockAddress::get(ptr()))); }

  private:

    template<typename T> friend class globalobj;
    llvm::BasicBlock * init(twine const &);
  };

  /**
   * @brief Used to accept code block specifiers as function arguments.
   *
   * Accepting an argument of type label && has the effect of creating a new
   * code block and filling it before the function call is made.  Sometimes a
   * delay is necessary, such as when the called function will provide a new
   * (function) scope in which to evaluate the code block.
   */
  using codeblock = std::function<void()>;
}}

