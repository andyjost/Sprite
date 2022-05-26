#pragma once

namespace cyrt
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

  inline Arg::Arg(Cursor const & value) : Arg(*value) {}

  inline Arg::Arg(Variable const & value) : Arg(value.rvalue()) {}

  inline Variable Variable::operator[](index_type pos) const
    { return Variable(this->target, pos); }

  inline Variable Cursor::operator[](index_type pos) const
    { return Variable(*this, pos); }
}
