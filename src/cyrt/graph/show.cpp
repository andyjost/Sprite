#include <cassert>
#include "cyrt/builtins.hpp"
#include "cyrt/graph/node.hpp"
#include "cyrt/graph/show.hpp"
#include "cyrt/graph/walk.hpp"
#include "cyrt/inspect.hpp"
#include <functional>
#include <iostream>
#include <unordered_map>

namespace
{
  using namespace cyrt;

  void show_sq_escaped(std::ostream & os, char value)
  {
    switch(value)
    {
      case '\'': os << '\\' << '\''; break;
      case '\\': os << '\\' << '\\'; break;
      case '\a': os << '\\' << 'a' ; break;
      case '\b': os << '\\' << 'b' ; break;
      case '\f': os << '\\' << 'f' ; break;
      case '\n': os << '\\' << 'n' ; break;
      case '\r': os << '\\' << 'r' ; break;
      case '\t': os << '\\' << 't' ; break;
      case '\v': os << '\\' << 'v' ; break;
      default  : os << value ; break;
    }
  }

  void show_dq_escaped(std::ostream & os, char value)
  {
    switch(value)
    {
      case '"' : os << '\\' << '"' ; break;
      case '\\': os << '\\' << '\\'; break;
      case '\a': os << '\\' << 'a' ; break;
      case '\b': os << '\\' << 'b' ; break;
      case '\f': os << '\\' << 'f' ; break;
      case '\n': os << '\\' << 'n' ; break;
      case '\r': os << '\\' << 'r' ; break;
      case '\t': os << '\\' << 't' ; break;
      case '\v': os << '\\' << 'v' ; break;
      default  : os << value ; break;
    }
  }


  struct ReprStringifier
  {
    ReprStringifier(std::ostream & os) : os(os) {}
    std::ostream & os;
    std::unordered_set<void *> memo;

    static void callback(void * static_data, void * id)
    {
      auto self = (ReprStringifier *)(static_data);
      if(id) // FIXME: guess
        self->os << '>';
      self->memo.erase(id);
    }

    void stringify(Cursor expr)
    {
      bool first = true;
      for(auto && walk=cyrt::walk(expr, this, &callback); walk; ++walk)
      {
        auto && cur = walk.cursor();
        if(first) first = false; else this->os << ' ';
        switch(cur.kind)
        {
          case 'i': show(cur.arg->ub_int);   continue;
          case 'f': show(cur.arg->ub_float); continue;
          case 'c': show(cur.arg->ub_char);  continue;
          case 'x': show(cur.arg->blob);     continue;
        }
        void * id = cur.id();
        if(!this->memo.insert(id).second)
          this->os << "...";
        else
        {
          this->os << '<';
          if(is_operator(*cur->info))
            os << '(' << cur->info->name << ')';
          else
            os << cur->info->name;
          walk.extend(id);
        }
      }
    }

