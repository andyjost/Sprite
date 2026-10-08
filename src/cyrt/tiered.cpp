#include <cerrno>
#include <chrono>
#include <condition_variable>
#include <cstring>
#include <deque>
#include <dlfcn.h>
#include <fcntl.h>
#include <filesystem>
#include <fstream>
#include <mutex>
#include <signal.h>
#include <spawn.h>
#include <sstream>
#include <sys/stat.h>
#include <sys/wait.h>
#include <thread>
#include <unistd.h>
#include <unordered_map>
#include "cyrt/dynload.hpp"
#include "cyrt/exceptions.hpp"
#include "cyrt/module.hpp"
#include "cyrt/tiered.hpp"

extern char ** environ;

// The worker thread and the swap of tiered execution.  See tiered.hpp.
namespace cyrt
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
      pid_t                     child = 0;
      // Incremented by tiered_cancel.  A job of an older generation is
      // dropped when it finishes.
      uint64_t                  generation = 0;

      std::mutex                              shim_mutex;
      std::unordered_map<std::string, void *> shims;
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
      unlink(logfile.c_str());
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

    // Starts a command with its output appended to ``logfile`` and no input.
    // Returns the process id, or zero with ``error`` set.
    pid_t spawn(
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
    int wait_status(pid_t pid)
    {
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
      pid_t pid = 0;
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
        bool ok = true;
        for(auto const & shim: done.job.shims)
        {
          std::string output;
          ok = tiered_build_shim(shim.file, shim.argv, done.job.envp, &output);
          if(!ok)
          {
            done.error = "the shim " + shim.file + " could not be linked";
            done.output = output;
            break;
          }
        }
        if(ok)
        {
          done.status = run(
              done.job.argv, done.job.envp, done.job.logfile, &done.error
            , &generation
            );
          done.output = take_output(done.job.logfile);
        }
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
      std::string const linkpath = path + "." + std::to_string(getpid())
          + "." + std::to_string(++counter) + ".tiered";
      unlink(linkpath.c_str());
      if(link(path.c_str(), linkpath.c_str()) == 0)
        return linkpath;
      std::error_code ec;
      std::filesystem::copy_file(path, linkpath, ec);
      if(ec)
      {
        *error = "cannot link or copy the object under a name of its own: "
               + ec.message();
        return {};
      }
      return linkpath;
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
      // The tables must be the ones the job was made for: the shim of the
      // module names them by address.
      for(auto const & step: job.steps)
        if(module->get_infotable(step.name) != step.info)
        {
          result.error = "the tables of the module were replaced";
          return result;
        }
      // The shims are loaded whatever the compile did: an object loaded
      // later must bind to the live tables of an interpreted module.
      for(auto const & shim: job.shims)
        if(!tiered_load_shim(shim.file, &result.error))
          return result;
      if(done.status != 0)
      {
        result.error = "the compile exited with status "
                     + std::to_string(done.status);
        return result;
      }
      // The load; see tiered.hpp.  A file at a path this process maps
      // already is loaded through a link of its own name.
      std::string loadpath = job.sofile;
      std::string linkpath;
      if(void * mapped = dlopen(job.sofile.c_str(), RTLD_LAZY | RTLD_NOLOAD))
      {
        dlclose(mapped);
        linkpath = unique_link(job.sofile, &result.error);
        if(linkpath.empty())
          return result;
        loadpath = linkpath;
      }
      // The first dlopen runs the initializers of the object, which write
      // the live tables.  Its handle is never closed on a failure below, so
      // the object stays mapped; on success the library owns the object and
      // the handle is released.
      void * raw = dlopen(loadpath.c_str(), RTLD_LAZY | RTLD_GLOBAL);
      if(!raw)
      {
        char const * msg = dlerror();
        result.error = std::string("cannot load the object: ")
                     + (msg ? msg : "");
        if(!linkpath.empty())
          unlink(linkpath.c_str());
        return result;
      }
      try
      {
        auto shlib = std::make_shared<SharedCurryModule>(job.sofile, loadpath);
        std::vector<std::pair<std::string, InfoTable const *>> steps;
        for(auto const & step: job.steps)
          steps.emplace_back(step.symbol, step.info);
        result.swapped = module->adopt(shlib, steps);
        result.ok = true;
        dlclose(raw);
      }
      catch(std::exception const & e)
      {
        result.error = e.what();
      }
      if(!linkpath.empty())
        unlink(linkpath.c_str());
      return result;
    }
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
        unlink(job.logfile.c_str());
    shared().queue.clear();
    shared().finished.clear();
    shared().results.clear();
    g_tiered_pending.store(false);
    if(shared().child)
      kill(-shared().child, SIGKILL);
  }

  bool tiered_build_shim(
      std::string const & shimfile, std::vector<std::string> const & argv
    , std::vector<std::string> const & envp, std::string * output
    )
  {
    std::lock_guard<std::mutex> lock(shared().shim_mutex);
    if(file_exists(shimfile))
      return true;
    // The command writes the file under a temporary name (see tiered.py),
    // which is moved into place when the linker succeeded, so that a loader
    // never sees a partial file.
    std::string const tmp = shimfile + ".tmp";
    std::string const logfile = shimfile + ".log";
    std::string error;
    int status = run(argv, envp, logfile, &error, nullptr);
    *output = take_output(logfile);
    if(status != 0)
    {
      if(!error.empty())
        *output = error + "\n" + *output;
      unlink(tmp.c_str());
      return false;
    }
    if(rename(tmp.c_str(), shimfile.c_str()) != 0)
    {
      *output = errno_text("cannot move the shim into place");
      return false;
    }
    return true;
  }

  bool tiered_load_shim(std::string const & shimfile, std::string * error)
  {
    std::lock_guard<std::mutex> lock(shared().shim_mutex);
    if(shared().shims.count(shimfile))
      return true;
    void * handle = dlopen(shimfile.c_str(), RTLD_NOW | RTLD_GLOBAL);
    if(!handle)
    {
      char const * msg = dlerror();
      *error = std::string("cannot load the shim: ") + (msg ? msg : "");
      return false;
    }
    shared().shims[shimfile] = handle;
    return true;
  }
}
