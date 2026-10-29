#include "curryrt/platform.hpp"
#include <cerrno>
#include <cstring>

#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <process.h>
#include <malloc.h>
#include <cstring>
#else
#include <pthread.h>
#include <dlfcn.h>
#include <unistd.h>
#include <sys/resource.h>
#include <cstdint>
#include <cstdlib>
#endif

namespace curryrt { namespace platform {

#if defined(_WIN32)

  namespace
  {
    struct Start { void * (*main)(void *); void * arg; };

    unsigned __stdcall trampoline(void * raw)
    {
      Start start = *static_cast<Start *>(raw);
      delete static_cast<Start *>(raw);
      start.main(start.arg);
      return 0;
    }

    std::string last_error_text()
    {
      DWORD const code = GetLastError();
      char * text = nullptr;
      DWORD const n = FormatMessageA(
          FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS
        , nullptr, code, 0, reinterpret_cast<char *>(&text), 0, nullptr);
      std::string result = n && text ? std::string(text, n) : "error " + std::to_string(code);
      if(text) LocalFree(text);
      while(!result.empty() && (result.back() == '\n' || result.back() == '\r' || result.back() == ' '))
        result.pop_back();
      return result;
    }

    std::wstring widen(std::string const & text)
    {
      if(text.empty()) return std::wstring();
      int const n = MultiByteToWideChar(CP_UTF8, 0, text.data(), (int) text.size(), nullptr, 0);
      std::wstring wide(n, L'\0');
      MultiByteToWideChar(CP_UTF8, 0, text.data(), (int) text.size(), &wide[0], n);
      return wide;
    }
  }

  bool start(Thread & thread, size_t stack_size, void * (*main)(void *), void * arg, std::string * error)
  {
    auto * boxed = new Start{main, arg};
    // The stack size is a reservation, committed page by page as the thread
    // descends, as pthread_attr_setstacksize reserves on Linux.
    unsigned const flags = stack_size ? STACK_SIZE_PARAM_IS_A_RESERVATION : 0;
    uintptr_t const handle = _beginthreadex(nullptr, (unsigned) stack_size, trampoline, boxed, flags, nullptr);
    if(!handle)
    {
      delete boxed;
      if(error) *error = "cannot create a thread: " + std::string(std::strerror(errno));
      return false;
    }
    thread.handle = reinterpret_cast<void *>(handle);
    thread.started = true;
    return true;
  }

  void join(Thread & thread)
  {
    if(!thread.started) return;
    HANDLE const handle = reinterpret_cast<HANDLE>(thread.handle);
    WaitForSingleObject(handle, INFINITE);
    CloseHandle(handle);
    thread.handle = nullptr;
    thread.started = false;
  }

  void set_current_thread_name(char const * name)
  {
    // SetThreadDescription exists since Windows 10 1607; the import is
    // resolved at run time so that the runtime loads where it is absent.
    using Setter = HRESULT (WINAPI *)(HANDLE, PCWSTR);
    static Setter const setter = reinterpret_cast<Setter>(
        GetProcAddress(GetModuleHandleW(L"kernel32.dll"), "SetThreadDescription"));
    if(setter) setter(GetCurrentThread(), widen(name).c_str());
  }

  void at_fork(void (*)(), void (*)(), void (*)()) {}

  char const * stack_floor_of_this_thread()
  {
    ULONG_PTR low = 0, high = 0;
    GetCurrentThreadStackLimits(&low, &high);
    return reinterpret_cast<char const *>(low);
  }

  void * aligned_allocate(size_t alignment, size_t size) { return _aligned_malloc(size, alignment); }
  void aligned_release(void * memory) { _aligned_free(memory); }

  void * load(std::string const & path, std::string * error)
  {
    HMODULE const module = LoadLibraryExW(widen(path).c_str(), nullptr, LOAD_WITH_ALTERED_SEARCH_PATH);
    if(!module && error) *error = last_error_text();
    return module;
  }

  bool loaded(std::string const & path)
  {
    HMODULE module = nullptr;
    // GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT: a query, not a load.
    return GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, widen(path).c_str(), &module) && module;
  }

  void * symbol(void * handle, char const * name)
  {
    return reinterpret_cast<void *>(GetProcAddress(static_cast<HMODULE>(handle), name));
  }

  bool unload(void * handle, std::string * error)
  {
    if(FreeLibrary(static_cast<HMODULE>(handle))) return true;
    if(error) *error = last_error_text();
    return false;
  }

