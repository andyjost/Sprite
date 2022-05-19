#include <cassert>
#include <cstdlib>
#include "cyrt/cyrt.hpp"
#include <sstream>
#include <type_traits>

#define CHAR_BOUND 256 // ASCII only

using namespace cyrt;

namespace cyrt
{
  static inline ConsNode * string_cast(Node * string)
  {
    assert(!string || string->info->type == &List_Type);
    switch(string ? string->info->tag : T_NIL)
    {
      case T_CONS: return NodeU{string}.cons;
      case T_NIL:  return nullptr;
      default:     assert(0);
                   return nullptr;
    }
  }

  static inline unboxed_char_type head_char(ConsNode * string)
  {
    assert(string);
    assert(string->info->type == &List_Type);
    assert(string->info->tag == T_CONS);
    return NodeU{string->head}.char_->value;
  }

  template<int Radix>
  static inline Node * _parseCharOrd(ConsNode *& string, bool advance)
  {
    static_assert(0 <= Radix && Radix <= 10, "digits only");
    if(advance && string)
      string = string_cast(string->tail);
    int ord = 0;
    while(string)
    {
      int offset = head_char(string) - '0';
      if(0 <= offset && offset <= Radix)
      {
        if(ord < CHAR_BOUND)
          ord = Radix * ord + offset;
      }
      else
        break;
      string = string_cast(string->tail);
    }
    if(ord < CHAR_BOUND)
      return char_((char) ord);
    else
      return nullptr;
  }

  template<>
  inline Node * _parseCharOrd<16>(ConsNode *& string, bool advance)
  {
    int ord = 0;
    char base = 0;
    if(advance && string)
      string = string_cast(string->tail);
    while(string)
    {
      char ch = head_char(string);
      switch(ch)
      {
        case '0':
        case '1':
        case '2':
        case '3':
        case '4':
        case '5':
        case '6':
        case '7':
        case '8':
        case '9': base = '0'; break;
        case 'a':
        case 'b':
        case 'c':
        case 'd':
        case 'e':
        case 'f': base = 'a' - 10; break;
        case 'A':
        case 'B':
        case 'C':
        case 'D':
        case 'E':
        case 'F': base = 'A' - 10; break;
        default : return nullptr;
      }
      if(ord < CHAR_BOUND)
        ord = 16 * ord + (ch - base);
      string = string_cast(string->tail);
    }
    if(ord < CHAR_BOUND)
      return char_((char) ord);
    else
      return nullptr;
  }

  static inline Node * _parseEscapeCode(ConsNode *& string)
  {
    if(!string)
      return nullptr;
    switch(head_char(string))
    {
      case '\\':
      case '"' :
      case '\'': return string->head;
      case 'a' : return char_('\a');
      case 'b' : return char_('\b');
      case 'f' : return char_('\f');
      case 'n' : return char_('\n');
      case 'r' : return char_('\r');
      case 't' : return char_('\t');
      case 'v' : return char_('\v');
      case 'o' : return _parseCharOrd<8>(string, true);
      case '0' : case '1' : case '2' : case '3' : case '4' :
      case '5' : case '6' : case '7' : case '8' : case '9' :
                 return _parseCharOrd<10>(string, false);
      case 'x' : return _parseCharOrd<16>(string, true);
      default  : return nullptr;
    }
  }

  static tag_type readCharLiteral_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = _0[0]; // pre-normalized with $## in the Prelude
    Node * char_out = nullptr;
    ConsNode * string = string_cast(_1);
    Node * replacement = nullptr;

    // Eat the opening single quote.
    if(!string || head_char(string) != '\'') goto failed;
    string = string_cast(string->tail);

    // Parse the content.
    if(string && head_char(string) == '\\')
    {
      string = string_cast(string->tail);
      char_out = _parseEscapeCode(string);
    }
    else if(string)
    {
      auto ch = head_char(string);
      if(ch < CHAR_BOUND && ch != '\'')
        char_out = string->head;
    }
    if(!char_out) goto failed;

