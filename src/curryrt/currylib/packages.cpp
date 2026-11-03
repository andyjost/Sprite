#include "curryrt/curryrt.hpp"
#include "curryrt/currylib/prelude.hpp"
#include "curryrt/module.hpp"
#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <thread>
#include <cmath>
#include <locale>
#include <sstream>
#include <unordered_set>
#include "curryrt/bigint.hpp"

using namespace curryrt;
namespace fs = std::filesystem;
namespace
{
  // Keep package constructor lookups together for the per-interpreter registry.
  InfoTable const * package_constructor(std::string const & module, std::string const & name)
  {
    if(!Module::find(module))
      throw std::runtime_error("Package primitive: module " + module + " is not loaded");
    // An empty name validates a prefix without selecting a constructor.
    if(name.empty()) return nullptr;
    auto info = Module::find_symbol(module, name);
    return info && info->tag >= T_CTOR && !is_partial(*info) ? info : nullptr;
  }

  tag_type step(RuntimeState *, Configuration * C)
  {
    Cursor root = C->cursor();
    std::string op = root->info->name;
    auto path = [&](int i) { return fs::u8path(extract_string(root[i].target)); };
    Node * result = unit();
    try
    {
      if(op == "prim_system")
      {
        int status = std::system(extract_string(root[0].target).c_str());
        if(status == -1) throw std::system_error(errno, std::generic_category());
#if !defined(_WIN32)
        // The C library encodes normal exit status in the high byte.
        status = (status & 127) ? 128 + (status & 127) : (status >> 8) & 255;
#endif
        result = int_(status);
      }
      else if(op == "prim_sleep")
      {
        auto seconds = NodeU{root[0].target}.int_->value;
        if(seconds > 0) std::this_thread::sleep_for(std::chrono::seconds(seconds));
      }
      else if(op == "prim_doesFileExist" || op == "prim_doesDirectoryExist")
      {
        std::error_code error;
        auto status = fs::status(path(0), error);
        bool exists = op == "prim_doesFileExist" ? fs::is_regular_file(status) : fs::is_directory(status);
        result = exists ? true_() : false_();
      }
      else if(op == "prim_fileSize") result = int_(fs::file_size(path(0)));
      else if(op == "prim_getModificationTime")
      {
        // C++17 file_clock has an implementation-defined epoch. Translate
        // via simultaneous clock readings to POSIX seconds, as CTime uses.
        auto stamp = fs::last_write_time(path(0));
        auto now = decltype(stamp)::clock::now();
        auto system = std::chrono::system_clock::now() + (stamp - now);
        auto seconds = std::chrono::duration_cast<std::chrono::seconds>(system.time_since_epoch()).count();
        auto ctor = package_constructor("Data.Time", "CTime");
        if(!ctor) throw std::runtime_error("Data.Time.CTime is not loaded");
        result = Node::create(ctor, int_(seconds));
      }
      else if(op == "getCurrentDirectory") result = build_curry_string(fs::current_path().u8string().c_str());
      else if(op == "prim_setCurrentDirectory") fs::current_path(path(0));
      else if(op == "prim_getDirectoryContents")
      {
        std::vector<std::string> entries{".", ".."};
        for(auto const & entry: fs::directory_iterator(path(0)))
          entries.push_back(entry.path().filename().u8string());
        result = nil();
        for(auto i=entries.rbegin(); i!=entries.rend(); ++i)
          result = cons(build_curry_string(i->c_str()), result);
      }
      else if(op == "prim_createDirectory")
      {
        if(!fs::create_directory(path(0)))
          throw std::system_error(std::make_error_code(std::errc::file_exists));
      }
      else if(op == "prim_removeDirectory" || op == "prim_removeFile")
      {
        bool directory = fs::is_directory(fs::symlink_status(path(0)));
        if(directory != (op == "prim_removeDirectory"))
          throw std::system_error(std::make_error_code(directory ?
              std::errc::is_a_directory : std::errc::not_a_directory));
        if(!fs::remove(path(0))) throw std::system_error(std::make_error_code(std::errc::no_such_file_or_directory));
      }
      else if(op == "prim_renameFile" || op == "prim_renameDirectory")
      {
        bool directory = fs::is_directory(fs::symlink_status(path(0)));
        if(directory != (op == "prim_renameDirectory"))
          throw std::system_error(std::make_error_code(directory ?
              std::errc::is_a_directory : std::errc::not_a_directory));
        fs::rename(path(0), path(1));
      }
      root->forward_to(io(result));
      return T_FWD;
    }
    catch(std::exception const & exc)
    {
      C->set_error(Node::create(ioerror_info(IO_ERROR), build_curry_string(exc.what())),
          std::string("i/o error: ") + exc.what(), ErrorKind::io);
      return E_ERROR;
    }
  }
  Node * data_node(Node * node)
  {
    while(node && (node->info->tag == T_FWD || node->info->tag == T_SETGRD))
      node = node->info->tag == T_FWD ? NodeU{node}.fwd->target : NodeU{node}.setgrd->value;
    if(!node) throw std::runtime_error("ReadShowTerm: null term");
    return node;
  }

