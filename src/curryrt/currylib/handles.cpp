#include "curryrt/curryrt.hpp"
#include "curryrt/currylib/library.hpp"
#include "curryrt/currylib/prelude.hpp"
#include "curryrt/module.hpp"
#include "curryrt/utf8.hpp"
#include "curryrt/platform.hpp"
#include "curryrt/evaluation.hpp"
#include "curryrt/bigint.hpp"
#include <algorithm>
#include <fstream>
#include <filesystem>
#include <cstring>
#include <memory>
#include <stdexcept>
#include <cstdlib>
#include <unordered_set>
#include <mutex>
#include <thread>
#include <future>
#include <sstream>
#include <iostream>

using namespace curryrt;
namespace
{
  stream_hook & host() { static auto hook = new stream_hook; return *hook; }
  struct Handle
  {
    long long owner = platform::process_id();
    int standard = -1;
    bool readable = false, writable = false, closed = false, binary = false;
    std::fstream file;
    void close()
    {
      if(!closed) { file.close(); closed = true; }
    }
  };
  // Never acquire the heap or call the host while holding this mutex.
  // It serializes both registry lifetime and every native file operation.
  // Recursive acquisition permits finalization during a node allocation.
  auto *& handle_mutex_ptr()
  {
    static auto mutex = new std::recursive_mutex;
    return mutex;
  }
  auto & handle_mutex() { return *handle_mutex_ptr(); }
  auto *& retired_streams_ptr()
  {
    static auto streams = new std::vector<int>;
    return streams;
  }
  auto & retired_streams() { return *retired_streams_ptr(); }
  auto *& open_handles_ptr()
  {
    static auto handles = new std::unordered_set<Handle *>;
    return handles;
  }
  auto & open_handles() { return *open_handles_ptr(); }
  void child_handles()
  {
    // Inherited streams may be mid-operation. Neither destroy nor flush them.
    handle_mutex_ptr() = new std::recursive_mutex;
    open_handles_ptr() = new std::unordered_set<Handle *>;
    retired_streams_ptr() = new std::vector<int>;
  }
  struct ShutdownRegistration
  {
    ShutdownRegistration()
    {
      std::atexit(shutdown_handles);
      platform::at_fork(nullptr, nullptr, child_handles);
    }
  };
  ShutdownRegistration const shutdown_registration;
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
    auto h = (Handle *) node->successors()[0].blob;
    if((h->standard < 0 || h->standard >= 3) && h->owner != platform::process_id())
      throw std::runtime_error("handle belongs to another process; open it again");
    return h;
  }
  tag_type finish(Configuration * C, Node * value, bool monadic=true)
  {
    C->cursor()->forward_to(monadic ? io(value) : value);
    return T_FWD;
  }
  tag_type step(RuntimeState * rts, Configuration * C)
  {
    ForkWork work;
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
      std::unique_lock<std::recursive_mutex> lock(handle_mutex());
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
      if(op == "prim_openFile" || op == "prim_openBinaryFile")
      {
        std::string path = extract_string(root[0].target);
        auto mode = root[1].target->info->tag - T_CTOR;
        auto h = std::make_unique<Handle>();
        h->binary = op == "prim_openBinaryFile";
        h->readable = mode == 0;
        h->writable = mode != 0;
        h->file.open(std::filesystem::u8path(path), std::ios::binary | (mode == 0 ? std::ios::in :
            mode == 1 ? std::ios::out | std::ios::trunc : std::ios::out | std::ios::app));
        if(!h->file) throw std::runtime_error(path + ": " + std::strerror(errno));
        Node * node = Node::create(&handle_info, h.get());
        gc_register_handle(node);
        open_handles().insert(h.get());
        h.release();
        return finish(C, node);
      }
      if(op == "prim_execCmd" || op == "prim_connectToCmd")
      {
        auto command = extract_string(root[0].target);
        lock.unlock();
        bool duplex = op == "prim_connectToCmd";
        std::istringstream ids(standard_stream(-1, duplex ? "connect" : "exec", command, 0));
        Node * nodes[3];
        for(int i = 0; i < (duplex ? 1 : 3); ++i)
        {
          auto h = std::make_unique<Handle>();
          if(!(ids >> h->standard) || h->standard < 3)
            throw std::runtime_error("invalid command stream");
          h->readable = duplex || i != 0;
          h->writable = i == 0;
          std::lock_guard<std::recursive_mutex> guard(handle_mutex());
          nodes[i] = Node::create(&handle_info, h.get());
          gc_register_handle(nodes[i]);
          open_handles().insert(h.get());
          h.release();
        }
        if(duplex) return finish(C, nodes[0]);
        auto tuple = Module::find_symbol(rts->istate.modules, "Prelude", "(,,)");
        if(!tuple) throw std::runtime_error("Prelude tuple constructor is not loaded");
        return finish(C, Node::create(tuple, nodes[0], nodes[1], nodes[2]));
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
          if(!streams.empty()) streams += ',';
          streams += std::to_string(h->standard);
        }
        lock.unlock();
        return finish(C, int_(std::stoll(standard_stream(0, "waits", streams, timeout))));
      }
      auto h = handle(root[0].target);
      if((op == "prim_hGetByte" || op == "prim_hPutByte") && !h->binary)
        throw std::runtime_error("stream is not binary");
      if(h->binary && (op == "prim_hGetChar" || op == "prim_hPutChar"))
        throw std::runtime_error("stream is not text");
      if(h->closed && op != "prim_hClose")
        throw std::runtime_error("stream does not exist (closed handle)");
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
        int standard = h->standard;
        if(op == "prim_hClose" && standard >= 3) h->closed = true;
        lock.unlock();
        auto result = standard_stream(standard, op, text, value);
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
        h->close();
        return finish(C, unit());
      }
      if(h->closed) throw std::runtime_error("stream does not exist (closed handle)");
      if(op == "prim_hGetByte")
      {
        if(!h->readable) throw std::runtime_error("stream is not readable");
        auto value = h->file.get();
        if(value == EOF && !h->file.eof()) throw std::runtime_error("file read failed");
        return finish(C, int_(value == EOF ? -1 : value));
      }
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
      else if(op == "prim_hPutByte")
      {
        if(!h->writable) throw std::runtime_error("stream is not writable");
        auto value = root[1].target;
        if(is_bigint(value) || NodeU{value}.int_->value < 0 || NodeU{value}.int_->value > 255)
          throw std::runtime_error("byte is outside 0..255");
        h->file.put(static_cast<char>(NodeU{value}.int_->value));
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
      fork_check();
      C->set_error(Node::create(ioerror_info(rts, IO_ERROR), build_curry_string(exc.what())),
          std::string("i/o error: ") + exc.what(), ErrorKind::io);
      return E_ERROR;
    }
  }
  void release(Handle * h)
  {
    if(h->owner != platform::process_id() || fork_poisoned()) return;
    ForkWork work;
    std::lock_guard<std::recursive_mutex> lock(handle_mutex());
    if(h->standard < 0 || h->standard >= 3)
    {
      if(h->standard >= 3 && !h->closed) retired_streams().push_back(h->standard);
      open_handles().erase(h);
      h->close();
      delete h;
    }
  }
  void shutdown(std::function<void()> const & visit = {})
  {
    if(fork_poisoned()) return;
    ForkWork work;
    std::lock_guard<std::recursive_mutex> lock(handle_mutex());
    for(auto h: open_handles())
    {
      if(visit) visit();
      if(h->standard >= 3 && !h->closed) retired_streams().push_back(h->standard);
      h->close();
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
    for(auto entry: {std::pair<char const *, int>{"prim_openBinaryFile", 2},
                    {"prim_hGetByte", 1}, {"prim_hPutByte", 2}})
    {
      auto format = new char[entry.second + 1];
      std::fill_n(format, entry.second, 'p'); format[entry.second] = 0;
      auto info = new InfoTable(T_FUNC, entry.second,
          sizeof(void *) * std::max(entry.second + 1, 2),
          F_STATIC_OBJECT | F_MONADIC, entry.first, format, step, nullptr);
      Module::register_primitive(std::string("System.IO.BinaryFile.") + entry.first, info);
    }
    auto command = new InfoTable(T_FUNC, 1, sizeof(Node1),
        F_STATIC_OBJECT | F_MONADIC, "prim_execCmd", "p", step, nullptr);
    Module::register_primitive("System.IOExts.prim_execCmd", command);
    auto connect = new InfoTable(T_FUNC, 1, sizeof(Node1),
        F_STATIC_OBJECT | F_MONADIC, "prim_connectToCmd", "p", step, nullptr);
    Module::register_primitive("System.IOExts.prim_connectToCmd", connect);
    return 0;
  }
  int const registered = register_handles();
}
namespace curryrt
{
  bool test_handle_mutex_held()
  {
    if(!handle_mutex().try_lock()) return true;
    handle_mutex().unlock();
    return false;
  }
  bool is_handle(InfoTable const * info) { return info == &handle_info; }
  void release_handle(Node * node)
  {
    release((Handle *) node->successors()[0].blob);
  }
  void shutdown_handles() { shutdown(); }
  bool test_handle_shutdown_race()
  {
    // A native-only hook pauses the walk while release attempts the same
    // mutex. No Python callback, GIL, or heap access participates in the walk.
    auto h = new Handle;
    {
      std::lock_guard<std::recursive_mutex> lock(handle_mutex());
      open_handles().insert(h);
    }
    std::promise<void> visiting, attempted, resume;
    auto ready = visiting.get_future();
    auto trying = attempted.get_future();
    auto proceed = resume.get_future();
    bool blocked = false;
    std::thread walker([&] {
      bool first = true;
      shutdown([&] {
        if(first) { first = false; visiting.set_value(); proceed.wait(); }
      });
    });
    ready.wait();
    std::thread collector([&] {
      // try_lock proves exclusion deterministically while the hook is held.
      blocked = !handle_mutex().try_lock();
      if(!blocked) handle_mutex().unlock();
      attempted.set_value();
      release(h);
    });
    trying.wait();
    resume.set_value();
    walker.join();
    collector.join();
    return blocked;
  }
  void set_stream_hook(stream_hook hook) { host() = std::move(hook); }
  std::string standard_stream(int stream, std::string const & operation,
                              std::string const & text, long long value)
  {
    if(!host()) throw std::runtime_error("standard stream host is unavailable");
    std::vector<int> retired;
    {
      std::lock_guard<std::recursive_mutex> lock(handle_mutex());
      retired.swap(retired_streams());
    }
    for(int id: retired)
    {
      try { host()(id, "release", "", 0); }
      catch(std::exception const & error)
      { std::cerr << "Hosted stream finalizer failed: " << error.what() << '\n'; }
      catch(...)
      { std::cerr << "Hosted stream finalizer failed: unknown error\n"; }
    }
    return host()(stream, operation, text, value);
  }
}
