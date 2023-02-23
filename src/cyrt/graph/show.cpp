#include <algorithm>
#include <boost/io/ios_state.hpp>
#include <cassert>
#include <cstdio>
#include <ctype.h>
#include "cyrt/builtins.hpp"
#include "cyrt/currylib/setfunctions.hpp"
#include "cyrt/graph/node.hpp"
#include "cyrt/graph/show.hpp"
#include "cyrt/graph/walk.hpp"
#include "cyrt/inspect.hpp"
#include <functional>
#include <iomanip>
#include <iostream>
#include <list>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace
{
  using namespace cyrt;
  static size_t constexpr FLOAT_PRECISION = 17;

  static bool constexpr ESCAPE_DQ = true;
  static bool constexpr ESCAPE_SQ = false;

  void show_escaped(std::ostream & os, char value, bool mode)
  {
    switch(value)
    {
      case '"' : if(mode)  os << '\\' << '"' ; else os << value;
                 return;
      case '\'': if(!mode) os << '\\' << '\'' ; else os << value;
                 return;
      case '\\': os << '\\' << '\\'; return;
      case '\a': os << '\\' << 'a' ; return;
      case '\b': os << '\\' << 'b' ; return;
      case '\f': os << '\\' << 'f' ; return;
      case '\n': os << '\\' << 'n' ; return;
      case '\r': os << '\\' << 'r' ; return;
      case '\t': os << '\\' << 't' ; return;
      case '\v': os << '\\' << 'v' ; return;
      default  : break;
    }

    if(isprint(value))
      os << value;
    else
    {
      char buf[8];
      auto rv = snprintf(&buf[0], 8, "\\%02d", int((unsigned char) value));
      if(rv < 0)
        os.setstate(std::ios::failbit);
      else
        os << buf;
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
          if(is_operator(*cur->info) && !is_list(*cur->info) && !is_tuple(*cur->info))
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
      show_escaped(this->os, value, ESCAPE_SQ);
      this->os << '\'';
    }
    void show(void const * value) { this->os << value; }
  };

  struct OStreamReverseAdaptor
  {
    std::stringstream ss;
    std::vector<std::string> buffered;

    void flush()
    {
      auto str = ss.str();
      if(!str.empty())
      {
        buffered.push_back(str);
        ss.str(""); // clear
      }
    }
  };

  struct StrStringifier
  {
    StrStringifier(std::ostream & os, SubstFreevars subst_freevars, ShowMonitor * monitor)
      : _os(&os), subst_freevars(subst_freevars), monitor(monitor)
    {}

    std::ostream * _os;
    SubstFreevars subst_freevars;
    ShowMonitor * monitor;
    std::unordered_map<xid_type, std::string> tr; // free variable translations
    int nextid = 0;
    std::unordered_multiset<void *> memo;
    std::list<OStreamReverseAdaptor> ostream_adaptors;
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
      //     '-'     bare concat list item
      //     'v'     bare concat list spine
      //     '_'     parenthesized concat list item
      //     '^'     parenthesized concat list spine
      //     '"'     string item
      //     '`'     string spine
      //     'c'     char appearing in a double-quoted string

      Context(char value) : value(value) {}
      Context(void * p) : p(p) {}
      operator void *() const { return this->p; }
    };

    std::ostream & os()
    {
      if(this->ostream_adaptors.empty())
        return *_os;
      else
        return this->ostream_adaptors.back().ss;
    }

    void push_reverse_order()
    {
      this->ostream_adaptors.emplace_back();
    }

    void flush_reverse_order()
    {
      assert(!this->ostream_adaptors.empty());
      this->ostream_adaptors.back().flush();
    }

    void pop_reverse_order()
    {
      this->flush_reverse_order();
      assert(!this->ostream_adaptors.empty());
      auto strings = std::move(this->ostream_adaptors.back().buffered);
      this->ostream_adaptors.pop_back();
      auto & out = this->os();
      size_t const N = strings.size();
      for(size_t i=0; i<N; ++i)
        out << ' ' << strings[N-i-1];
    }

    static void callback(void * static_data, void * data, Walk2 const * walk)
    {
      auto self = (StrStringifier *)(static_data);
      switch(Context(data).value)
      {
        case '(':
        case ')':
        case '>':
        case '&': self->os() << ')'; break;
        case '[': self->os() << ']'; break;
      }
      void * id = walk->cursor().id();
      if(id)
      {
        assert(self->memo.count(id));
        auto p = self->memo.find(id);
        if(p != self->memo.end())
          self->memo.erase(p);
      }

      if(self->monitor)
        self->monitor->exit(self->os(), walk, Context(data).value);
    }

    void show_name(InfoTable const * info)
    {
      if(info)
      {
        if(is_operator(*info))
          this->os() << '(' << info->name << ')';
        else
          this->os() << info->name;
      }
    }

    bool is_terminus(InfoTable const * info)
    {
      // Indicates whether to always show this type of node (as opposed to an
      // elipsis) when a cycle occurs.
      if(info->arity == 0)
        return true;
      switch(typetag(*info))
      {
        case F_INT_TYPE  :
        case F_CHAR_TYPE :
        case F_FLOAT_TYPE:
        case F_BOOL_TYPE : return true;
        default          : break;
      }
      switch(info->tag)
      {
        case T_FAIL   :
        case T_FREE   :
        case T_UNBOXED: return true;
        default       : return false;
      }
    }

    void stringify(Cursor expr)
    {
      for(auto && walk=cyrt::walk(expr, this, &callback); walk; ++walk)
      {
        auto cur = walk.cursor();
        void * id = cur.id();
        bool cycle = false;
        this->memo.insert(id);
        if(cur.kind == 'p')
        {
          if(this->memo.count(id) > 1 && !this->is_terminus(cur->info))
            cycle = true;
          else if(cur->info->tag == T_FWD)
          {
            walk.extend(walk.data());
            continue;
          }
        }

        void *& data = walk.data();
        bool disallow_parens = false;

        switch(Context(data).value)
        {
          case '\0': disallow_parens = true; data = Context(' '); break;
          case ' ' :
          case '&' : this->os() << ' ';                           break;
          case '(' : disallow_parens = true; data = Context(')'); break;
          case ')' : disallow_parens = true; this->os() << ", ";  break;

          // Bracketed list.
          case '[' : disallow_parens = true; data = Context(']'); break;
          case ']' :
            assert(is_list(*cur->info));
            disallow_parens = true;
            if(cur->info->tag == T_CONS)
            {
              this->os() << ", ";
              if(cycle)
              {
                this->os() << "...]";
                continue;
              }
              walk.extend(Context('['));
            }
            else
              this->os() << ']';
            continue;

          // Concat list.
          case '_' : data = Context('^'); break;
          case '-' : data = Context('v'); break;
          case '^' :
          case 'v' :
            assert(is_list(*cur->info));
            if(!cycle && cur->info->tag == T_CONS)
            {
              this->flush_reverse_order();
              walk.extend(Context('_'));
            }
            else
            {
              this->pop_reverse_order();
              if(cycle)
                this->os() << "...";
              if(Context(data).value == '^')
                this->os() << ')';
            }
            continue;

          // String.
          case '"': data = Context('`'); break;
          case '`' :
            assert(is_list(*cur->info));
            if(cycle)
              this->os() << "\"...";
            else if(cur->info->tag == T_CONS)
              walk.extend(Context('"'));
            else
              this->os() << '"';
            continue;

          // Cons list.
          case ':' : data = Context('!'); break;
          case '<' : data = Context('>'); break;
          case '!' :
          case '>' :
            this->os() << ':';
            if(is_list(*cur->info))
            {
              if(cycle)
              {
                this->os() << "...";
                if(Context(data).value == '>')
                  this->os() << ")";
                continue;
              }
              else if(cur->info->tag == T_CONS)
              {
                auto next = Context(data).value == '!' ? Context(':') : Context('<');
                walk.extend(next);
              }
              else
                this->os() << '[' << ']';
              continue;
            }
            break;
        }

        if(cycle)
        {
          this->os() << "...";
          continue;
        }

        if(this->monitor)
          this->monitor->enter(this->os(), &walk, Context(data).value);

        switch(cur.kind)
        {
          case 'i': show(cur.arg->ub_int);
                    continue;
          case 'f': show(cur.arg->ub_float);
                    continue;
          case 'c': if(Context(data).value == 'c')
                      show_escaped(this->os(), cur.arg->ub_char, ESCAPE_DQ);
                    else
                      show(cur.arg->ub_char);
                    continue;
          case 'x': show(cur.arg->blob);
                    continue;
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
              this->os() << label;
            }
            else
              this->os() << p->second;
          }
          else
            this->os() << '_' << vid;
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
            if(partial->is_encapsulated())
              goto default_case;
            if(partial->info == &PartialS_Info)
            {
              if(!disallow_parens)
                os() << '(';
              os() << partial->info->name << ' '
                 << partial->missing << " {";
              show_name(partial->head_info);
              os() << "} " << partial->terms->repr();
              if(!disallow_parens)
                os() << ')';
            }
            else
            {
              if(!disallow_parens)
                os() << '(';
              show_name(partial->head_info);
              if(partial->terms == Nil)
              {
                if(!disallow_parens)
                  os() << ')';
              }
              else
              {
                this->push_reverse_order();
                walk.extend(Context(disallow_parens ? 'v' : '^'));
                ++walk; // skip #missing
                ++walk; // skip head_info
              }
            }
            continue;
          }
          case F_IO_TYPE:
          {
            walk.extend(Context(data));
            continue;
          }
          case F_LIST_TYPE:
            begin_list(walk, cur, disallow_parens);
            continue;
          case F_TUPLE_TYPE:
            this->os() << '(';
            walk.extend(Context('('));
            continue;
          case F_CSTRING_TYPE:
          {
            this->os() << '"';
            char const * p = NodeU{cur}.c_str->data;
            while(*p) show_escaped(this->os(), *p++, ESCAPE_DQ);
            this->os() << '"';
            continue;
          }
          default_case:
          default:
            if(!disallow_parens && info->arity)
            {
              this->os() << '(';
              this->show_name(info);
              walk.extend(Context('&'));
            }
            else
            {
              this->show_name(info);
              walk.extend(Context(' '));
            }
            continue;
        }
      }
    }

    void show(unboxed_int_type value)
    {
      if(value < 0)
        this->os() << '(' << value << ')';
      else
        this->os() << value;
    }

    void show(unboxed_float_type value)
    {
      boost::io::ios_flags_saver raii(this->os());
      this->os() << std::showpoint << std::setprecision(FLOAT_PRECISION);
      if(value < 0)
        this->os() << '(' << value << ')';
      else
        this->os() << value;
    }

    void show(unboxed_char_type value)
    {
      this->os() << '\'';
      show_escaped(this->os(), value, ESCAPE_SQ);
      this->os() << '\'';
    }

    void show(void const * value)
      { this->os() << value; }

    void begin_list(Walk2 & walk, Cursor cur, bool disallow_parens)
    {
      Node * end = cur;
      bool is_string = true;
      bool is_empty = true;
      std::unordered_set<void *> memo2;
      while(end && is_list(*end->info) && end->info->tag == T_CONS)
      {
        if(!memo2.insert(end).second)
        {
          is_string = false; // use bracket-style for cyclic lists.
          break;
        }
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
          this->os() << '"';
          walk.extend(Context('"'));
        }
        else
        {
          this->os() << '[';
          walk.extend(Context('['));
        }
      }
      else
      {
        if(disallow_parens)
          walk.extend(Context(':'));
        else
        {
          this->os() << '(';
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
