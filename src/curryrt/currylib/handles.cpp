#include "curryrt/curryrt.hpp"
#include "curryrt/currylib/library.hpp"
#include "curryrt/currylib/prelude.hpp"
#include "curryrt/module.hpp"
#include "curryrt/utf8.hpp"
#include <algorithm>
#include <fstream>
#include <filesystem>
#include <cstring>
#include <memory>
#include <stdexcept>

using namespace curryrt;
namespace
{
  stream_hook & host() { static auto hook = new stream_hook; return *hook; }
  struct Handle
  {
    int standard = -1;
    bool readable = false, writable = false, closed = false;
    std::fstream file;
  };
  extern DataType const handle_type;
  InfoTable const handle_info{T_CTOR, 1, sizeof(Node1), F_STATIC_OBJECT | F_OPAQUE,
      "Handle", "x", nullptr, &handle_type};
  InfoTable const * const handle_ctors[] = {&handle_info};
  DataType const handle_type{handle_ctors, 1, 't', F_STATIC_OBJECT, "Handle"};
  Handle & standard_handle(int index)
  {
    static Handle handles[3];
    handles[index].standard = index;
    return handles[index];
  }
  Handle * handle(Node * node)
  {
    if(node->info != &handle_info) throw std::runtime_error("invalid handle");
    return (Handle *) node->successors()[0].blob;
  }
  tag_type finish(Configuration * C, Node * value, bool monadic=true)
  {
    C->cursor()->forward_to(monadic ? io(value) : value);
    return T_FWD;
  }
  tag_type step(RuntimeState * rts, Configuration * C)
  {
    Cursor root = C->cursor();
    std::string op = root->info->name;
    // Even direct calls through the API must force primitive arguments.
    for(index_type i=0; i<root->info->arity; ++i)
    {
      Variable arg = root[i];
      auto tag = rts->hnf(C, &arg);
      if(tag < T_CTOR) return tag;
    }
    try
    {
      if(op == "stdin" || op == "stdout" || op == "stderr")
      {
        auto & h = standard_handle(op == "stdin" ? 0 : op == "stdout" ? 1 : 2);
        Node * node = Node::create(&handle_info, &h);
        gc_register_handle(node);
        return finish(C, node, false);
      }
      if(op == "handle_eq")
        return finish(C, handle(root[0].target) == handle(root[1].target) ?
            true_() : false_(), false);
      if(op == "prim_openFile")
      {
        std::string path = extract_string(root[0].target);
        auto mode = root[1].target->info->tag - T_CTOR;
        auto h = std::make_unique<Handle>();
        h->readable = mode == 0;
        h->writable = mode != 0;
        h->file.open(std::filesystem::u8path(path), std::ios::binary | (mode == 0 ? std::ios::in :
            mode == 1 ? std::ios::out | std::ios::trunc : std::ios::out | std::ios::app));
        if(!h->file) throw std::runtime_error(path + ": " + std::strerror(errno));
        Node * node = Node::create(&handle_info, h.get());
        gc_register_handle(node);
        h.release();
        return finish(C, node);
      }
      if(op == "prim_hWaitForInputs")
      {
        // File streams are regular files; standard input uses the host's wait.
        Cursor list = root[0].target;
        std::vector<Handle *> handles;
        while(list->info != &Nil_Info)
        {
          handles.push_back(handle(list[0].target));
          list = list[1].target;
        }
        long long timeout = NodeU{root[1].target}.int_->value;
        // One host call waits for all streams rather than serial timeouts.
        std::string streams;
        for(size_t i=0; i<handles.size(); ++i)
        {
          auto h = handles[i];
          if(h->closed || (h->standard < 0 && !h->readable))
            throw std::runtime_error("handle is closed or not readable");
          if(h->standard < 0) return finish(C, int_(i));
          streams += char('0' + h->standard);
        }
        return finish(C, int_(std::stoll(standard_stream(0, "waits", streams, timeout))));
      }
      auto h = handle(root[0].target);
      if(h->standard >= 0)
      {
        std::string text;
        long long value = 0;
        if(op == "prim_hPutChar")
        {
          char buf[MAX_UTF8_LENGTH];
          auto n = utf8_encode(buf, NodeU{root[1].target}.char_->value);
          text.assign(buf, n);
        }
        if(op == "prim_hSeek")
        {
          text = std::to_string(root[1].target->info->tag - T_CTOR);
          value = NodeU{root[2].target}.int_->value;
        }
        if(op == "prim_hWaitForInput") value = NodeU{root[1].target}.int_->value;
        auto result = standard_stream(h->standard, op, text, value);
        if(op == "prim_hGetChar")
        {
          if(result.empty()) throw std::runtime_error("EOF");
          char const * p = result.data();
          return finish(C, char_(utf8_decode(p, p + result.size())));
        }
        if(op == "prim_hWaitForInput" || op == "prim_hIsEOF" ||
            op == "prim_hIsReadable" || op == "prim_hIsWritable" ||
            op == "prim_hIsTerminalDevice")
          return finish(C, result == "1" ? true_() : false_());
        return finish(C, unit());
      }
      // PAKCS deliberately ignores a second close.
      if(op == "prim_hClose")
      {
        if(!h->closed) { h->file.close(); h->closed = true; }
        return finish(C, unit());
      }
      if(h->closed) throw std::runtime_error("stream does not exist (closed handle)");
      if(op == "prim_hIsReadable") return finish(C, h->readable ? true_() : false_());
      if(op == "prim_hIsWritable") return finish(C, h->writable ? true_() : false_());
      if(op == "prim_hIsTerminalDevice") return finish(C, false_());
      if(op == "prim_hFlush")
      {
        if(!h->writable) return finish(C, unit());
        h->file.flush();
      }
      else if(op == "prim_hSeek")
      {
        auto mode = root[1].target->info->tag - T_CTOR;
        auto offset = NodeU{root[2].target}.int_->value;
        auto direction = mode == 0 ? std::ios::beg : mode == 1 ? std::ios::cur : std::ios::end;
        h->file.clear();
        if(h->readable) h->file.seekg(offset, direction);
        else h->file.seekp(offset, direction);
      }
      else if(op == "prim_hPutChar")
      {
        if(!h->writable) throw std::runtime_error("stream is not writable");
        char buf[MAX_UTF8_LENGTH];
        auto n = utf8_encode(buf, NodeU{root[1].target}.char_->value);
        h->file.write(buf, n);
      }
      else
      {
        if(!h->readable) throw std::runtime_error("stream is not readable");
        if(op == "prim_hWaitForInput") return finish(C, true_());
        int lead = h->file.peek();
        if(op == "prim_hIsEOF") return finish(C, lead == EOF ? true_() : false_());
        if(lead == EOF) throw std::runtime_error("EOF");
        char buf[MAX_UTF8_LENGTH];
        buf[0] = h->file.get();
        size_t n = 1, length = utf8_sequence_length((unsigned char) buf[0]);
        while(n < length)
        {
          int byte = h->file.peek();
          if(byte == EOF || (byte & 0xc0) != 0x80) break;
          buf[n++] = h->file.get();
        }
        char const * p = buf;
        return finish(C, char_(utf8_decode(p, buf + n)));
      }
      if(!h->file) throw std::runtime_error("stream operation failed");
      return finish(C, unit());
    }
    catch(std::exception const & exc)
    {
      C->set_error(Node::create(ioerror_info(IO_ERROR), build_curry_string(exc.what())),
          std::string("i/o error: ") + exc.what(), ErrorKind::io);
      return E_ERROR;
    }
  }
  int register_handles()
  {
    Module::register_builtin_module("System.IO", {{"Handle", &handle_type}},
        {{"Handle", &handle_info}});
    for(auto entry: {std::pair<char const *, int>{"handle_eq", 2},
        {"stdin", 0}, {"stdout", 0}, {"stderr", 0}, {"prim_openFile", 2},
        {"prim_hClose", 1}, {"prim_hFlush", 1}, {"prim_hIsEOF", 1},
        {"prim_hSeek", 3}, {"prim_hWaitForInput", 2}, {"prim_hWaitForInputs", 2},
        {"prim_hGetChar", 1}, {"prim_hPutChar", 2}, {"prim_hIsReadable", 1},
        {"prim_hIsWritable", 1}, {"prim_hIsTerminalDevice", 1}})
    {
      auto format = new char[entry.second + 1];
      std::fill_n(format, entry.second, 'p'); format[entry.second] = 0;
      bool monadic = std::string(entry.first).find("prim_") == 0;
      auto info = new InfoTable(T_FUNC, entry.second,
          sizeof(void *) * std::max(entry.second + 1, 2),
          F_STATIC_OBJECT | (monadic ? F_MONADIC : 0), entry.first, format, step, nullptr);
      Module::register_primitive(std::string("System.IO.") + entry.first, info);
    }
    return 0;
  }
  int const registered = register_handles();
}
namespace curryrt
{
  bool is_handle(InfoTable const * info) { return info == &handle_info; }
  void release_handle(Node * node)
  {
    auto h = handle(node);
    if(h->standard < 0) delete h;
  }
  void set_stream_hook(stream_hook hook) { host() = std::move(hook); }
  std::string standard_stream(int stream, std::string const & operation,
                              std::string const & text, long long value)
  {
    if(!host()) throw std::runtime_error("standard stream host is unavailable");
    return host()(stream, operation, text, value);
  }
}