  struct TermPrinter
  {
    std::unordered_set<Node *> path;
    std::string print(Node * raw)
    {
      auto node = data_node(raw);
      auto info = node->info;
      if(!path.insert(node).second)
        throw std::runtime_error("ReadShowTerm.showTerm: cyclic term");
      struct Pop
      {
        std::unordered_set<Node *> & path;
        Node * node;
        ~Pop() { path.erase(node); }
      } pop{path, node};
      if(info->tag == T_FREE)
        throw std::runtime_error("ReadShowTerm.showTerm: free variable");
      if(is_partial(*info))
        throw std::runtime_error("ReadShowTerm.showTerm: partial application");
      if(info->tag < T_CTOR)
        throw std::runtime_error("ReadShowTerm.showTerm: argument is not in normal form");
      if(is_int(*info) || is_float(*info) || is_char(*info))
      {
        if(is_float(*info) && !std::isfinite(NodeU{node}.float_->value))
          throw std::runtime_error("ReadShowTerm.showTerm: non-finite Float");
        auto text = node->str();
        // Prolog's N>=0 includes negative zero.
        if(is_float(*info) && NodeU{node}.float_->value == 0 && text == "(-0.0)")
          return "-0.0";
        return text;
      }
      if(info->type == &Unit_Type) return "()";
      if(info->type == &List_Type)
      {
        std::vector<Node *> elements;
        std::unordered_set<Node *> spine;
        auto tail = node;
        bool string = true;
        while(tail->info->type == &List_Type && tail->info->tag == T_CONS)
        {
          if(!spine.insert(tail).second)
            throw std::runtime_error("ReadShowTerm.showTerm: cyclic list");
          auto head = data_node(NodeU{tail}.cons->head);
          string = string && is_char(*head->info);
          elements.push_back(head);
          tail = data_node(NodeU{tail}.cons->tail);
        }
        if(tail->info->type != &List_Type || tail->info->tag != T_NIL)
          throw std::runtime_error("ReadShowTerm.showTerm: incomplete list");
        if(elements.empty()) return "[]";
        if(string) return node->str();
        std::string text = "[";
        for(auto element: elements)
        {
          if(text.size() > 1) text += ',';
          text += print(element);
        }
        return text + ']';
      }
      std::string name = info->name;
      // Tables normally store unqualified names.
      auto dot = name.rfind('.');
      if(dot != std::string::npos && !name.empty() &&
          ((name[0] >= 'A' && name[0] <= 'Z') || (name[0] >= 'a' && name[0] <= 'z')))
        name.erase(0, dot + 1);
      bool tuple = name.size() >= 3 && name.front() == '(' && name[1] == ',';
      // PAKCS tests the qualified atom for isId before dropping its module.
      // Thus even an unqualified operator name is printed without brackets.
      std::string text = tuple ? "(" : name;
      if(info->arity && !tuple) text = "(" + text;
      for(index_type i = 0; i < info->arity; ++i)
      {
        if(!tuple) text += ' ';
        else if(i) text += ',';
        if(info->format[i] != 'p')
          throw std::runtime_error("ReadShowTerm.showTerm: opaque constructor " + name);
        text += print(node->successor_node(i));
      }
      if(info->arity) text += ')';
      return text;
    }
  };

  struct TermParseFailure {};

