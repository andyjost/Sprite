#include <algorithm>
#include <boost/io/ios_state.hpp>
#include <cassert>
#include "cyrt/builtins.hpp"
#include "cyrt/graph/node.hpp"
#include "cyrt/graph/show.hpp"
#include "cyrt/graph/walk.hpp"
#include "cyrt/inspect.hpp"
#include <functional>
#include <iomanip>
#include <iostream>
#include <unordered_map>
#include <cstdio>

namespace
{
  using namespace cyrt;
  static size_t constexpr FLOAT_PRECISION = 17;

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

    static void callback(void * static_data, void * id, Walk2 const *)
    {
      auto self = (ReprStringifier *)(static_data);
      if(id) self->os << '>';
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
    void show(unboxed_float_type value)
    {
      boost::io::ios_flags_saver raii(this->os);
      this->os << std::showpoint << std::setprecision(FLOAT_PRECISION) << value;
    }
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
    StrStringifier(std::ostream & os, SubstFreevars subst_freevars, ShowMonitor * monitor)
      : os(os), subst_freevars(subst_freevars), monitor(monitor)
    {}

    std::ostream & os;
    SubstFreevars subst_freevars;
    ShowMonitor * monitor;
    std::unordered_map<xid_type, std::string> tr; // free variable translations
    int nextid = 0;
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
      //     ':'     bare cons list item
      //     '!'     bare cons list spine
      //     '<'     parenthisized cons list item
      //     '>'     parenthisized cons list spine
      //     '_'     concat list item
      //     '^'     concat list spine
      //     '"'     string item
      //     '`'     string spine
      //     'c'     char in a string (not single-quoted)

      Context(char value) : value(value) {}
      Context(void * p) : p(p) {}
      operator void *() const { return this->p; }
    };

    static void callback(void * static_data, void * data, Walk2 const * walk)
    {
      auto self = (StrStringifier *)(static_data);
      switch(Context(data).value)
      {
        case '(':
        case ')':
        case '>':
        case '&': self->os << ')'; break;
        case '[': self->os << ']'; break;
      }
      if(self->monitor)
        self->monitor->exit(self->os, walk, Context(data).value);
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
        bool disallow_parens = false;
        switch(Context(data).value)
        {
          case '\0': disallow_parens = true; data = Context(' '); break;
          case ' ' :
          case '&' : os << ' ';                        break;
          case '(' : disallow_parens = true; data = Context(')'); break;
          case ')' : disallow_parens = true; os << ", ";          break;

          // Bracketed list.
          case '[' : disallow_parens = true; data = Context(']'); break;
          case ']' :
            assert(is_list(*cur->info));
            disallow_parens = true;
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
          case '<' : data = Context('>'); break;
          case '!' :
          case '>' :
            os << ':';
            if(is_list(*cur->info))
            {
              if(cur->info->tag == T_CONS)
              {
                auto next = Context(data).value == '!' ? Context(':') : Context('<');
                walk.extend(next);
              }
              else
                os << '[' << ']';
              continue;
            }
            break;
        }

        if(this->monitor)
          this->monitor->enter(this->os, &walk, Context(data).value);

        switch(cur.kind)
        {
          case 'i': show(cur.arg->ub_int);   continue;
          case 'f': show(cur.arg->ub_float); continue;
          case 'c': show(cur.arg->ub_char, Context(data).value != 'c');  continue;
          case 'x': show(cur.arg->blob);     continue;
        }

        auto * info = cur->info;
        if(info->tag == T_FREE)
        {
          xid_type vid = NodeU{cur}.free->vid;
          if(this->subst_freevars)
          {
            auto p = tr.find(vid);
            if(p == tr.end())
            {
              auto label = this->next_label();
              tr[vid] = label;
              os << label;
            }
            else
              os << p->second;
          }
          else
            os << '_' << vid;
          continue;
        }

        switch(typetag(*info))
        {
          case F_INT_TYPE:
          case F_FLOAT_TYPE:
            walk.extend();
            continue;
          case F_CHAR_TYPE:
            if(Context(data).value == '`')
              walk.extend(Context('c'));
            else
              walk.extend();
            continue;
          case F_PARTIAL_TYPE:
          {
            auto const * partial = NodeU{cur}.partapplic;
            if(partial->terms == Nil)
              show_name(os, partial->head_info);
            else
            {
              os << '(';
              show_name(os, partial->head_info);
              walk.extend(Context('^'));
              ++walk; // skip #missing
              ++walk; // skip head_info
            }
            continue;
          }
          case F_LIST_TYPE:
            begin_list(walk, cur, disallow_parens);
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
            if(!disallow_parens && info->arity)
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
      boost::io::ios_flags_saver raii(this->os);
      this->os << std::showpoint << std::setprecision(FLOAT_PRECISION);
      if(value < 0)
        this->os << '(' << value << ')';
      else
        this->os << value;
    }

    void show(unboxed_char_type value, bool sq)
    {
      if(sq) this->os << '\'';
      show_sq_escaped(this->os, value);
      if(sq) this->os << '\'';
    }

    void show(void const * value)
      { this->os << value; }

    void begin_list(Walk2 & walk, Cursor cur, bool disallow_parens)
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
      {
        if(disallow_parens)
          walk.extend(Context(':'));
        else
        {
          this->os << '(';
          walk.extend(Context('<'));
        }
      }
    }

    std::string next_label()
    {
      std::string label("_");
      int n = this->nextid++;
      while(n >= 0)
      {
        label.push_back('a' + n % 26);
        n = n / 26 - 1;
      }
      std::reverse(label.begin()+1, label.end());
      return label;
    }
  };
}

namespace cyrt
{
  void show(std::ostream & os, Cursor cur, ShowStyle sty, ShowMonitor * monitor)
  {
    auto subst_freevars = PLAIN_FREEVARS;
    switch(sty)
    {
      case SHOW_STR_SUBST_FREEVARS:
        subst_freevars = SUBST_FREEVARS;
      case SHOW_STR:
      {
        auto && stringifier = StrStringifier(os, subst_freevars, monitor);
        return stringifier.stringify(cur);
      }
      case SHOW_REPR:
      {
        auto && stringifier = ReprStringifier(os);
        return stringifier.stringify(cur);
      }
    }
  }

  void show(std::ostream & os, std::vector<index_type> const & path)
  {
    os << '[';
    bool tail = false;
    for(auto i: path)
    {
      if(tail) os << ", "; else tail = true;
      os << i;
    }
    os << ']';
  }

  void show(std::ostream & os, std::vector<Set *> const & path)
  {
    os << "{TODO}";
  }
}
