#pragma once
#include "curryrt/dynload.hpp"
#include "curryrt/module.hpp"

namespace curryrt
{
  // Private translation product; raise on layout or translation changes.
  constexpr uint32_t IMAGE_VERSION = 15;
  std::unique_ptr<ModuleBOM> load_image(Module &, std::string const &,
      std::string const & expected_header = "", bool attach_code = true,
      ModuleRegistry const * references = nullptr);
}
