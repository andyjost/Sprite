#pragma once
#include "curryrt/dynload.hpp"
#include "curryrt/module.hpp"

namespace curryrt
{
  // Private, portable translation product; raise on any layout change.
  constexpr uint32_t IMAGE_VERSION = 12;
  std::unique_ptr<ModuleBOM> load_image(Module &, std::string const &,
      std::string const & expected_header = "", bool attach_code = true);
}
