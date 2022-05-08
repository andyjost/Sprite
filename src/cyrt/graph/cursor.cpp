#include "cyrt/graph/cursor.hpp"
#include "cyrt/graph/node.hpp"
#include "cyrt/graph/walk.hpp"
#include <limits>
#include <sstream>

namespace cyrt
{
  std::string Arg::repr() const
  {
    std::stringstream ss;
    ss << "<Arg \"" << this->blob << "\" at " << this << ">";
    return ss.str();
  }

  std::string Cursor::str() const
  {
    return this->str(SUBST_FREEVARS);
  }

  std::string Cursor::str(SubstFreevars subst_freevars, ShowMonitor * monitor) const
  {
    std::stringstream ss;
    if(this->arg)
    {
      switch(this->kind)
      {
        case 'p': ss << this->arg->node->str(subst_freevars, monitor); break;
        case 'i': ss << this->arg->ub_int;                             break;
        case 'f': ss << this->arg->ub_float;                           break;
        case 'c': ss << "'" << this->arg->ub_char << "'";              break;
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

  std::string Cursor::str(Variable const & var) const
  {
    return this->str(var, SUBST_FREEVARS);
  }

  static size_t constexpr MAX = std::numeric_limits<size_t>::max();

  struct GetSpan : ShowMonitor
  {
    GetSpan(Variable const & watched) : watched(&watched) {}
    Variable const * watched;
    size_t begin=MAX, end=MAX;

    explicit operator bool() const { return this->begin != MAX && this->end != MAX; }

    void enter(std::ostream & os, Walk2 const * walk, char context) override
    {
      if(walk->path() == watched->realpath)
      {
        assert(walk->cursor() == this->watched->target);
        this->begin = os.tellp();
      }
    }

    void exit(std::ostream & os, Walk2 const * walk, char context) override
    {
      if(this->begin != MAX && this->end == MAX)
        if(walk->at_terminus(watched->realpath))
          this->end = os.tellp();
    }
  };

  std::string Cursor::str(Variable const & var, SubstFreevars subst_freevars) const
  {
    GetSpan monitor{var};
    std::stringstream ss;
    ss << this->str(subst_freevars, &monitor);
    if(!monitor)
      throw std::invalid_argument("position not found");
    size_t len = ss.tellp();
    ss << "\n";
    for(size_t i=0; i<len; ++i)
    {
      if(i==monitor.end)
        break;
      ss << (i<monitor.begin ? ' ' : '~');
    }
    ss << '\n';
    for(size_t i=0; i<len; ++i)
    {
      if(i==monitor.begin)
        break;
      ss << ' ';
    }
    ss << " path: ";
    show(ss, var.realpath);
    ss << ", guards: ";
    show(ss, var.guards);
    return ss.str();

  void show(std::ostream &, Cursor, ShowStyle, ShowMonitor * = nullptr);
  }

  std::string Variable::str() const
  {
    return this->str(SUBST_FREEVARS);
  }

  std::string Variable::str(SubstFreevars subst_freevars) const
  {
    std::stringstream ss;
    ss << "path: ";
    show(ss, this->realpath);
    ss << ", guards: ";
    show(ss, this->guards);
    ss << ", target: " << this->target.str(subst_freevars);
    return ss.str();
  }
}