  struct TermReader
  {
    std::vector<std::string> prefixes;
    std::vector<unsigned> input;
    std::vector<Node *> tails;
    size_t pos = 0;
    explicit TermReader(Node * modules, Node * string)
    {
      for(auto list = data_node(modules); list->info->tag == T_CONS;
          list = data_node(NodeU{list}.cons->tail))
      {
        auto prefix = extract_string(NodeU{list}.cons->head);
        package_constructor(prefix, "");
        prefixes.push_back(prefix);
      }
      auto list = data_node(string);
      while(list->info->tag == T_CONS)
      {
        tails.push_back(list);
        input.push_back(NodeU{data_node(NodeU{list}.cons->head)}.char_->value);
        list = data_node(NodeU{list}.cons->tail);
      }
      tails.push_back(list);
    }
    unsigned peek() const { return pos < input.size() ? input[pos] : 0; }
    bool take(unsigned c)
    {
      if(pos < input.size() && input[pos] == c) { ++pos; return true; }
      return false;
    }
    void need(unsigned c) { if(!take(c)) throw TermParseFailure{}; }
    static bool white(unsigned c) { return c == 32 || c == 10 || c == 13 || c == 12 || c == 9; }
    static bool letter(unsigned c) { return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z'); }
    static bool digit(unsigned c) { return c >= '0' && c <= '9'; }
    static bool idchar(unsigned c) { return letter(c) || digit(c) || c == '_' || c == '\'' || c == '.'; }
    static bool opchar(unsigned c) { return c && std::string(":!#$%&*+./<=>?@\\^|-~").find(char(c)) != std::string::npos && c < 128; }
    void space()
    {
      for(;;)
      {
        while(white(peek())) ++pos;
        if(peek() != '{' || pos + 1 == input.size() || input[pos+1] != '-') return;
        pos += 2;
        while(pos + 1 < input.size() && !(input[pos] == '-' && input[pos+1] == '}')) ++pos;
        if(pos + 1 >= input.size()) throw TermParseFailure{};
        pos += 2;
      }
    }
    unsigned character()
    {
      if(pos == input.size()) throw TermParseFailure{};
      auto c = input[pos++];
      if(c != '\\') return c;
      if(pos == input.size()) throw TermParseFailure{};
      c = input[pos++];
      if(digit(c))
      {
        unsigned value = c - '0';
        while(digit(peek()))
        {
          if(value > 0x10ffff) throw TermParseFailure{};
          value = value * 10 + input[pos++] - '0';
        }
        if(value > 0x10ffff) throw TermParseFailure{};
        return value;
      }
      std::string codes = "abtnvfr\\\"'";
      std::string values = "\a\b\t\n\v\f\r\\\"'";
      auto i = codes.find(char(c));
      if(c < 128 && i != std::string::npos) return values[i];
      // Named ASCII escapes accepted by PAKCS's readChar/readString.
      static char const * names[] = {"NUL","SOH","STX","ETX","EOT","ENQ","ACK","BEL",
        "BS","HT","LF","VT","FF","CR","SO","SI","DLE","DC1","DC2","DC3","DC4",
        "NAK","SYN","ETB","CAN","EM","SUB","ESC","FS","GS","RS","US","SP"};
      --pos;
      for(unsigned n = 0; n <= 33; ++n)
      {
        std::string name = n == 33 ? "DEL" : names[n];
        if(pos + name.size() <= input.size() && std::equal(name.begin(), name.end(), input.begin()+pos))
        { pos += name.size(); return n == 33 ? 127 : n; }
      }
      throw TermParseFailure{};
    }
    Node * construct(std::string const & name, std::vector<Arg> const & args)
    {
      InfoTable const * ctor = nullptr;
      for(auto const & prefix: prefixes)
        if((ctor = package_constructor(prefix, name))) break;
      if(!ctor)
      {
        std::string modules;
        for(auto const & prefix: prefixes) { if(!modules.empty()) modules += ", "; modules += prefix; }
        throw std::runtime_error("ReadShowTerm: unknown constructor " + name + " in modules [" + modules + "]");
      }
      if(ctor->arity != args.size()) throw TermParseFailure{};
      for(index_type i = 0; i < ctor->arity; ++i)
        if(ctor->format[i] != 'p')
          throw std::runtime_error("ReadShowTerm: opaque constructor " + name);
      return Node::create(ctor, args.data());
    }
    bool endargs() const
    {
      return pos == input.size() || peek() == ')' || peek() == ',' || peek() == ':' || peek() == ']';
    }
    Node * term(bool application = true)
    {
      space();
      if(pos == input.size()) throw TermParseFailure{};
      if(take('['))
      {
        if(take(']')) return nil();
        std::vector<Node *> elements;
        do { elements.push_back(term()); space(); } while(take(','));
        need(']');
        Node * list = nil();
        for(auto i = elements.rbegin(); i != elements.rend(); ++i) list = cons(*i, list);
        return list;
      }
      if(take('\'')) { auto c = character(); need('\''); return char_(c); }
      if(take('"'))
      {
        std::vector<unsigned> chars;
        while(peek() != '"') chars.push_back(character());
        need('"');
        Node * string = nil();
        for(auto i = chars.rbegin(); i != chars.rend(); ++i) string = cons(char_(*i), string);
        return string;
      }
      if(take('('))
      {
        if(take(')')) return unit();
        // An operator constructor is itself parenthesized inside its application.
        size_t saved = pos;
        if(take('(') && opchar(peek()))
        {
          std::string name;
          while(opchar(peek())) name += char(input[pos++]);
          if(take(')'))
          {
            space();
            std::vector<Arg> args;
            while(!endargs()) { args.push_back(term(false)); space(); }
            need(')');
            return construct(name, args);
          }
        }
        pos = saved;
        auto first = term(); space();
        if(take(','))
        {
          std::vector<Arg> args{first};
          do { args.push_back(term()); space(); } while(take(','));
          need(')');
          auto ctor = package_constructor("Prelude", "(" + std::string(args.size()-1, ',') + ")");
          if(!ctor) throw std::runtime_error("ReadShowTerm: tuple constructor is not loaded");
          return Node::create(ctor, args.data());
        }
        if(take(':'))
        {
          std::vector<Node *> heads{first};
          Node * tail;
          for(;;)
          {
            tail = term(); space();
            if(!take(':')) break;
            heads.push_back(tail);
          }
          need(')');
          for(auto i = heads.rbegin(); i != heads.rend(); ++i) tail = cons(*i, tail);
          return tail;
        }
        need(')'); return first;
      }
      if(digit(peek()) || (peek() == '-' && pos+1 < input.size() && digit(input[pos+1])))
      {
        std::string text;
        if(take('-')) text += '-';
        while(digit(peek())) text += char(input[pos++]);
        bool floating = false;
        if(peek() == '.' && pos+1 < input.size() && digit(input[pos+1]))
        {
          floating = true; text += char(input[pos++]);
          while(digit(peek())) text += char(input[pos++]);
          if(peek() == 'e' || peek() == 'E')
          {
            text += char(input[pos++]);
            if(peek() == '+' || peek() == '-') text += char(input[pos++]);
            if(!digit(peek())) throw TermParseFailure{};
            while(digit(peek())) text += char(input[pos++]);
          }
        }
        // numberconst skips ASCII blanks, but leaves other whitespace in the tail.
        while(take(' ')) {}
        if(!floating) return integer(text.c_str());
        std::istringstream stream(text); stream.imbue(std::locale::classic());
        double value; stream >> value;
        if(stream.fail() || !std::isfinite(value)) throw TermParseFailure{};
        return float_(value);
      }
      bool alpha = letter(peek());
      if(!alpha && !opchar(peek())) throw TermParseFailure{};
      std::string name;
      if(alpha) { while(idchar(peek())) name += char(input[pos++]); }
      else { while(opchar(peek())) name += char(input[pos++]); }
      space();
      std::vector<Arg> args;
      if(application)
        while(!endargs()) { args.push_back(term(false)); space(); }
      return construct(name, args);
    }
  };

