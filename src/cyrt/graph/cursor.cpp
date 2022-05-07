#include "cyrt/graph/cursor.hpp"
#include "cyrt/graph/node.hpp"
#include <sstream>

namespace cyrt
{
  std::string Arg::repr() const
  {
    std::stringstream ss;
    ss << "<Arg \"" << this->blob << "\" at " << this << ">";
    return ss.str();
  }

  std::string Cursor::str(SubstFreevars subst_freevars) const
  {
    std::stringstream ss;
    if(this->arg)
    {
      switch(this->kind)
      {
        case 'p': ss << this->arg->node->str(subst_freevars); break;
        case 'i': ss << this->arg->ub_int;                    break;
        case 'f': ss << this->arg->ub_float;                  break;
        case 'c': ss << "'" << this->arg->ub_char << "'";     break;
        default :;
      }
    }
    return ss.str();
  }

  std::string Cursor::repr() const
  {
    std::stringstream ss;
    ss << "<Cursor " << this->arg << ": ";
    if(this->arg)
    {
      switch(this->kind)
      {
        case 'p': ss << "Node "     << this->arg->node;           break;
        case 'i': ss << "ub_int "   << this->arg->ub_int;         break;
        case 'f': ss << "ub_float " << this->arg->ub_float;       break;
        case 'c': ss << "ub_char '" << this->arg->ub_char << "'"; break;
        case 'x': ss << "blob "     << this->arg->blob;           break;
        case 'u': ss << "nothing";                                break;
        default : ss << "error";                                  break;
      }
    }
    ss << ">";
    return ss.str();
  }
}