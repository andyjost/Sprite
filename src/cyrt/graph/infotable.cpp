#include "cyrt/graph/infotable.hpp"
#include <sstream>

namespace cyrt
{
  void showptr(std::ostream & os, void const * px)
  {
    if(px)
      os << px;
    else
      os << "nullptr";
  }

  std::string InfoTable::repr() const
  {
    std::stringstream ss;
    ss << "InfoTable("
          "name=\""     << this->name          << "\", "
          "arity="      << this->arity         << ", "
          "tag="        << this->tag           << ", "
          "flags="      << (int) this->flags   << ", "
          "step=";
    showptr(ss, (void *) this->step);
    ss << ", "
          "type=";
    if(this->type)
    {
      ss << '"' << this->type->name << "\" at ";
      showptr(ss, this->type);
    }
    else
      showptr(ss, this->type);
    ss << ", "
          "alloc_size=" << this->alloc_size    << ", "
          "format=\""   << this->format        << "\""
          ")";
    return ss.str();
  }
}
