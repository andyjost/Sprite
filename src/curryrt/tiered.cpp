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
#include <thread>
#include <unordered_map>
#if !defined(_WIN32)
#include <fcntl.h>
#include <signal.h>
#include <spawn.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>
#endif
#include "curryrt/platform.hpp"
#include "curryrt/dynload.hpp"
#include "curryrt/exceptions.hpp"
#include "curryrt/module.hpp"
#include "curryrt/tiered.hpp"
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
      std::mutex                mutex;
      std::condition_variable   work_cv;  // the worker waits here for a job
      std::condition_variable   idle_cv;  // waiters of tiered_wait
      std::deque<TieredJob>     queue;
      std::deque<Finished>      finished;
      std::vector<TieredResult> results;
      TieredStatus              counts;
      bool                      thread_started = false;
      bool                      running = false;
      long long                 child = 0;   // the process id of the running compile
      // Incremented by tiered_cancel.  A job of an older generation is
      // dropped when it finishes.
      uint64_t                  generation = 0;
    };

    Shared & shared()
    {
      static Shared * const instance = new Shared;
      return *instance;
    }

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
    // Windows runs the interpreter in this release: no compile child.
    long long spawn(
        std::vector<std::string>, std::vector<std::string>
      , std::string const &, std::string * error
      )
    {
      *error = "the background compile is not available on Windows; the module runs interpreted";
      return 0;
    }

    int wait_status(long long) { return -1; }
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
      }
      return status;
    }

    bool file_exists(std::string const & filename)
    {
      struct stat st;
      return stat(filename.c_str(), &st) == 0;
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
          shared().running = false;
          if(generation == shared().generation)
          {
            shared().finished.push_back(std::move(done));
            g_tiered_pending.store(true);
          }
        }
        shared().idle_cv.notify_all();
      }
    }

    void start_worker()
    {
      if(!shared().thread_started)
      {
        std::thread(worker).detach();
        shared().thread_started = true;
      }
    }

    // A hard link of ``path`` under a name of its own beside it, or a copy
    // when the file system refuses the link.  Returns the empty string with
    // ``error`` set on failure.  See the load in tiered.hpp.
    std::string unique_link(std::string const & path, std::string * error)
    {
      static std::atomic<unsigned> counter{0};
      std::string const linkpath = path + "." + std::to_string(platform::process_id())
          + "." + std::to_string(++counter) + ".tiered";
      std::error_code ec;
      std::filesystem::remove(linkpath, ec);
      ec.clear();
      std::filesystem::create_hard_link(path, linkpath, ec);
      if(!ec)
        return linkpath;
      ec.clear();
      std::filesystem::copy_file(path, linkpath, ec);
      if(ec)
      {
        *error = "cannot link or copy the object under a name of its own: "
               + ec.message();
        return {};
      }
      return linkpath;
    }

    // Opens the object ``sofile`` into the global scope; see the load in
    // tiered.hpp.  A file at a path this process maps already is opened
    // through a link of its own name, which ``loadpath`` names and the
    // caller removes once the library took its own handle.  Returns the
    // handle, or null with ``error`` set.
    void * open_object(
        std::string const & sofile, std::string & loadpath, std::string * error
      )
    {
      loadpath = sofile;
      std::string linkpath;
      if(platform::loaded(sofile))
      {
        linkpath = unique_link(sofile, error);
        if(linkpath.empty())
          return nullptr;
        loadpath = linkpath;
      }
      // The first dlopen maps the object; the binding of its load, which
      // follows (SharedCurryModule), may give kept tables steps that point
      // into it.  The handle is never closed on a failure after this
      // point, so the object stays mapped.
      std::string msg;
      void * raw = platform::load(loadpath, &msg);
      if(!raw)
      {
        *error = "cannot load the object: " + msg;
        if(!linkpath.empty())
        {
          std::error_code ignored;
          std::filesystem::remove(linkpath, ignored);
        }
      }
      return raw;
    }

    // Publishes the products of a private compile beside the source (see
    // TieredJob::publish): the generated file, the ABI stamp, then the
    // object, each copied under a temporary name in the target directory
    // and renamed into place, when the source's ICurry file is the one of
    // the import and the directory exists.  Returns the path to open: the
    // published object, or the private one when nothing was published, a
    // removed directory included (issue #173).  Runs on the thread of the
    // swap, so the files beside the source change only at a safepoint of
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
      if(icurryfile.empty() || !file_exists(icurryfile)
          || !fs::is_directory(directory, ec)
          || tiered_file_digest(icurryfile) != digest)
        return sofile;
      auto stem = [](std::string const & path)
      {
        return path.size() > 3 && path.compare(path.size() - 3, 3, ".so") == 0
            ? path.substr(0, path.size() - 3) : path;
      };
      static std::atomic<unsigned> counter{0};
      std::pair<std::string, std::string> const pairs[] = {
          {stem(sofile) + ".cpp", stem(publish) + ".cpp"}
        , {sofile + ".abi", publish + ".abi"}
        , {sofile, publish}
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
          fs::rename(tmp, target, ec);
        if(ec)
        {
          std::error_code ignored;
          fs::remove(tmp, ignored);
          return sofile;
        }
      }
      return publish;
    }

    // Maps the object of an import of a job (see the imports in
    // tiered.hpp), unless the import has one: it was loaded from its
    // object, swapped, or mapped by an earlier swap.  Nothing when the
    // object does not exist: the load of the importer then reports what
    // it lacks.  An import without a module of its name in the registry
    // (none is expected) gets its object mapped all the same, and the
    // handle stays open, so that the object stays mapped.  Returns false
    // with the error of ``result`` set.
    bool map_import(TieredJob::Import const & imp, TieredResult & result)
    {
      auto module = Module::find(imp.module);
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
      void * raw = open_object(path, loadpath, &result.error);
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
          auto shlib = std::make_shared<SharedCurryModule>(path, loadpath);
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
      if(loadpath != path)
      {
        std::error_code ignored;
        std::filesystem::remove(loadpath, ignored);
      }
      return ok;
    }

    // Loads the object of a finished job and swaps the steps.
    TieredResult apply(Finished & done, bool in_evaluation)
    {
      TieredJob & job = done.job;
      TieredResult result;
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
      auto module = Module::find(job.module);
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
      // The products go beside the source now, when the source is still
      // there (publish_products), whatever comes of the swap below: the
      // object is the translation of the ICurry the import read, and the
      // next process loads it.  The object opened is the published one,
      // else the private one.
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
        if(!map_import(imp, result))
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
      void * raw = open_object(path, loadpath, &result.error);
      if(!raw)
        return result;
      try
      {
        auto shlib = std::make_shared<SharedCurryModule>(path, loadpath);
        result.swapped = module->adopt(shlib, steps);
        result.ok = true;
        platform::unload(raw, nullptr);
      }
      catch(std::exception const & e)
      {
        result.error = e.what();
      }
      if(loadpath != path)
      {
        std::error_code ignored;
        std::filesystem::remove(loadpath, ignored);
      }
      return result;
    }
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
    start_worker();
    shared().queue.push_back(std::move(job));
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

  void tiered_cancel()
  {
    std::lock_guard<std::mutex> lock(shared().mutex);
    ++shared().generation;
    for(auto const & job: shared().queue)
      if(!job.logfile.empty())
      {
        std::error_code ignored;
        std::filesystem::remove(job.logfile, ignored);
      }
    shared().queue.clear();
    shared().finished.clear();
    shared().results.clear();
    g_tiered_pending.store(false);
    #if !defined(_WIN32)
    if(shared().child)
      kill(-(pid_t) shared().child, SIGKILL);
    #endif
  }
}
