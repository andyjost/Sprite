#pragma once

namespace sprite
{
  static_assert(sizeof(Arg) == sizeof(void *));

  // Arg
  template<typename T>
  inline Arg & Arg::operator=(T && value)
  {
    Arg tmp{std::forward<T>(value)};
    this->blob = tmp.blob;
    return *this;
  }

  // Cursor
  inline InfoTable const * Cursor::info() const
    { return arg && arg->head ? arg->head->info : nullptr; }
}