  tag_type readshow_step(RuntimeState *, Configuration * C)
  {
    Cursor root = C->cursor();
    // Local vectors and the printer's cycle set contain heap pointers.
    GcClamp clamp;
    try
    {
      Node * result;
      if(std::string(root->info->name) == "prim_showTerm")
      {
        auto text = TermPrinter{}.print(root[0].target);
        result = build_curry_string(text.c_str());
      }
      else
      {
        TermReader reader(root[0].target, root[1].target);
        try
        {
          auto value = reader.term();
          result = cons(pair(value, reader.tails[reader.pos]), nil());
        }
        catch(TermParseFailure const &) { result = nil(); }
      }
      root->forward_to(result);
      return T_FWD;
    }
    catch(std::exception const & error)
    {
      C->set_error(nullptr, error.what(), ErrorKind::evaluation);
      return E_ERROR;
    }
  }

  void primitive(char const * module, char const * name, int arity)
  {
    auto format = new char[arity + 1];
    std::fill_n(format, arity, 'p'); format[arity] = 0;
    auto info = new InfoTable(T_FUNC, arity, sizeof(void *) * std::max(arity + 1, 2),
        F_STATIC_OBJECT | F_MONADIC, name, format, step, nullptr);
    Module::register_primitive(std::string(module) + "." + name, info);
  }
  int register_packages()
  {
    for(auto name: {"prim_doesFileExist", "prim_doesDirectoryExist", "prim_fileSize",
        "prim_getModificationTime", "prim_setCurrentDirectory", "prim_getDirectoryContents",
        "prim_createDirectory", "prim_removeDirectory", "prim_removeFile"})
      primitive("System.Directory", name, 1);
    primitive("System.Directory", "getCurrentDirectory", 0);
    primitive("System.Directory", "prim_renameDirectory", 2);
    primitive("System.Directory", "prim_renameFile", 2);
    primitive("System.Process", "prim_system", 1);
    primitive("System.Process", "prim_sleep", 1);
    static InfoTable const show(T_FUNC, 1, sizeof(Node1), F_STATIC_OBJECT,
        "prim_showTerm", "p", readshow_step, nullptr);
    static InfoTable const reads(T_FUNC, 2, sizeof(Node2), F_STATIC_OBJECT,
        "prim_readsUnqualifiedTerm", "pp", readshow_step, nullptr);
    Module::register_primitive("ReadShowTerm.prim_showTerm", &show);
    Module::register_primitive("ReadShowTerm.prim_readsUnqualifiedTerm", &reads);
    return 0;
  }
  int const registered = register_packages();
}
