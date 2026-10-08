#pragma once
#include <atomic>
#include <string>
#include <vector>
#include "cyrt/fwd.hpp"

// Tiered execution.
//
// Under the interpreter flag ``interpret`` set to 'tiered', a module without a
// compiled object is interpreted at once (cyrt/icurry.hpp), a child process
// compiles it in the background, and the compiled steps replace the
// interpreted ones in the running process.  This file holds the runtime side:
// the worker thread that runs the child processes, and the swap.
//
// The worker.  tiered_submit queues a job: the commands that make the shim
// and the object of a module, and the functions to swap.  One detached thread
// runs the jobs in the order of submission, one at a time, so that the object
// of a module exists before a module that imports it is compiled.  A finished
// job sets g_tiered_pending.  The thread touches no structure of the runtime:
// it spawns processes and reads files.
//
// The swap.  tiered_apply_pending runs on the thread that evaluates: the
// scheduler calls it at its periodic safepoint (RuntimeState::check_interrupts)
// and the Python side calls it between evaluations.  For each finished job it
// loads the shims, then the object, whose initializers write the compiled
// step into the tables the interpreter made (see the shim below and
// Module::adopt).  A step pointer is one word, and the bytecode of a function
// outlives the swap, so a step in flight finishes on the bytecode and the
// next step of the function runs compiled.
//
// The load.  dlopen names a loaded object by its path.  A file written over
// the path of an object this process maps (the object of an earlier
// incarnation of the module, kept with its tables by Module::clear) would
// not be read: dlopen would hand back the old object.  Such a file is loaded
// through a hard link of its own name beside it, removed once the object is
// mapped; the two files differ by inode, so the dynamic linker loads the new
// one.  Once an object is mapped its initializers have written the live
// tables, so the object stays mapped whatever happens next: no failure after
// the load unmaps it.
//
// The shim.  The code of a compiled object names its own info tables and data
// types by ELF symbol, and so do its bill of materials and its constructor
// arrays.  The dynamic linker binds such a reference to the first definition
// in the global scope.  The shim is a library of absolute symbols, made with
// the linker, that gives each symbol the address of the table the interpreter
// made, and it is loaded before the object.  So the object binds every table
// reference, its own included, to the tables that the nodes, the bytecode of
// other modules, and the Python objects already hold, and one table serves a
// symbol for the life of the process.  Without the shim the swap would leave
// two tables per symbol, and the runtime compares tables by address (the
// equality, the bindings of free variables, curry.inspect.isa).
//
// The static tables and types of the object are constructed by its dynamic
// initializers, at the addresses their symbols resolve to: the tables the
// interpreter made.  So the load itself is the swap, the object's own copies
// of the tables stay blank, and the shim must be loaded before the object.
//
// A failure of the compile, of the shim, or of the load leaves the module
// interpreted; the result reports the cause, and the Python side logs it once.
namespace cyrt
{
  struct TieredJob
  {
    // The full name of the module.
    std::string module;
    // The shims the object binds to: its own, and those of the modules the
    // interpreter runs that were not loaded when the job was made.  Each
    // names its file and the command that links it.  The worker links the
    // missing ones; the swap loads them before the object, whether or not
    // the compile succeeded, so that every object loaded later binds to the
    // live tables.
    struct Shim
    {
      std::string file;
      std::vector<std::string> argv;
    };
    std::vector<Shim> shims;
    // The command that compiles the module, the environment of the commands
    // ("KEY=VALUE"), the file that takes their output, and the object the
    // compile writes.
    std::vector<std::string> argv;
    std::vector<std::string> envp;
    std::string logfile;
    std::string sofile;
    // The functions to swap: the name of the function in its module, the
    // symbol of its step function in the object, and the table the
    // interpreter made.
    struct Step
    {
      std::string name;
      std::string symbol;
      InfoTable const * info;
    };
    std::vector<Step> steps;
  };

  struct TieredResult
  {
    std::string module;
    std::string sofile;
    // The object was loaded and the steps were swapped.
    bool ok = false;
    // The result was applied at a safepoint of the scheduler, during an
    // evaluation.
    bool in_evaluation = false;
    // The functions swapped.
    size_t swapped = 0;
    // The wall seconds of the commands.
    double seconds = 0;
    // Why the module stays interpreted, and the output of the commands.
    std::string error;
    std::string output;
  };

  struct TieredStatus
  {
    size_t queued = 0;
    size_t running = 0;
    size_t swapped_functions = 0;
    size_t swapped_modules = 0;
    size_t failed_modules = 0;
    size_t applied_in_evaluation = 0;
  };

  // Queues a job.  Starts the worker thread on the first call.
  void tiered_submit(TieredJob);

  // Applies the finished jobs on the calling thread, which must be the
  // thread that evaluates.  Returns at once when no job finished.  Never
  // throws: a failure goes into the result of the job.
  void tiered_apply_pending(bool in_evaluation);

  // Loads the object of a module that was compiled on the calling thread
  // and swaps its steps at once, as tiered_apply_pending does for a finished
  // job; no command of the job runs, and the shims of the job are loaded
  // first.  The compile on first use under interpret:off ends here (see
  // trap_step in module.hpp and backends/cxx/materialize.py).  The result
  // is returned, not queued, and counts in tiered_status as the result of a
  // job.  Never throws.
  TieredResult tiered_adopt(TieredJob job, bool in_evaluation);

  // The results applied since the last call, in order.
  std::vector<TieredResult> tiered_take_results();

  TieredStatus tiered_status();

  // Waits until no job is queued or running, or until ``seconds`` passed.
  // Returns true when the worker is idle.  The finished jobs still wait for
  // tiered_apply_pending.
  bool tiered_wait(double seconds);

  // Drops the queued jobs, kills the running child process, and drops the
  // finished jobs not yet applied and the results not yet taken.  The shims
  // stay loaded.
  void tiered_cancel();

  // Runs the command that links a shim, unless the file exists.  The worker
  // and the Python side call this, one at a time.  Returns false when the
  // command failed; ``output`` takes its output.
  bool tiered_build_shim(
      std::string const & shimfile, std::vector<std::string> const & argv
    , std::vector<std::string> const & envp, std::string * output
    );

  // Loads a shim into the global scope.  A shim loaded already is not
  // loaded again.  Returns false and sets ``error`` when dlopen fails.
  bool tiered_load_shim(std::string const & shimfile, std::string * error);

  // Set by the worker when a job finished; cleared by tiered_apply_pending.
  // The scheduler checks it at its periodic safepoint.
  extern std::atomic<bool> g_tiered_pending;
}
