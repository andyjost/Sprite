#include "curryrt/curryrt.hpp"
#include "curryrt/currylib/prelude.hpp"
#include "curryrt/currylib/library.hpp"
#include "curryrt/module.hpp"
#include "curryrt/platform.hpp"
#include <chrono>
#include <ctime>
#include <cstdlib>
#include <cstring>
#include <algorithm>

using namespace curryrt;

namespace
{
  std::string install_prefix;
  auto const start = std::chrono::steady_clock::now();

  tag_type finish(Configuration * C, Node * value, bool monadic=true)
  {
    C->cursor()->forward_to(monadic ? io(value) : value);
    return T_FWD;
  }

  tag_type io_error(Configuration * C, int code)
  {
    std::string message = std::strerror(code);
    C->set_error(Node::create(ioerror_info(IO_ERROR),
        build_curry_string(message.c_str())), "i/o error: " + message,
        ErrorKind::io);
    return E_ERROR;
  }

  tag_type distribution(RuntimeState *, Configuration * C)
  {
    std::string name = C->cursor()->info->name;
    Node * value;
    if(name == "curryCompiler" || name == "curryRuntime")
      value = build_curry_string("sprite");
    else if(name == "baseVersion")
      value = build_curry_string(SPRITE_BASE_VERSION);
    else if(name == "installDir")
      value = build_curry_string(install_prefix.c_str());
    else if(name.find("Major") != std::string::npos)
      value = int_(SPRITE_VERSION_MAJOR);
    else if(name.find("Minor") != std::string::npos)
      value = int_(SPRITE_VERSION_MINOR);
    else
      value = int_(SPRITE_VERSION_PATCH);
    return finish(C, value, false);
  }

  tag_type cpu_time(RuntimeState *, Configuration * C)
  {
    auto ticks = std::clock();
    return finish(C, int_(ticks < 0 ? 0 :
        static_cast<unboxed_int_type>(1000.0 * ticks / CLOCKS_PER_SEC)));
  }

  tag_type elapsed_time(RuntimeState *, Configuration * C)
  {
    return finish(C, int_(std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - start).count()));
  }

  tag_type windows(RuntimeState *, Configuration * C)
  {
#if defined(_WIN32)
    return finish(C, true_(), false);
#else
    return finish(C, false_(), false);
#endif
  }

  tag_type environment(RuntimeState *, Configuration * C)
  {
    Cursor root = C->cursor();
    // The Curry wrappers normalize the complete strings before this step.
    std::string name = extract_string(root[0].target);
    std::string operation = root->info->name;
    if(operation == "prim_getEnviron")
    {
      auto value = std::getenv(name.c_str());
      return finish(C, build_curry_string(value ? value : ""));
    }
    int error;
    if(name.empty() || name.find('=') != std::string::npos ||
        name.find('\0') != std::string::npos)
      error = EINVAL;
    else if(operation == "prim_setEnviron")
    {
      std::string value = extract_string(root[1].target);
      error = value.find('\0') != std::string::npos ? EINVAL :
          platform::set_environment(name, value);
    }
    else
      error = platform::unset_environment(name);
    return error ? io_error(C, error) : finish(C, unit());
  }

  extern DataType const ref_type;
  InfoTable const ref_info{T_CTOR, 1, sizeof(Node1), F_STATIC_OBJECT,
      "IORef", "p", nullptr, &ref_type};
  InfoTable const * const ref_ctors[] = {&ref_info};
  DataType const ref_type{ref_ctors, 1, 't', F_STATIC_OBJECT, "IORef"};

  tag_type new_ref(RuntimeState *, Configuration * C)
  {
    return finish(C, Node::create(&ref_info, C->cursor()[0].rvalue()));
  }

  tag_type read_ref(RuntimeState * rts, Configuration * C)
  {
    Variable ref = C->cursor()[0];
    auto tag = rts->hnf(C, &ref);
    if(tag < T_CTOR) return tag;
    return finish(C, ref.successor_node(0));
  }

  tag_type write_ref(RuntimeState * rts, Configuration * C)
  {
    Variable ref = C->cursor()[0];
    auto tag = rts->hnf(C, &ref);
    if(tag < T_CTOR) return tag;
    ref.set_successor(0, C->cursor()[1].rvalue());
    return finish(C, unit());
  }

  void primitive(char const * module, char const * name, index_type arity,
                 stepfunc_type step, bool monadic=true)
  {
    // Tables live for the process, just as the static Prelude tables do.
    auto format = new char[arity + 1];
    std::fill_n(format, arity, 'p');
    format[arity] = 0;
    auto info = new InfoTable(T_FUNC, arity,
        sizeof(void *) * std::max<int>(arity + 1, 2),
        F_STATIC_OBJECT | (monadic ? F_MONADIC : 0), name, format, step, nullptr);
    Module::register_primitive(std::string(module) + "." + name, info);
  }

  int register_library()
  {
    for(auto name: {"curryCompiler", "curryCompilerMajorVersion",
        "curryCompilerMinorVersion", "curryCompilerRevisionVersion",
        "curryRuntime", "curryRuntimeMajorVersion", "curryRuntimeMinorVersion",
        "baseVersion", "installDir"})
      primitive("Curry.Compiler.Distribution", name, 0, distribution, false);
    primitive("System.CPUTime", "getCPUTime", 0, cpu_time);
    primitive("System.CPUTime", "getElapsedTime", 0, elapsed_time);
    primitive("System.Environment", "isWindows", 0, windows, false);
    primitive("System.Environment", "prim_getEnviron", 1, environment);
    primitive("System.Environment", "prim_setEnviron", 2, environment);
    primitive("System.Environment", "prim_unsetEnviron", 1, environment);
    Module::register_builtin_module("Data.IORef", {{"IORef", &ref_type}},
        {{"IORef", &ref_info}});
    primitive("Data.IORef", "newIORef", 1, new_ref);
    primitive("Data.IORef", "prim_readIORef", 1, read_ref);
    primitive("Data.IORef", "prim_writeIORef", 2, write_ref);
    return 0;
  }
  int const registered = register_library();
}

namespace curryrt
{
  bool is_io_ref(InfoTable const * info) { return info == &ref_info; }

  void set_install_prefix(std::string const & prefix) { install_prefix = prefix; }
}
