#include "curryrt/curryrt.hpp"
#include "curryrt/currylib/prelude.hpp"
#include "curryrt/module.hpp"
#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <thread>

using namespace curryrt;
namespace fs = std::filesystem;
namespace
{
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
        auto ctor = Module::find_symbol("Data.Time", "CTime");
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
    return 0;
  }
  int const registered = register_packages();
}
