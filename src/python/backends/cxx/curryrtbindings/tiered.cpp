#include "heap.hpp"
#include <string>
#include <vector>
#include "curryrt/graph/infotable.hpp"
#include "curryrt/tiered.hpp"
#include "pybind11/pybind11.h"
#include "pybind11/stl.h"

namespace py = pybind11;

// The bindings of tiered execution (curryrt/tiered.hpp).  The Python side
// (backends/cxx/tiered.py) builds the jobs and reads the results.
namespace
{
  using namespace curryrt;

  // The job of a module: the steps (name, symbol, info) and the imports
  // (module, sofile, icurryfile, icurry_digest, publish) come as sequences
  // of tuples; ``publish`` names the object beside the source the swap
  // publishes, or is empty (TieredJob::publish).
  TieredJob make_job(
      std::string module, std::vector<std::string> argv
    , std::vector<std::string> envp, std::string logfile, std::string sofile
    , std::string publish, py::sequence steps, std::string icurryfile
    , std::string icurry_digest, py::sequence imports
    )
  {
    TieredJob job;
    job.module = std::move(module);
    job.argv = std::move(argv);
    job.envp = std::move(envp);
    job.logfile = std::move(logfile);
    job.sofile = std::move(sofile);
    job.publish = std::move(publish);
    job.icurryfile = std::move(icurryfile);
    job.icurry_digest = std::move(icurry_digest);
    for(py::handle item: steps)
    {
      py::tuple tup = item.cast<py::tuple>();
      if(tup.size() != 3)
        throw py::value_error("a step is (name, symbol, info)");
      InfoTable const * info = tup[2].cast<InfoTable const *>();
      if(!info)
        throw py::value_error("a step needs an info table");
      job.steps.push_back(TieredJob::Step{
          tup[0].cast<std::string>(), tup[1].cast<std::string>(), info
        });
    }
    for(py::handle item: imports)
    {
      py::tuple tup = item.cast<py::tuple>();
      if(tup.size() != 5)
        throw py::value_error(
            "an import is (module, sofile, icurryfile, icurry_digest, publish)"
          );
      job.imports.push_back(TieredJob::Import{
          tup[0].cast<std::string>(), tup[1].cast<std::string>()
        , tup[2].cast<std::string>(), tup[3].cast<std::string>()
        , tup[4].cast<std::string>()
        });
    }
    return job;
  }

  void tiered_submit_(
      std::string module, std::vector<std::string> argv
    , std::vector<std::string> envp, std::string logfile, std::string sofile
    , std::string publish, py::sequence steps, std::string icurryfile
    , std::string icurry_digest, py::sequence imports
    )
  {
    tiered_submit(make_job(
        std::move(module), std::move(argv), std::move(envp)
      , std::move(logfile), std::move(sofile), std::move(publish), steps
      , std::move(icurryfile), std::move(icurry_digest), imports
      ));
  }

  py::dict result_dict(TieredResult const & r)
  {
    py::dict d;
    d["module"] = r.module;
    d["sofile"] = r.sofile;
    d["ok"] = r.ok;
    d["in_evaluation"] = r.in_evaluation;
    d["swapped"] = r.swapped;
    d["mapped"] = r.mapped;
    d["seconds"] = r.seconds;
    d["error"] = r.error;
    d["output"] = r.output;
    return d;
  }

  py::dict tiered_adopt_(
      std::string module, std::string sofile, py::sequence steps
    )
  {
    TieredJob job = make_job(
        std::move(module), {}, {}, {}, std::move(sofile), {}, steps, {}, {}
      , py::tuple()
      );
    return result_dict(tiered_adopt(std::move(job), true));
  }

  py::list tiered_results_()
  {
    py::list out;
    for(auto const & r: tiered_take_results())
      out.append(result_dict(r));
    return out;
  }

  py::dict tiered_status_()
  {
    TieredStatus s = tiered_status();
    py::dict d;
    d["queued"] = s.queued;
    d["running"] = s.running;
    d["swapped_functions"] = s.swapped_functions;
    d["swapped_modules"] = s.swapped_modules;
    d["failed_modules"] = s.failed_modules;
    d["applied_in_evaluation"] = s.applied_in_evaluation;
    return d;
  }

  bool tiered_wait_(double seconds)
  {
    py::gil_scoped_release release;
    return tiered_wait(seconds);
  }

}

namespace curryrt { namespace python
{
  void register_tiered(pybind11::module_ mod)
  {
    mod.def("tiered_submit", &tiered_submit_
      , py::arg("module"), py::arg("argv"), py::arg("envp")
      , py::arg("logfile"), py::arg("sofile"), py::arg("publish") = ""
      , py::arg("steps")
      , py::arg("icurryfile") = "", py::arg("icurry_digest") = ""
      , py::arg("imports") = py::tuple()
      , "Queues the background compile of a module.  sofile is the object "
        "the compile writes, in a private directory; publish names the "
        "object beside the source the swap publishes before it opens the "
        "object, or is empty.  steps "
        "is a sequence of (name, symbol, info): the functions to swap when "
        "the object is ready.  icurryfile and icurry_digest name the ICurry "
        "file (.icy) of the module at the import and its tiered_file_digest; "
        "the swap refuses the object when the file differs (the error "
        "TIERED_EDITED).  imports is a sequence of (module, sofile, "
        "icurryfile, icurry_digest, publish), the objects of the imports the "
        "interpreter runs, in dependency order: the swap maps each one whose "
        "module has no object before the object of the module, under the "
        "same check of its ICurry.", curryrt::python::heap_access{});
    mod.def("tiered_file_digest", &tiered_file_digest, py::arg("path")
      , "The digest of a file for the check of the swap: its size and the "
        "CRC-32 of its bytes, as text; the empty string when the file cannot "
        "be read.", curryrt::python::heap_access{});
    mod.attr("TIERED_EDITED") = TIERED_EDITED;
    mod.def("tiered_adopt", &tiered_adopt_
      , py::arg("module"), py::arg("sofile"), py::arg("steps")
      , "Loads the object of a module compiled in this process and swaps the "
        "steps at once (the compile on first use under interpret:off).  steps "
        "is as for tiered_submit.  Returns the result as a dict "
        "with the keys of tiered_results.", curryrt::python::heap_access{});
    mod.def("tiered_poll", []{ tiered_apply_pending(false); }
      , "Applies the compiled objects that finished in the background.  Call "
        "it from the thread that evaluates.", curryrt::python::heap_access{});
    mod.def("tiered_results", &tiered_results_
      , "The results applied since the last call: dicts with the keys "
        "module, sofile, ok, in_evaluation, swapped, mapped (the imports "
        "whose objects the swap mapped), seconds, error, output.", curryrt::python::heap_access{});
    mod.def("tiered_status", &tiered_status_
      , "The counts of tiered execution: queued, running, swapped_functions, "
        "swapped_modules, failed_modules, applied_in_evaluation.", curryrt::python::heap_access{});
    mod.def("tiered_wait", &tiered_wait_, py::arg("seconds")
      , "Waits until no job is queued or running, or until the seconds "
        "passed.  Returns True when the worker is idle.", curryrt::python::heap_access{});
    mod.def("tiered_cancel", &tiered_cancel
      , "Drops the queued jobs and kills the running compile.", curryrt::python::heap_access{});
  }
}}
