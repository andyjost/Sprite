#include <cassert>
#include <functional>
#include <iostream>
#include "sprite/graph/node.hpp"
#include "sprite/graph/show.hpp"
#include "sprite/graph/walk.hpp"
#include <unordered_map>

namespace
{
  using namespace sprite;

  struct ReprStringifier
  {
    ReprStringifier(std::ostream & os) : os(os) {}
    std::ostream & os;
    std::unordered_set<void *> memo;

    static void callback(void * static_data, void * id)
    {
      auto self = (ReprStringifier *)(static_data);
      self->os << '>';
      self->memo.erase(id);
    }

    void stringify(Cursor expr)
    {
      bool first = true;
      for(auto && state=walk(expr, nullptr, this, &callback); state; ++state)
      {
        auto && cur = state.cursor();
        if(first) first = false; else this->os << ' ';
        switch(cur.kind)
        {
          case 'i': os << cur->ub_int;   continue;
          case 'f': os << cur->ub_float; continue;
          case 'c': os << cur->ub_char;  continue;
        }
        void * id = cur.id();
        if(!this->memo.insert(id).second)
          this->os << "...";
        else
        {
          this->os << '<';
          if(cur.info()->flags & OPERATOR)
            os << '(' << cur.info()->name << ')';
          else
            os << cur.info()->name;
          state.push(id);
        }
      }
    }

    // void format_node(Cursor cur)
    // {
    //   assert(cur.kind == 'p');
    //   auto * info = cur.info();
    //   // switch(info->tag)
    //   // {
    //   //   case T_FAIL: os << "failed";                   return true;
    //   //   case T_FREE: os << '_' << NodeU{cur}.free.cid; return true;
    //   //   case T_FWD:  return format_node(os, NodeU{cur}.fwd.target);
    //   // }
    //   // Head.
    //   if(info->flags & OPERATOR)
    //     os << '(' << info->name << ')';
    //   else
    //     os << info->name;
    //   // Successors.
    //   // bool const subexpr_is_outer = info->flags & (LIST_TYPE | TUPLE_TYPE);
    //   // bool const is_partial = info->flags & PARTIAL_TYPE;
    //   // for(index_type i=0; i<info->arity; ++i)
    //   // {
    //   //   os << ' ';
    //   //   this->stringify(cur->node.successor(i));
    //   // }
    //   // return true;
    // }
  };

  // bool litnormal_format(Cursor cur, std::ostream & os)
  // {
  //   switch(cur.kind)
  //   {
  //     case 'i': os << cur->ub_int;   return true;
  //     case 'f': os << cur->ub_float; return true;
  //     case 'c': os << cur->ub_char;  return true;
  //   }
  //   return false;
  // }

  // bool litunboxed_format(Cursor cur, std::ostream & os)
  // {
  //   switch(cur.kind)
  //   {
  //     case 'i': os << cur->ub_int << '#';   return true;
  //     case 'f': os << cur->ub_float << '#'; return true;
  //     case 'c': os << cur->ub_char << '#';  return true;
  //   }
  //   return false;
  // }
}

namespace sprite
{
  void show(std::ostream & os, Cursor cur, ShowStyle sty)
  {
    auto && stringifier = ReprStringifier(os);
    return stringifier.stringify(cur);
  }
}
