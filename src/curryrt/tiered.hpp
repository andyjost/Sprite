#pragma once
#include "curryrt/export.hpp"
#include <atomic>
#include <string>
#include <vector>
#include "curryrt/fwd.hpp"

// The gxx backend of compiled execution.
//
// gxx_arm registers the private job of an interpreted module; gxx_hot queues
// it when the first function reaches the shared JIT threshold. Eager mode
// queues the job immediately with tiered_submit and waits at module load.
// The internal tiered names also serve foreground AOT adoption.
//
// The worker.  tiered_submit queues a job: the command that makes the object
// of a module, and the functions to swap.  One detached thread
// runs the jobs in the order of submission, one at a time, so that the object
// of a module exists before a module that imports it is compiled.  A finished
// job sets g_tiered_pending and g_icurry_posted. The worker touches no
// structure of the runtime:
// it spawns processes and reads files.
//
// The swap.  tiered_apply_pending runs on the thread that evaluates: the
// scheduler calls it at the JIT safepoint (RuntimeState::procD_loop)
// and the Python side calls it between evaluations.  For each finished job it
// loads the object, whose load binds its slots to the tables the interpreter
// made and writes the compiled step of each function into its table (see
// the binding below), and counts the functions swapped (Module::adopt).  A
// step pointer is one word, and the bytecode of a function outlives the
// swap, so a step in flight finishes on the bytecode and the next step of
// the function runs compiled.
//
// The load.  dlopen names a loaded object by its path.  A file written over
// the path of an object this process maps (the object of an earlier
// incarnation of the module, kept with its tables by Module::clear) would
// not be read: dlopen would hand back the old object.  Such a file is loaded
// through a hard link of its own name beside it, removed once the object is
// mapped; the two files differ by inode, so the dynamic linker loads the new
// one.  Once an object is mapped, the binding of its load may have given
// kept tables steps that point into it, so the object stays mapped whatever
// happens next: no failure after the load unmaps it.
//
// The binding.  The code of a compiled object reads every info table and
// data type it names through a slot of the object, which the load fills
// (the binding in curryrt/dynload.hpp): a symbol of the module takes the
// table the interpreter made, a symbol of an import the table of the
// import.  So the object names the tables that the nodes, the bytecode of
// other modules, and the Python objects already hold, and one table serves
// a symbol for the life of the process, on every platform.  Without the
// binding the swap would leave two tables per symbol, and the runtime
// compares tables by address (the equality, the bindings of free
// variables, curry.inspect.isa).  The binding writes the compiled step of
// the object into every table without compiled code, so the load is the
// swap, and Module::adopt counts the functions and links the object.
//
// The imports.  An object names the objects of its imports by SONAME, and
// the dynamic linker satisfies each name with an object of that name the
// process has mapped.  A job carries the objects of the imports the
// interpreter runs (TieredJob::imports, in dependency order), and the swap
// maps each one whose module has no object yet before it loads the
// importer's: the job of the import may run later, or not at all (a
// module without a function to swap, whose object the child of the
// importer compiled).  The load binds the object of the import to the live
// tables of the import, so the import is swapped by it, under the same
// check of its ICurry; its own job, when it comes, adopts the mapped
// object.  Without this an importer whose import had not swapped stayed
// interpreted with the message of the dynamic linker in its log.
//
// A failure of the compile or of the load leaves the module interpreted;
// the result reports the cause, and the Python side logs it once.
namespace curryrt
{
  struct TieredJob
  {
    // The full name of the module.
    std::string module;
    // The command that compiles the module, the environment of the command
    // ("KEY=VALUE"), the file that takes its output, and the object the
    // compile writes.
    std::vector<std::string> argv;
    std::vector<std::string> envp;
    std::string logfile;
    std::string sofile;
    // The object beside the source that the swap publishes before it opens
    // the object: the child compiled a private copy and wrote nothing under
    // the source (issue #173), and the swap copies the object, its ABI
    // stamp and the generated file there, each under a temporary name and
    // renamed into place, when the source's ICurry file is the one of the
    // import and its directory exists; else it opens the private object.
    // Empty: nothing is published (a compile under foreign flags, #116).
    std::string publish;
    // The ICurry file (.icy) of the module at the import, and its digest
    // then (tiered_file_digest).  The swap refuses the object when the file
    // differs: the child compiled the source as it was when the child ran,
    // and an object of an edited source is not the code the loaded module
    // means (issue #110).  The .icy, not the JSON made from it: a rerun of
    // the front end writes the same .icy for the same text, while the
    // JSON of the child differs from the one of the import in its spacing.
    // Empty: no check.
    std::string icurryfile;
    std::string icurry_digest;
    // The objects of the imports of the module that the interpreter runs,
    // in dependency order (an import before the modules that import it),
    // each once: the full name of the import, the object its compile
    // writes, and its ICurry file and digest at the import, as above.  The
    // swap maps each one whose module has no object before it loads the
    // object of the module (see the imports above).
    struct Import
    {
      std::string module;
      std::string sofile;
      std::string icurryfile;
      std::string icurry_digest;
      std::string publish; // as the job's, for the object of the import
    };
    std::vector<Import> imports;
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
    // The imports whose objects this swap mapped (see TieredJob::imports).
    std::vector<std::string> mapped;
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

  // The error of a result whose object was refused because the ICurry of
  // the module changed after the import (see TieredJob).
  constexpr char const * TIERED_EDITED =
      "the ICurry of the module changed after the import";

  // The digest of a file for the check of the swap: its size and the CRC-32
  // of its bytes, as text.  The empty string when the file cannot be read.
  std::string tiered_file_digest(std::string const & path);

  // Queues a job.  Starts the worker thread on the first call.
  void tiered_submit(TieredJob);

  // Register a module job until one of its functions reaches the threshold.
  void gxx_arm(TieredJob);
  void gxx_hot(InfoTable const *);

  // Applies the finished jobs on the calling thread, which must be the
  // thread that evaluates.  Returns at once when no job finished.  Never
  // throws: a failure goes into the result of the job.
  void tiered_apply_pending(bool in_evaluation);

  // Loads the object of a module that was compiled on the calling thread
  // and swaps its steps at once, as tiered_apply_pending does for a finished
  // job; no command of the job runs.  The compile on first use under
  // interpret:off ends here (see
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
  // finished jobs not yet applied and the results not yet taken.
  void tiered_cancel();

  // Set by the worker when a job finished; cleared by tiered_apply_pending.
  // The scheduler checks the shared g_icurry_posted flag at its JIT safepoint.
  extern CURRYRT_DATA std::atomic<bool> g_tiered_pending;
}