  std::string path_of_object_holding(void const * address)
  {
    HMODULE module = nullptr;
    if(!GetModuleHandleExW(
        GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT
      , reinterpret_cast<LPCWSTR>(address), &module))
      return std::string();
    wchar_t buffer[32768];
    DWORD const n = GetModuleFileNameW(module, buffer, 32768);
    if(!n || n >= 32768) return std::string();
    int const bytes = WideCharToMultiByte(CP_UTF8, 0, buffer, (int) n, nullptr, 0, nullptr, nullptr);
    std::string path(bytes, '\0');
    WideCharToMultiByte(CP_UTF8, 0, buffer, (int) n, &path[0], bytes, nullptr, nullptr);
    return path;
  }

  long long process_id() { return GetCurrentProcessId(); }

#else

  bool start(Thread & thread, size_t stack_size, void * (*main)(void *), void * arg, std::string * error)
  {
    pthread_attr_t attr;
    int rc = pthread_attr_init(&attr);
    if(rc == 0 && stack_size)
      rc = pthread_attr_setstacksize(&attr, stack_size);
    pthread_t id;
    if(rc == 0)
      rc = pthread_create(&id, &attr, main, arg);
    pthread_attr_destroy(&attr);
    if(rc != 0)
    {
      if(error) *error = "cannot create a thread: " + std::string(std::strerror(rc));
      return false;
    }
    thread.handle = new pthread_t(id);
    thread.started = true;
    return true;
  }

  void join(Thread & thread)
  {
    if(!thread.started) return;
    auto * id = static_cast<pthread_t *>(thread.handle);
    pthread_join(*id, nullptr);
    delete id;
    thread.handle = nullptr;
    thread.started = false;
  }

  void set_current_thread_name(char const * name)
  {
    #if defined(__APPLE__)
    pthread_setname_np(name);
    #elif defined(__linux__)
    pthread_setname_np(pthread_self(), name);
    #else
    (void) name;
    #endif
  }

  void at_fork(void (*prepare)(), void (*parent)(), void (*child)())
  {
    pthread_atfork(prepare, parent, child);
  }

  char const * stack_floor_of_this_thread()
  {
    #if defined(__linux__)
    pthread_attr_t attr;
    if(pthread_getattr_np(pthread_self(), &attr) == 0)
    {
      void * addr = nullptr;
      size_t size = 0;
      int const rc = pthread_attr_getstack(&attr, &addr, &size);
      pthread_attr_destroy(&attr);
      if(rc == 0 && addr)
        return static_cast<char const *>(addr);
    }
    #elif defined(__APPLE__)
    return static_cast<char const *>(pthread_get_stackaddr_np(pthread_self()))
        - pthread_get_stacksize_np(pthread_self());
    #endif
    struct rlimit limit;
    if(getrlimit(RLIMIT_STACK, &limit) == 0 && limit.rlim_cur != RLIM_INFINITY)
    {
      char probe;
      std::uintptr_t const here = (std::uintptr_t) &probe;
      if(here > limit.rlim_cur)
        return (char const *) (here - limit.rlim_cur);
    }
    return nullptr;
  }

  void * aligned_allocate(size_t alignment, size_t size) { return std::aligned_alloc(alignment, size); }
  void aligned_release(void * memory) { std::free(memory); }

  void * load(std::string const & path, std::string * error)
  {
    void * handle = dlopen(path.c_str(), RTLD_LAZY | RTLD_GLOBAL);
    if(!handle && error)
    {
      char const * msg = dlerror();
      *error = msg ? msg : "unknown error";
    }
    return handle;
  }

  bool loaded(std::string const & path)
  {
    if(void * mapped = dlopen(path.c_str(), RTLD_LAZY | RTLD_NOLOAD))
    {
      dlclose(mapped);
      return true;
    }
    return false;
  }

  void * symbol(void * handle, char const * name) { return dlsym(handle, name); }

  bool unload(void * handle, std::string * error)
  {
    if(dlclose(handle) == 0) return true;
    if(error)
    {
      char const * msg = dlerror();
      *error = msg ? msg : "unknown error";
    }
    return false;
  }

  std::string path_of_object_holding(void const * address)
  {
    Dl_info info;
    if(dladdr(const_cast<void *>(address), &info) && info.dli_fname)
      return info.dli_fname;
    return std::string();
  }

  long long process_id() { return getpid(); }

#endif
}}