    void show(unboxed_int_type value) { this->os << value; }
    void show(unboxed_float_type value) { this->os << value; }
    void show(unboxed_char_type value)
    {
      this->os << '\'';
      show_sq_escaped(this->os, value);
      this->os << '\'';
    }
    void show(void const * value) { this->os << value; }
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
      //     '&'     parenthesized subexpr
      //     '('     tuple first term
      //     ')'     tuple non-first term
      //     '['     square list item
      //     ']'     square list spine
      //     ':'     cons list item
      //     '!'     cons list spine
      //     '_'     concat list item
      //     '^'     concat list spine
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
        case '&': self->os << ')'; break;
        case '[': self->os << ']'; break;
      }
    }

    void show_name(std::ostream & os, InfoTable const * info)
    {
      if(is_operator(*info))
        os << '(' << info->name << ')';
      else
        os << info->name;
    }

    void stringify(Cursor expr)
    {
      for(auto && walk=cyrt::walk(expr, this, &callback); walk; ++walk)
      {
        auto cur = walk.cursor().skipfwd();
        void *& data = walk.data();
        bool bare = false;
        switch(Context(data).value)
        {
          case '\0': bare = true; data = Context(' '); break;
          case ' ' :
          case '&' : os << ' ';                        break;
          case '(' : bare = true; data = Context(')'); break;
          case ')' : bare = true; os << ", ";          break;

          // Bracketed list.
          case '[' : bare = true; data = Context(']'); break;
          case ']' :
            assert(is_list(*cur->info));
            bare = true;
            if(cur->info->tag == T_CONS)
            {
              os << ", ";
              walk.extend(Context('['));
            }
            else
              os << ']';
            continue;

          // Concat list.
          case '_' : data = Context('^'); break;
          case '^' :
            assert(is_list(*cur->info));
            if(cur->info->tag == T_CONS)
            {
              os << ' ';
              walk.extend(Context('_'));
            }
            else
              os << ')';
            continue;

          // String.
          case '"': data = Context('`'); break;
          case '`' :
            assert(is_list(*cur->info));
            if(cur->info->tag == T_CONS)
              walk.extend(Context('"'));
            else
              os << '"';
            continue;

          // Cons list.
          case ':' : data = Context('!'); break;
          case '!' :
            os << ':';
            if(is_list(*cur->info))
            {
              if(cur->info->tag == T_CONS)
                walk.extend(Context(':'));
              else
                os << '[' << ']';
              continue;
            }
            break;
        }

        switch(cur.kind)
        {
          case 'i': show(cur.arg->ub_int);   continue;
          case 'f': show(cur.arg->ub_float); continue;
          case 'c': show(cur.arg->ub_char);  continue;
          case 'x': show(cur.arg->blob);     continue;
        }

        auto * info = cur->info;
        switch(info->tag)
        {
          case T_FREE: os << '_' << NodeU{cur}.free->vid; continue;
        }

        switch(typetag(*info))
        {
          case F_INT_TYPE:
          case F_CHAR_TYPE:
          case F_FLOAT_TYPE:
            walk.extend();
            continue;
          case F_PARTIAL_TYPE:
          {
            auto const * partial = NodeU{cur}.partapplic;
            os << '(';
            show_name(os, partial->head_info);
            walk.extend(Context('^'));
            ++walk; // skip #missing
            ++walk; // skip head_info
            continue;
          }
          case F_LIST_TYPE:
            begin_list(walk, cur);
            continue;
          case F_TUPLE_TYPE:
            os << '(';
            walk.extend(Context('('));
            continue;
          case F_CSTRING_TYPE:
          {
            os << '"';
            char const * p = NodeU{cur}.c_str->data;
            while(*p) show_dq_escaped(os, *p++);
            os << '"';
            continue;
          }
          default:
            if(!bare && info->arity)
            {
              os << '(';
              this->show_name(os, info);
              walk.extend(Context('&'));
            }
            else
            {
              this->show_name(os, info);
              walk.extend(Context(' '));
            }
            continue;
        }
      }
    }

    void show(unboxed_int_type value)
    {
      if(value < 0)
        this->os << '(' << value << ')';
      else
        this->os << value;
    }

    void show(unboxed_float_type value)
    {
      if(value < 0)
        this->os << '(' << value << ')';
      else
        this->os << value;
    }

    void show(unboxed_char_type value)
      { show_sq_escaped(this->os, value); }

    void show(void const * value)
      { this->os << value; }

    void begin_list(Walk2 & walk, Cursor cur)
    {
      Node * end = cur;
      bool is_string = true;
      bool is_empty = true;
      while(end && is_list(*end->info) && end->info->tag == T_CONS)
      {
        auto cons = NodeU{end}.cons;
        is_string = is_string
            && (cons->head && is_char(*cons->head->info));
        end = cons->tail;
        is_empty = false;
      }
      if(end && is_list(*end->info))
      {
        if(is_string && !is_empty)
        {
          this->os << '"';
          walk.extend(Context('"'));
        }
        else
        {
          this->os << '[';
          walk.extend(Context('['));
        }
      }
      else
        walk.extend(Context(':'));
    }
  };
}

namespace cyrt
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
