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

  // Variable
  inline Node * Variable::rvalue() const
  {
    if(!this->guards.empty())
      return this->guarded_rvalue();
    if(!this->target)
      return nullptr; // unassigned variable (forward reference)
    assert(this->target.kind == 'p');
    return *this->target;
  }
}
