#include <algorithm>
#include <array>
#include <atomic>
#include <cerrno>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <condition_variable>
#include <cstring>
#include <deque>
#include <filesystem>
#include <fstream>
#include <mutex>
#include <sstream>
#include <system_error>
#include <thread>
#include <unordered_map>
#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#else
#include <fcntl.h>
#include <signal.h>
#include <spawn.h>
#include <sys/stat.h>
#include <sys/file.h>
#include <sys/wait.h>
#include <unistd.h>
#endif
#include "curryrt/platform.hpp"
#include "curryrt/dynload.hpp"
#include "curryrt/exceptions.hpp"
#include "curryrt/module.hpp"
#include "curryrt/tiered.hpp"
#include "curryrt/icurry.hpp"
#include "curryrt/evaluation.hpp"

#if !defined(_WIN32)
extern char ** environ;
#endif

// The worker thread and the swap of tiered execution.  See tiered.hpp.
namespace curryrt
{
  std::atomic<bool> g_tiered_pending{false};

  namespace
  {
    using JobKey = std::pair<size_t, std::string>;

    struct Finished
    {
      TieredJob   job;
      uint64_t    generation;
      int         status;   // the exit status of the compile; 0 is success
      double      seconds;
      std::string error;    // set when a command could not run
      std::string output;
    };

    // The state shared with the worker thread.  It is made once and never
    // destroyed: the worker waits on the condition variable for the life of
    // the process, and the destructor of a condition variable blocks until
    // its waiters left, which would hang the exit of the process.
    struct Shared
    {
      std::unordered_map<InfoTable const *, JobKey> hot_modules;
      std::map<JobKey, TieredJob> hot_jobs;
      std::mutex                mutex;
      std::condition_variable   work_cv;  // the worker waits here for a job
      std::condition_variable   idle_cv;  // waiters of tiered_wait
      std::deque<TieredJob>     queue;
      std::deque<Finished>      finished;
      std::vector<TieredResult> results;
      TieredStatus              counts;
      bool                      thread_started = false;
      bool                      running = false;
      size_t                    running_registry = 0;
      long long                 child = 0;   // POSIX pid, or a Windows Child pointer
      // Incremented by tiered_cancel.  A job of an older generation is
      // dropped when it finishes.
      uint64_t                  generation = 0;
    };

    Shared *& shared_ptr()
    {
      static Shared * instance = new Shared;
      return instance;
    }
    Shared & shared() { return *shared_ptr(); }

    std::string errno_text(char const * what)
    {
      return std::string(what) + ": " + std::strerror(errno);
    }

    // Reads the output file of a job, at most 32 KiB of it, and removes it.
    std::string take_output(std::string const & logfile)
    {
      std::string text;
      if(logfile.empty())
        return text;
      std::ifstream stream(logfile);
      if(stream)
      {
        std::stringstream ss;
        ss << stream.rdbuf();
        text = ss.str();
        if(text.size() > 32768)
          text = text.substr(0, 32768) + "\n...";
      }
      std::error_code ignored;
      std::filesystem::remove(logfile, ignored);
      return text;
    }

    std::vector<char *> pointers(std::vector<std::string> & strings)
    {
      std::vector<char *> out;
      for(auto & s: strings)
        out.push_back(&s[0]);
      out.push_back(nullptr);
      return out;
    }

#if defined(_WIN32)
    // Keep the compiler and its descendants in a job: cancelling a session
    // must also stop clang-cl and the linker started by the Python child.
    struct Child { HANDLE process; HANDLE job; };

