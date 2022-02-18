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

  void show_escaped(std::ostream & os, char value)
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
      for(auto && search=walk(expr, this, &callback); search; ++search)
      {
        auto && cur = search.cursor();
        if(first) first = false; else this->os << ' ';
        switch(cur.kind)
        {
          case 'i': show(cur->ub_int);   continue;
          case 'f': show(cur->ub_float); continue;
          case 'c': show(cur->ub_char);  continue;
          case 'x': show(cur->blob);  continue;
        }
        void * id = cur.id();
        if(!this->memo.insert(id).second)
          this->os << "...";
        else
        {
          this->os << '<';
          if(cur.info()->typetag == OPERATOR)
            os << '(' << cur.info()->name << ')';
          else
            os << cur.info()->name;
          search.push(id);
        }
      }
    }

    void show(unboxed_int_type value) { this->os << value; }
    void show(unboxed_float_type value) { this->os << value; }
    void show(unboxed_char_type value)
    {
      this->os << '\'';
      show_escaped(this->os, value);
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
      if(info->typetag & OPERATOR)
        os << '(' << info->name << ')';
      else
        os << info->name;
    }

    void stringify(Cursor expr)
    {
      for(auto && search=walk(expr, this, &callback); search; ++search)
      {
        auto cur = search.cursor().skipfwd();
        void *& data = search.data();
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
            assert(cur.info()->typetag == LIST_TYPE);
            bare = true;
            if(cur.info()->tag == T_CONS)
            {
              os << ", ";
              search.push(Context('['));
            }
            else
              os << ']';
            continue;

          // Concat list.
          case '_' : data = Context('^'); break;
          case '^' :
            assert(cur.info()->typetag == LIST_TYPE);
            if(cur.info()->tag == T_CONS)
            {
              os << ' ';
              search.push(Context('_'));
            }
            else
              os << ')';
            continue;

          // String.
          case '"': data = Context('`'); break;
          case '`' :
            assert(cur.info()->typetag == LIST_TYPE);
            if(cur.info()->tag == T_CONS)
              search.push(Context('"'));
            else
              os << '"';
            continue;

          // Cons list.
          case ':' : data = Context('!'); break;
          case '!' :
            os << ':';
            if(cur.info()->typetag == LIST_TYPE)
            {
              if(cur.info()->tag == T_CONS)
                search.push(Context(':'));
              else
                os << '[' << ']';
              continue;
            }
            break;
        }

        switch(cur.kind)
        {
          case 'i': show(cur->ub_int);   continue;
          case 'f': show(cur->ub_float); continue;
          case 'c': show(cur->ub_char);  continue;
          case 'x': show(cur->blob);  continue;
        }

        auto * info = cur.info();
        switch(info->tag)
        {
          case T_FREE: os << '_' << NodeU{cur}.free->vid; continue;
        }

        switch(info->typetag)
        {
          case INT_TYPE:
          case CHAR_TYPE:
          case FLOAT_TYPE:
            search.push();
            continue;
          case PARTIAL_TYPE:
          {
            auto const * partial = NodeU{cur->node}.partapplic;
            os << '(';
            show_name(os, partial->head_info);
            search.push(Context('^'));
            ++search; // skip #missing
            ++search; // skip head_info
            continue;
          }
          case LIST_TYPE:
            begin_list(search, cur);
            continue;
          case TUPLE_TYPE:
            os << '(';
            search.push(Context('('));
            continue;
          default:
            if(!bare && info->arity)
            {
              os << '(';
              this->show_name(os, info);
              search.push(Context('&'));
            }
            else
            {
              this->show_name(os, info);
              search.push(Context(' '));
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
      { show_escaped(this->os, value); }

    void show(void const * value)
      { this->os << value; }

    void begin_list(Search & search, Cursor cur)
    {
      Node * end = cur->node;
      bool is_string = true;
      bool is_empty = true;
      while(end && end->info->typetag == LIST_TYPE && end->info->tag == T_CONS)
      {
        auto cons = NodeU{end}.cons;
        is_string = is_string
            && (cons->head && cons->head->info->typetag == CHAR_TYPE);
        end = cons->tail;
        is_empty = false;
      }
      if(end && end->info->typetag == LIST_TYPE)
      {
        if(is_string && !is_empty)
        {
          this->os << '"';
          search.push(Context('"'));
        }
        else
        {
          this->os << '[';
          search.push(Context('['));
        }
      }
      else
        search.push(Context(':'));
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
