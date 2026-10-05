#include <cassert>
#include <cstring>
#include "cyrt/builtins.hpp"
#include "cyrt/graph/infotable.hpp"
#include <sstream>

namespace cyrt
{
  InfoTable::InfoTable(
      tag_type           tag
    , index_type         arity
    , index_type         alloc_size
    , flag_type          flags
    , char const *       name
    , char const *       format
    , stepfunc_type      step
    , DataType const *   type
    )
    : tag(tag), arity(arity), alloc_size(alloc_size), flags(flags)
    , name(name), format(format), step(step), type(type)
  {
    assert(tag >= E_ERROR);
    // It must be possible to overwrite any function with a FWD node.
    assert((tag != T_FUNC) || alloc_size >= sizeof(FwdNode));
    // The block of a node holds a word per successor, and one word at least.
    // The generated code relies on this when it writes a result into the
    // redex (Node::rewrite; see backends/cxx/compiler.py).  A pinned table
    // is exempt: its static object is a head alone (Node0), and such a node
    // is never a redex.  So is a pad table: a pad of one word fills the
    // slack of a block.  Arg is a word; the union is incomplete here.
    assert(
        (flags & F_PINNED) || tag == T_PAD
        || alloc_size >= sizeof(Head) + sizeof(void *) * (arity ? arity : 1)
      );
    assert(name);
    assert(std::strlen(name));
    assert(format);
    assert(std::strlen(format) == arity);
    // Functions and pinned nodes have a step value.
    assert(!step || ((tag == T_FUNC) || (flags & F_PINNED)));
    // All constructors and only constructors belong to a type.
    assert((tag >= T_CTOR) == bool(type));
  }

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