    std::wstring widen(std::string const & text)
    {
      int size = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS,
                                    text.data(), int(text.size()), nullptr, 0);
      std::wstring result(size, L'\0');
      MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, text.data(),
                          int(text.size()), result.data(), size);
      return result;
    }

    // The quoting rules of the Microsoft C runtime (including trailing
    // backslashes and embedded quotes); CreateProcess takes one command line.
    std::wstring quote(std::string const & arg)
    {
      std::wstring out = L"\"";
      unsigned slashes = 0;
      for(auto ch: widen(arg))
      {
        if(ch == L'\\') { ++slashes; continue; }
        out.append(ch == L'"' ? 2 * slashes + 1 : slashes, L'\\');
        slashes = 0;
        out += ch;
      }
      out.append(2 * slashes, L'\\');
      return out + L"\"";
    }

    long long spawn(
        std::vector<std::string> argv, std::vector<std::string> envp
      , std::string const & logfile, std::string * error
      )
    {
      if(argv.empty()) { *error = "an empty command"; return 0; }
      std::wstring command;
      for(auto const & arg: argv)
      {
        if(!command.empty()) command += L' ';
        command += quote(arg);
      }
      // Windows requires the environment block sorted without regard to case.
      std::vector<std::wstring> variables;
      for(auto const & entry: envp) variables.push_back(widen(entry));
      std::sort(variables.begin(), variables.end(), [](auto const & a, auto const & b) {
        return _wcsicmp(a.c_str(), b.c_str()) < 0;
      });
      std::wstring environment;
      for(auto const & entry: variables) { environment += entry; environment += L'\0'; }
      environment += L'\0';
      SECURITY_ATTRIBUTES security{sizeof(SECURITY_ATTRIBUTES), nullptr, TRUE};
      HANDLE input = CreateFileW(L"NUL", GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE,
                                &security, OPEN_EXISTING, 0, nullptr);
      HANDLE output = CreateFileW(logfile.empty() ? L"NUL" : widen(logfile).c_str(),
          FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE, &security,
          OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
      HANDLE job = CreateJobObjectW(nullptr, nullptr);
      JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits{};
      limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
      bool ready = input != INVALID_HANDLE_VALUE && output != INVALID_HANDLE_VALUE
          && job && SetInformationJobObject(job, JobObjectExtendedLimitInformation,
                                            &limits, sizeof(limits));
      STARTUPINFOW startup{};
      startup.cb = sizeof(startup);
      startup.dwFlags = STARTF_USESTDHANDLES;
      startup.hStdInput = input;
      startup.hStdOutput = startup.hStdError = output;
      PROCESS_INFORMATION process{};
      bool started = ready && CreateProcessW(nullptr, command.data(), nullptr, nullptr,
          TRUE, CREATE_SUSPENDED | CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT,
          envp.empty() ? nullptr : environment.data(), nullptr, &startup, &process);
      DWORD failure = GetLastError();
      if(started && !AssignProcessToJobObject(job, process.hProcess))
      { failure = GetLastError(); TerminateProcess(process.hProcess, 1); started = false; }
      if(started && ResumeThread(process.hThread) == DWORD(-1))
      { failure = GetLastError(); TerminateJobObject(job, 1); started = false; }
      if(input != INVALID_HANDLE_VALUE) CloseHandle(input);
      if(output != INVALID_HANDLE_VALUE) CloseHandle(output);
      if(process.hThread) CloseHandle(process.hThread);
      if(!started)
      {
        if(process.hProcess) CloseHandle(process.hProcess);
        if(job) CloseHandle(job);
        *error = "cannot start compile (Windows error " + std::to_string(failure) + ")";
        return 0;
      }
      return reinterpret_cast<long long>(new Child{process.hProcess, job});
    }

    int wait_status(long long child)
    {
      auto process = reinterpret_cast<Child *>(child)->process;
      if(WaitForSingleObject(process, INFINITE) != WAIT_OBJECT_0) return -1;
      DWORD status = 0;
      return GetExitCodeProcess(process, &status) ? int(status) : -1;
    }

    void close_child(long long child)
    {
      auto ptr = reinterpret_cast<Child *>(child);
      CloseHandle(ptr->process);
      CloseHandle(ptr->job);
      delete ptr;
    }
#else
    // Starts a command with its output appended to ``logfile`` and no input.
    // Returns the process id, or zero with ``error`` set.
    long long spawn(
        std::vector<std::string> argv, std::vector<std::string> envp
      , std::string const & logfile, std::string * error
      )
    {
      if(argv.empty())
      {
        *error = "an empty command";
        return 0;
      }
      posix_spawn_file_actions_t actions;
      posix_spawn_file_actions_init(&actions);
      posix_spawn_file_actions_addopen(
          &actions, 0, "/dev/null", O_RDONLY, 0
        );
      if(!logfile.empty())
      {
        posix_spawn_file_actions_addopen(
            &actions, 1, logfile.c_str(), O_WRONLY | O_CREAT | O_APPEND, 0644
          );
        posix_spawn_file_actions_adddup2(&actions, 1, 2);
      }
      // The child leads a process group of its own, so that tiered_cancel
      // reaches the compiler it starts as well.
      posix_spawnattr_t attr;
      posix_spawnattr_init(&attr);
      posix_spawnattr_setflags(&attr, POSIX_SPAWN_SETPGROUP);
      posix_spawnattr_setpgroup(&attr, 0);
      auto argv_ = pointers(argv);
      auto envp_ = pointers(envp);
      pid_t pid = 0;
      int rc = posix_spawnp(
          &pid, argv[0].c_str(), &actions, &attr, argv_.data()
        , envp.empty() ? environ : envp_.data()
        );
      posix_spawnattr_destroy(&attr);
      posix_spawn_file_actions_destroy(&actions);
      if(rc != 0)
      {
        errno = rc;
        *error = errno_text(("cannot start " + argv[0]).c_str());
        return 0;
      }
      return pid;
    }

    // Waits for a child.  Returns its exit status, or 128 plus the signal.
    int wait_status(long long child)
    {
      pid_t const pid = (pid_t) child;
      int status = 0;
      while(waitpid(pid, &status, 0) < 0)
        if(errno != EINTR)
          return -1;
      if(WIFEXITED(status))
        return WEXITSTATUS(status);
      if(WIFSIGNALED(status))
        return 128 + WTERMSIG(status);
      return -1;
    }

#endif

    // Runs a command to its end.  Returns the exit status; -1 when it could
    // not run.  A command of a job (``generation`` set) is started under the
    // lock, so that tiered_cancel either sees the child on record or
    // precedes the start, in which case the command does not run.
    int run(
        std::vector<std::string> const & argv
      , std::vector<std::string> const & envp, std::string const & logfile
      , std::string * error, uint64_t const * generation
      )
    {
      long long pid = 0;
      {
        std::lock_guard<std::mutex> lock(shared().mutex);
        if(generation && *generation != shared().generation)
        {
          *error = "cancelled";
          return -1;
        }
        pid = spawn(argv, envp, logfile, error);
        if(!pid)
          return -1;
        if(generation)
          shared().child = pid;
      }
      int status = wait_status(pid);
      if(generation)
      {
        std::lock_guard<std::mutex> lock(shared().mutex);
        shared().child = 0;
#if defined(_WIN32)
        close_child(pid);
#endif
      }
#if defined(_WIN32)
      else close_child(pid);
#endif
      return status;
    }

    bool file_exists(std::string const & filename)
    {
      std::error_code error;
      return std::filesystem::exists(std::filesystem::u8path(filename), error);
    }

    // The table of the CRC-32 (the polynomial of zlib), made on first use.
    std::array<uint32_t, 256> const & crc_table()
    {
      static std::array<uint32_t, 256> const table = []{
        std::array<uint32_t, 256> t{};
        for(uint32_t i=0; i<256; ++i)
        {
          uint32_t c = i;
          for(int k=0; k<8; ++k)
            c = (c & 1) ? (0xEDB88320u ^ (c >> 1)) : (c >> 1);
          t[i] = c;
        }
        return t;
      }();
      return table;
    }

    void worker()
    {
      while(true)
      {
        TieredJob job;
        uint64_t generation;
        {
          std::unique_lock<std::mutex> lock(shared().mutex);
          shared().work_cv.wait(lock, []{ return !shared().queue.empty(); });
          job = std::move(shared().queue.front());
          shared().queue.pop_front();
          shared().running = true;
          shared().running_registry = job.registry.storage->id;
          generation = shared().generation;
        }
        Finished done{std::move(job), generation, -1, 0.0, {}, {}};
        auto const t0 = std::chrono::steady_clock::now();
        done.status = run(
            done.job.argv, done.job.envp, done.job.logfile, &done.error
          , &generation
          );
        done.output = take_output(done.job.logfile);
        done.seconds = std::chrono::duration<double>(
            std::chrono::steady_clock::now() - t0
          ).count();
        {
          std::lock_guard<std::mutex> lock(shared().mutex);
          fork_work_end(platform::process_id());
          shared().running = false;
          if(generation == shared().generation)
          {
            shared().finished.push_back(std::move(done));
            g_tiered_pending.store(true);
            g_icurry_posted.store(true, std::memory_order_release);
          }
        }
        shared().idle_cv.notify_all();
      }
    }

    // Starts the worker thread once.  Returns false with ``error`` set when
    // the thread cannot start (EAGAIN under a limit on the tasks of the
    // user): the caller records the job as a compile that could not run,
    // the module stays interpreted, and the evaluation that reached the
    // threshold goes on.
    bool start_worker(std::string * error)
    {
      if(!shared().thread_started)
      {
        try
          { std::thread(worker).detach(); }
        catch(std::system_error const & e)
        {
          *error = std::string("cannot start the compile thread (") + e.what() + ")";
          return false;
        }
        shared().thread_started = true;
      }
      return true;
    }

    // Called under the mutex.  Records ``job`` as a compile that could not
    // run, for the next poll (tiered_apply_pending).
    void fail_job(TieredJob job, std::string error)
    {
      shared().finished.push_back(Finished{
          std::move(job), shared().generation, -1, 0.0, std::move(error), {}
        });
      g_tiered_pending.store(true);
      g_icurry_posted.store(true, std::memory_order_release);
    }

    // POSIX dlopen caches pathname strings even after atomic replacement.
    // A distinct spelling opens the canonical inode without a link or copy.
    void * open_object(
        std::string const & sofile, std::string & loadpath, std::string * error
      )
    {
      loadpath = sofile;
#if defined(_WIN32)
      if(platform::loaded(sofile))
      {
        *error = "the object is mapped under this name in this process; "
                 "the new object loads in the next process";
        return nullptr;
      }
#else
      if(platform::loaded(sofile))
      {
        static std::atomic<unsigned long long> generation{0};
        auto file = std::filesystem::absolute(std::filesystem::u8path(sofile));
        std::string alias = file.parent_path().u8string() + "/";
        // Encode the counter in separator runs between dot components.
        // The spelling grows logarithmically, rather than one dot per load.
        for(auto n = ++generation; n; n >>= 1)
          alias += (n & 1) ? ".//" : "./";
        loadpath = alias + file.filename().u8string();
      }
#endif
      // The first dlopen maps the object; the binding of its load, which
      // follows (SharedCurryModule), may give kept tables steps that point
      // into it.  The handle is never closed on a failure after this
      // point, so the object stays mapped.
      std::string msg;
      void * raw = platform::load(loadpath, &msg);
      if(!raw)
      {
        *error = "cannot load the object: " + msg;
      }
      return raw;
    }

    // Use the same module lock as the Python product writers.
    struct ProductLock
    {
#if defined(_WIN32)
      HANDLE handle = INVALID_HANDLE_VALUE;
      OVERLAPPED overlap{};
#else
      int handle = -1;
#endif
      bool acquired = false;
      explicit ProductLock(std::string const & object)
      {
        auto path = std::filesystem::u8path(object);
        path.replace_extension(".lock");
#if defined(_WIN32)
        handle = CreateFileW(path.c_str(), GENERIC_READ | GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr, OPEN_ALWAYS,
            FILE_ATTRIBUTE_NORMAL, nullptr);
        if(handle != INVALID_HANDLE_VALUE)
          acquired = LockFileEx(handle, LOCKFILE_EXCLUSIVE_LOCK | LOCKFILE_FAIL_IMMEDIATELY, 0, 1, 0, &overlap);
#else
        handle = ::open(path.c_str(), O_RDWR | O_CREAT, 0666);
        if(handle >= 0)
        {
          int status;
          do { status = flock(handle, LOCK_EX | LOCK_NB); } while(status < 0 && errno == EINTR);
          acquired = status == 0;
        }
#endif
      }
      ~ProductLock()
      {
#if defined(_WIN32)
        if(handle != INVALID_HANDLE_VALUE) CloseHandle(handle);
#else
        if(handle >= 0) close(handle);
#endif
      }
    };

    // Publishes the products of a private compile beside the source (see
    // TieredJob::publish): the generated file, the object, then the
    // ABI stamp, each copied under a temporary name in the target directory
    // and renamed into place, when the source's ICurry file is the one of
    // the import and the directory exists. Returns the private path to open
    // whether publication succeeds or the directory was removed (issue #173).
    // Runs on the thread of the swap, so the files beside the source
    // change only at a safepoint of
    // the interpreter.
    std::string publish_products(
        std::string const & sofile, std::string const & publish
      , std::string const & icurryfile, std::string const & digest
      )
    {
      if(publish.empty() || publish == sofile)
        return sofile;
      namespace fs = std::filesystem;
      std::error_code ec;
      fs::path directory = fs::path(publish).parent_path();
      if(platform::loaded(publish)) return sofile;
      if(icurryfile.empty() || !file_exists(icurryfile)
          || !fs::is_directory(directory, ec)
          || tiered_file_digest(icurryfile) != digest)
        return sofile;
      auto stem = [](std::string const & path)
      {
        auto source = fs::u8path(path);
        source.replace_extension();
        return source.u8string();
      };
      ProductLock lock(publish);
      if(!lock.acquired || !file_exists(icurryfile)
          || tiered_file_digest(icurryfile) != digest) return sofile;
      // A failed object replacement must not leave a new stamp on old code.
      fs::remove(fs::u8path(publish + ".abi"), ec);
      if(ec) return sofile;
      static std::atomic<unsigned> counter{0};
      std::pair<std::string, std::string> const pairs[] = {
          {stem(sofile) + ".cpp", stem(publish) + ".cpp"}
        , {sofile, publish}
        , {sofile + ".abi", publish + ".abi"}
        };
      for(auto const & pair: pairs)
      {
        if(!file_exists(pair.first))
          continue;
        fs::path target(pair.second);
        fs::path tmp = target.parent_path()
            / ("." + target.filename().string() + ".publish-"
               + std::to_string(platform::process_id()) + "-" + std::to_string(counter++));
        fs::copy_file(pair.first, tmp, fs::copy_options::overwrite_existing, ec);
        if(!ec)
        {
          if(pair.first == sofile)
          {
            std::string error;
            if(!platform::publish_object(tmp.u8string(), target.u8string(), &error))
              ec = std::make_error_code(std::errc::permission_denied);
          }
          else
          {
#if defined(_WIN32)
            if(!MoveFileExW(tmp.c_str(), target.c_str(), MOVEFILE_REPLACE_EXISTING))
              ec = std::error_code(GetLastError(), std::system_category());
#else
            fs::rename(tmp, target, ec);
#endif
          }
        }
        if(ec)
        {
          std::error_code ignored;
          fs::remove(tmp, ignored);
          return sofile;
        }
      }
      // Adoption keeps the generation built by this job. The canonical name
      // is available to other producers as soon as this lock is released.
      return sofile;
    }

    // Publish the binding owner before dlopen, restoring the old name if
    // the loader refuses the file before any slots can have been bound.
    struct Publication
    {
      std::shared_ptr<Module> module;
      std::shared_ptr<Module> previous;
      ModuleRegistry origin;
      bool mapped = false;
      explicit Publication(std::shared_ptr<Module> module)
        : module(module), origin(module ? module->registry : process_registry())
      {
        if(module)
        {
          previous = Module::find(process_registry(), module->name);
          module->publish();
        }
      }
      ~Publication()
      {
        if(module && !mapped && origin.storage != process_registry().storage)
        {
          module->registry = origin;
          auto & entries = process_registry().storage->modules;
          if(previous) entries[module->name] = previous;
          else entries.erase(module->name);
        }
      }
    };

    // Maps the object of an import of a job (see the imports in
    // tiered.hpp), unless the import has one: it was loaded from its
    // object, swapped, or mapped by an earlier swap.  Nothing when the
    // object does not exist: the load of the importer then reports what
    // it lacks.  An import without a module of its name in the registry
    // (none is expected) gets its object mapped all the same, and the
    // handle stays open, so that the object stays mapped.  Returns false
    // with the error of ``result`` set.
    bool map_import(ModuleRegistry const & registry, TieredJob::Import const & imp, TieredResult & result)
    {
      auto module = Module::find(registry, imp.module);
      if(module && module->shlib())
        return true;
      if(!file_exists(imp.sofile))
        return true;
      if(!imp.icurryfile.empty()
          && tiered_file_digest(imp.icurryfile) != imp.icurry_digest)
      {
        result.error = "the ICurry of the import " + imp.module
                     + " changed after the import";
        return false;
      }
      std::string const path = publish_products(
          imp.sofile, imp.publish, imp.icurryfile, imp.icurry_digest
        );
      std::string loadpath;
      Publication publication(module);
      void * raw = open_object(path, loadpath, &result.error);
      publication.mapped = raw != nullptr;
      if(!raw)
      {
        result.error = "the import " + imp.module + ": " + result.error;
        return false;
      }
      bool ok = false;
      try
      {
        if(module)
        {
          auto shlib = std::make_shared<SharedCurryModule>(path, loadpath, registry);
          module->adopt(shlib, {});
          platform::unload(raw, nullptr);
        }
        result.mapped.push_back(imp.module);
        ok = true;
      }
      catch(std::exception const & e)
      {
        result.error = "the import " + imp.module + ": " + e.what();
      }
      return ok;
    }

    // Loads the object of a finished job and swaps the steps.
    TieredResult apply(Finished & done, bool in_evaluation)
    {
      TieredJob & job = done.job;
      TieredResult result;
      result.registry_id = job.registry.storage->id;
      result.module = job.module;
      result.sofile = job.sofile;
      result.in_evaluation = in_evaluation;
      result.seconds = done.seconds;
      result.output = std::move(done.output);
      if(!done.error.empty())
      {
        result.error = done.error;
        return result;
      }
      auto module = Module::find(job.registry, job.module);
      if(!module)
      {
        result.error = "the module is no longer loaded";
        return result;
      }
      // The tables must be the ones the job was made for: the swap writes
      // the steps of the job into them.  A module made again with other
      // tables submits a job of its own.
      for(auto const & step: job.steps)
        if(module->get_infotable(step.name) != step.info)
        {
          result.error = "the tables of the module were replaced";
          return result;
        }
      if(done.status != 0)
      {
        result.error = "the compile exited with status "
                     + std::to_string(done.status);
        return result;
      }
      if(!job.fingerprints.empty())
      {
        for(auto const & expected: job.fingerprints)
        {
          auto split = expected.find('\n');
          std::ifstream stamp(expected.substr(0, split));
          std::string line, record;
          while(std::getline(stamp, line)) record = line;
          if(split == std::string::npos || record.find(expected.substr(split + 1)) == std::string::npos)
          {
            result.error = "the compiled dependency fingerprints differ from the loaded closure";
            return result;
          }
        }
      }
      // The products go beside the source now, when the source is still
      // there (publish_products), whatever comes of the swap below: the
      // object is the translation of the ICurry the import read, and the
      // next process loads it. Adoption always opens the job's private object.
      std::string const path = publish_products(
          job.sofile, job.publish, job.icurryfile, job.icurry_digest
        );
      result.sofile = path;
      // The object must be the translation of the ICurry the import read:
      // the child compiles the source as it is when the child runs (see
      // TieredJob).
      if(!job.icurryfile.empty()
          && tiered_file_digest(job.icurryfile) != job.icurry_digest)
      {
        result.error = TIERED_EDITED;
        return result;
      }
      // The objects of the imports first; see tiered.hpp.
      for(auto const & imp: job.imports)
        if(!map_import(job.registry, imp, result))
          return result;
      std::vector<std::pair<std::string, InfoTable const *>> steps;
      for(auto const & step: job.steps)
        steps.emplace_back(step.symbol, step.info);
      // The object of the module may be mapped already: the swap of an
      // importer mapped it (map_import).  Then the steps are adopted from
      // it.
      if(auto shlib = module->shlib())
        if(shlib->sofilename() == path || shlib->sofilename() == job.sofile)
        {
          try
          {
            result.swapped = module->adopt(shlib, steps);
            result.ok = true;
          }
          catch(std::exception const & e)
          {
            result.error = e.what();
          }
          return result;
        }
      // The load; see tiered.hpp.  On success the library owns the object
      // and the handle is released.
      std::string loadpath;
      Publication publication(module);
      void * raw = open_object(path, loadpath, &result.error);
      publication.mapped = raw != nullptr;
      if(!raw)
        return result;
      try
      {
        auto shlib = std::make_shared<SharedCurryModule>(path, loadpath, job.registry);
        result.swapped = module->adopt(shlib, steps);
        result.ok = true;
        platform::unload(raw, nullptr);
      }
      catch(std::exception const & e)
      {
        result.error = e.what();
      }
      return result;
    }
  }

  void tiered_after_fork()
  {
    // No parent job, PID, condition variable or armed private path is actionable.
    shared_ptr() = new Shared;
    g_tiered_pending.store(false);
  }

  std::string tiered_file_digest(std::string const & path)
  {
    std::ifstream stream(path, std::ios::binary);
    if(!stream)
      return {};
    auto const & table = crc_table();
    uint32_t crc = 0xFFFFFFFFu;
    size_t size = 0;
    char buffer[65536];
    while(stream.read(buffer, sizeof(buffer)) || stream.gcount() > 0)
    {
      std::streamsize const n = stream.gcount();
      for(std::streamsize i=0; i<n; ++i)
        crc = table[(crc ^ (unsigned char) buffer[i]) & 0xFFu] ^ (crc >> 8);
      size += n;
    }
    char text[48];
    std::snprintf(text, sizeof(text), "%zu:%08x", size, crc ^ 0xFFFFFFFFu);
    return text;
  }

  void tiered_submit(TieredJob job)
  {
    std::lock_guard<std::mutex> lock(shared().mutex);
    std::string error;
    if(!start_worker(&error))
    {
      fail_job(std::move(job), std::move(error));
      return;
    }
    fork_work_begin();
    shared().queue.push_back(std::move(job));
    shared().work_cv.notify_one();
  }

  void cxx_arm(TieredJob job)
  {
    std::lock_guard<std::mutex> lock(shared().mutex);
    JobKey key{job.registry.storage->id, job.module};
    for(auto const & step: job.steps)
      shared().hot_modules[step.info] = key;
    shared().hot_jobs[key] = std::move(job);
  }

  void cxx_hot(InfoTable const * info)
  {
    std::lock_guard<std::mutex> lock(shared().mutex);
    auto module = shared().hot_modules.find(info);
    if(module == shared().hot_modules.end())
      return;
    auto job = shared().hot_jobs.find(module->second);
    if(job == shared().hot_jobs.end())
      return;
    TieredJob taken = std::move(job->second);
    shared().hot_jobs.erase(job);
    std::string error;
    if(!start_worker(&error))
    {
      fail_job(std::move(taken), std::move(error));
      return;
    }
    fork_work_begin();
    shared().queue.push_back(std::move(taken));
    shared().work_cv.notify_one();
  }

  void tiered_apply_pending(bool in_evaluation)
  {
    HeapScope heap;
    if(!g_tiered_pending.load(std::memory_order_relaxed))
      return;
    std::deque<Finished> finished;
    {
      std::lock_guard<std::mutex> lock(shared().mutex);
      finished.swap(shared().finished);
      g_tiered_pending.store(false);
    }
    for(auto & done: finished)
    {
      TieredResult result;
      try
      {
        result = apply(done, in_evaluation);
      }
      catch(...)
      {
        result.registry_id = done.job.registry.storage->id;
        result.module = done.job.module;
        result.error = "an unexpected error";
      }
      std::lock_guard<std::mutex> lock(shared().mutex);
      if(result.ok)
      {
        shared().counts.swapped_functions += result.swapped;
        shared().counts.swapped_modules += 1;
        if(in_evaluation)
          shared().counts.applied_in_evaluation += 1;
      }
      else
        shared().counts.failed_modules += 1;
      shared().results.push_back(std::move(result));
    }
  }

  TieredResult tiered_adopt(TieredJob job, bool in_evaluation)
  {
    HeapScope heap;
    Finished done{std::move(job), 0, 0, 0.0, {}, {}};
    TieredResult result;
    try
    {
      result = apply(done, in_evaluation);
    }
    catch(...)
    {
      result.registry_id = done.job.registry.storage->id;
        result.module = done.job.module;
      result.error = "an unexpected error";
    }
    std::lock_guard<std::mutex> lock(shared().mutex);
    if(result.ok)
    {
      shared().counts.swapped_functions += result.swapped;
      shared().counts.swapped_modules += 1;
      if(in_evaluation)
        shared().counts.applied_in_evaluation += 1;
    }
    else
      shared().counts.failed_modules += 1;
    return result;
  }

  std::vector<TieredResult> tiered_take_results()
  {
    std::lock_guard<std::mutex> lock(shared().mutex);
    std::vector<TieredResult> out;
    out.swap(shared().results);
    return out;
  }

  TieredStatus tiered_status()
  {
    std::lock_guard<std::mutex> lock(shared().mutex);
    TieredStatus status = shared().counts;
    status.queued = shared().queue.size();
    status.running = shared().running ? 1 : 0;
    return status;
  }

  bool tiered_wait(double seconds)
  {
    std::unique_lock<std::mutex> lock(shared().mutex);
    auto idle = []{ return shared().queue.empty() && !shared().running; };
    if(seconds <= 0)
      return idle();
    auto const deadline = std::chrono::steady_clock::now()
        + std::chrono::duration_cast<std::chrono::steady_clock::duration>(
              std::chrono::duration<double>(seconds)
            );
    return shared().idle_cv.wait_until(lock, deadline, idle);
  }

  void tiered_cancel(ModuleRegistry const * registry)
  {
    std::lock_guard<std::mutex> lock(shared().mutex);
    auto owns = [&](TieredJob const & job)
      { return !registry || job.registry.storage == registry->storage; };
    for(auto it = shared().hot_modules.begin(); it != shared().hot_modules.end();)
      if(!registry || it->second.first == registry->storage->id)
        it = shared().hot_modules.erase(it);
      else ++it;
    for(auto it = shared().hot_jobs.begin(); it != shared().hot_jobs.end();)
      if(owns(it->second)) it = shared().hot_jobs.erase(it);
      else ++it;
    auto & queue = shared().queue;
    queue.erase(std::remove_if(queue.begin(), queue.end(), [&](TieredJob const & job)
      {
        if(!owns(job)) return false;
        fork_work_end(platform::process_id());
        if(!job.logfile.empty())
        {
          std::error_code ignored;
          std::filesystem::remove(job.logfile, ignored);
        }
        return true;
      }), queue.end());
    auto & finished = shared().finished;
    finished.erase(std::remove_if(finished.begin(), finished.end(),
        [&](Finished const & done) { return owns(done.job); }), finished.end());
    auto & results = shared().results;
    results.erase(std::remove_if(results.begin(), results.end(),
        [&](TieredResult const & result)
          { return !registry || result.registry_id == registry->storage->id; }), results.end());
    g_tiered_pending.store(!finished.empty());
    if(!registry || (shared().running && shared().running_registry == registry->storage->id))
    {
      ++shared().generation;
      #if defined(_WIN32)
      if(shared().child)
        TerminateJobObject(reinterpret_cast<Child *>(shared().child)->job, 1);
      #else
      if(shared().child)
        kill(-(pid_t) shared().child, SIGKILL);
      #endif
    }
  }
}
