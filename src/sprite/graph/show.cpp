#include <cassert>
#include <functional>
#include <iostream>
#include "sprite/builtins.hpp"
#include "sprite/graph/node.hpp"
#include "sprite/graph/show.hpp"
#include "sprite/graph/walk.hpp"
#include "sprite/inspect.hpp"
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
          if(cur.info()->flags == OPERATOR)
            os << '(' << cur.info()->name << ')';
          else
            os << cur.info()->name;
          state.push(id);
        }
      }
    }
  };

  struct StrStringifier
  {
    StrStringifier(std::ostream & os) : os(os) {}

    std::ostream & os;
    union Context
    {
      char value;
      void * p;
      // values:
      //     '\0'    top expression first term
      //     ' '     top expression non-first term
      //     '{'     parenthesized subexpr first term
      //     '}'     parenthesized subexpr non-first term
      //     '('     tuple first term
      //     ')'     tuple non-first term
      //     '['     square list item
      //     ']'     square list spine
      //     '!'     cons list item
      //     ':'     cons list spine
      //     '"'     string item
      //     '`'     string spine

      Context(char value) : value(value) {}
      Context(void * p) : p(p) {}
      operator void *() const { return this->p; }
    };

    static void callback(void * static_data, void * data)
    {
      auto self = (StrStringifier *)(static_data);
      switch(Context(data).value)
      {
        case '(':
        case ')': 
        case '{': 
        case '}': self->os << ')';
      }
    }

    void stringify(Cursor expr)
    {
      for(auto && state=walk(expr, nullptr, this, &callback); state; ++state)
      {
        auto cur = state.cursor().skipfwd();
        void *& data = state.data();
        switch(Context(data).value)
        {
          case '\0': data = Context(' '); break;
          case ' ' : os << ' ';           break;
          case '{' : data = Context('}'); break;
          case '}' : os << ' ';           break;
          case '(' : data = Context(')'); break;
          case ')' : os << ", ";          break;

          // Bracketed list.
          case '[' : data = Context(']'); break;
          case ']' :
            assert(cur.info()->flags == LIST_TYPE);
            if(cur.info()->tag == T_CONS)
            {
              os << ", ";
              state.push(Context('['));
            }
            else
              os << ']';
            continue;

          // String.
          case '"': data = Context('`'); break;
          case '`' :
            assert(cur.info()->flags == LIST_TYPE);
            if(cur.info()->tag == T_CONS)
              state.push(Context('"'));
            else
              os << '"';
            continue;

          // Cons list.
          case '!' : data = Context(':'); break;
          case ':' :
            if(cur.info()->flags == LIST_TYPE && cur.info()->tag == T_CONS)
            {
              os << ':';
              state.push(Context('!'));
              continue;
            }
            break;
        }

        switch(cur.kind)
        {
          case 'i': os << cur->ub_int;   continue;
          case 'f': os << cur->ub_float; continue;
          case 'c': os << cur->ub_char;  continue;
        }

        auto * info = cur.info();
        switch(info->tag)
        {
          case T_FAIL: os << "failed";                    continue;
          case T_FREE: os << '_' << NodeU{cur}.free->cid; continue;
          case T_FWD: /*state.push();*/ assert(0);        continue;
        }

        switch(cur.info()->flags)
        {
          case INT_TYPE:
          case CHAR_TYPE:
          case FLOAT_TYPE:
          case PARTIAL_TYPE:
            state.push();
            continue;
          case LIST_TYPE:
            state.push(analyze_list(cur));
            continue;
          case TUPLE_TYPE:
            os << '(';
            state.push(Context('('));
            continue;
          default:
            if(cur.info()->arity)
            {
              os << '(';
              os << cur.info()->name;
              state.push(Context('{'));
            }
            else
            {
              os << cur.info()->name;
              state.push();
            }
            continue;
        }
      }
    }

    Context analyze_list(Cursor cur)
    {
      Node * end = cur->node;
      bool is_string = true;
      while(end && end->info->flags == LIST_TYPE && end->info->tag == T_CONS)
      {
        auto cons = NodeU{end}.cons;
        is_string = is_string
            && (cons->head && cons->head->info->flags == CHAR_TYPE);
        end = cons->tail;
      }
      if(end && end->info->flags == LIST_TYPE)
      {
        if(is_string)
        {
          this->os << '"';
          return Context('"');
        }
        else
        {
          this->os << '[';
          return Context('[');
        }
      }
      else
        return Context('!');
    }
  };
}

namespace sprite
{
  void show(std::ostream & os, Cursor cur, ShowStyle sty)
  {
    switch(sty)
    {
      case SHOW_STR:
      {
        auto && stringifier = StrStringifier(os);
        return stringifier.stringify(cur);
      }
      case SHOW_REPR:
      {
        auto && stringifier = ReprStringifier(os);
        return stringifier.stringify(cur);
      }
    }
  }
}
