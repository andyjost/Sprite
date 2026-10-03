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

  // The successor of a variable.  The realpath runs from the root of the
  // step, so the path of this variable comes first: Scan::push walks it from
  // the root when the successor is head-normalized.
  inline Variable Variable::operator[](index_type pos) const
  {
    Variable tmp(this->target, pos);
    tmp.realpath.insert(
        tmp.realpath.begin(), this->realpath.begin(), this->realpath.end()
      );
    tmp.guards.insert(tmp.guards.end(), this->guards.begin(), this->guards.end());
    return tmp;
  }

  inline Variable Cursor::operator[](index_type pos) const
    { return Variable(*this, pos); }
}