    // Eat the closing single quote.
    assert(string);
    string = string_cast(string->tail);
    if(!string || head_char(string) != '\'') goto failed;

    assert(char_out);
    replacement = cons(pair(char_out, string->tail), nil());
    _0->forward_to(replacement);
    return T_FWD;
  failed:
    return _0->make_failure();
  }

  static tag_type readFloatLiteral_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = _0[0]; // pre-normalized with $## in the Prelude
    ConsNode * string = string_cast(_1);
    std::stringstream ss;
    while(string)
    {
      auto ch = (char) head_char(string);
      switch(ch)
      {
        case '0': case '1': case '2': case '3': case '4':
        case '5': case '6': case '7': case '8': case '9':
        case 'e': case 'E': case '+': case '-': case '.':
            ss << ch;
            string = string_cast(string->tail);
        default:
            break;
      }
    }
    static_assert(std::is_same<unboxed_float_type, double>::value, "stdtod assumes double");
    unboxed_float_type const value = std::strtod(ss.str().c_str(), nullptr);
    Node * replacement = cons(pair(int_(value), string ? (Node *) string : nil()), nil());
    _0->forward_to(replacement);
    return T_FWD;
  }

  static tag_type readNatLiteral_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = _0[0]; // pre-normalized with $## in the Prelude
    ConsNode * string = string_cast(_1);
    static ptrdiff_t constexpr SZ = 32;
    char buf[SZ];
    char * px = &buf[0];
    while(string && px < &buf[SZ-1])
    {
      auto ch = (char) head_char(string);
      if('0' <= ch && ch <= '9')
      {
        *px++ = ch;
        string = string_cast(string->tail);
      }
      else
        break;
    }
    *px++ = '\0';
    assert(px - &buf[0] <= SZ);
    static_assert(std::is_same<unboxed_int_type, long>::value, "stdtol assumes long");
    errno = 0;
    unboxed_int_type value = std::strtol(&buf[0], nullptr, 10);
    if(errno == ERANGE)
      return _0->make_failure();
    Node * replacement = cons(pair(int_(value), string ? (Node *) string : nil()), nil());
    _0->forward_to(replacement);
    return T_FWD;
  }

  static tag_type readStringLiteral_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = _0[0]; // pre-normalized with $## in the Prelude
    Node * str_out = nil();
    Node ** tail_out = &str_out;
    ConsNode * string = string_cast(_1);
    Node * replacement = nullptr;

    // Eat the opening double quote.
    if(!string || head_char(string) != '"') goto failed;
    string = string_cast(string->tail);

    // Parse the content.
    while(true)
    {
      Node * char_out = nullptr;
      if(string)
      {
        auto ch = head_char(string);
        if(ch == '\\')
        {
          string = string_cast(string->tail);
          char_out = _parseEscapeCode(string);
        }
        else if(ch == '"')
          break;
        else if(ch < CHAR_BOUND)
          char_out = string->head;
      }
      if(!char_out) goto failed;
      *tail_out = cons(char_out, nil());
      tail_out = &NodeU{*tail_out}.cons->tail;
      string = string_cast(string->tail);
    }
    replacement = cons(pair(str_out, string->tail), nil());
    _0->forward_to(replacement);
    return T_FWD;
  failed:
    return _0->make_failure();
  }
}

extern "C"
{
  InfoTable const prim_readCharLiteral_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "readCharLiteral"
    , /*format*/     "p"
    , /*step*/       readCharLiteral_step
    , /*type*/       nullptr
    };

  InfoTable const prim_readFloatLiteral_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "readFloatLiteral"
    , /*format*/     "p"
    , /*step*/       readFloatLiteral_step
    , /*type*/       nullptr
    };

  InfoTable const prim_readNatLiteral_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "readNatLiteral"
    , /*format*/     "p"
    , /*step*/       readNatLiteral_step
    , /*type*/       nullptr
    };

  InfoTable const prim_readStringLiteral_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "readStringLiteral"
    , /*format*/     "p"
    , /*step*/       readStringLiteral_step
    , /*type*/       nullptr
    };
}
