#include <string>
#include <vector>
#include "cyrt/graph/infotable.hpp"
#include "cyrt/tiered.hpp"
#include "pybind11/pybind11.h"
#include "pybind11/stl.h"

namespace py = pybind11;

// The bindings of tiered execution (cyrt/tiered.hpp).  The Python side
// (backends/cxx/tiered.py) builds the jobs and reads the results.
namespace
{
  using namespace cyrt;

  // The job of a module: the shims (file, argv), the steps (name, symbol,
  // info) and the imports (module, sofile, icurryfile, icurry_digest) come
  // as sequences of tuples.
  TieredJob make_job(
      std::string module, py::sequence shims, std::vector<std::string> argv
    , std::vector<std::string> envp, std::string logfile, std::string sofile
    , py::sequence steps, std::string icurryfile, std::string icurry_digest
    , py::sequence imports
    )
  {
    TieredJob job;
    job.module = std::move(module);
    for(py::handle item: shims)
    {
      py::tuple tup = item.cast<py::tuple>();
      if(tup.size() != 2)
        throw py::value_error("a shim is (file, argv)");
      job.shims.push_back(TieredJob::Shim{
          tup[0].cast<std::string>(), tup[1].cast<std::vector<std::string>>()
        });
    }
    job.argv = std::move(argv);
    job.envp = std::move(envp);
    job.logfile = std::move(logfile);
    job.sofile = std::move(sofile);
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
      if(tup.size() != 4)
        throw py::value_error(
            "an import is (module, sofile, icurryfile, icurry_digest)"
          );
      job.imports.push_back(TieredJob::Import{
          tup[0].cast<std::string>(), tup[1].cast<std::string>()
        , tup[2].cast<std::string>(), tup[3].cast<std::string>()
        });
    }
    return job;
  }

  void tiered_submit_(
      std::string module, py::sequence shims, std::vector<std::string> argv
    , std::vector<std::string> envp, std::string logfile, std::string sofile
    , py::sequence steps, std::string icurryfile, std::string icurry_digest
    , py::sequence imports
    )
  {
    tiered_submit(make_job(
        std::move(module), shims, std::move(argv), std::move(envp)
      , std::move(logfile), std::move(sofile), steps, std::move(icurryfile)
      , std::move(icurry_digest), imports
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
      std::string module, py::sequence shims, std::string sofile
    , py::sequence steps
    )
  {
    TieredJob job = make_job(
        std::move(module), shims, {}, {}, {}, std::move(sofile), steps, {}, {}
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

  void tiered_build_shim_(
      std::string const & shimfile, std::vector<std::string> const & argv
    , std::vector<std::string> const & envp
    )
  {
    std::string output;
    bool ok;
    {
      py::gil_scoped_release release;
      ok = tiered_build_shim(shimfile, argv, envp, &output);
    }
    if(!ok)
      throw std::runtime_error(
          "cannot link the shim " + shimfile + ":\n" + output
        );
  }

  void tiered_load_shim_(std::string const & shimfile)
  {
    std::string error;
    if(!tiered_load_shim(shimfile, &error))
      throw std::runtime_error(error);
  }
}

namespace cyrt { namespace python
{
  void register_tiered(pybind11::module_ mod)
  {
    mod.def("tiered_submit", &tiered_submit_
      , py::arg("module"), py::arg("shims"), py::arg("argv"), py::arg("envp")
      , py::arg("logfile"), py::arg("sofile"), py::arg("steps")
      , py::arg("icurryfile") = "", py::arg("icurry_digest") = ""
      , py::arg("imports") = py::tuple()
      , "Queues the background compile of a module.  shims is a sequence of "
        "(file, argv): the shims to link and load before the object.  steps "
        "is a sequence of (name, symbol, info): the functions to swap when "
        "the object is ready.  icurryfile and icurry_digest name the ICurry "
        "file (.icy) of the module at the import and its tiered_file_digest; "
        "the swap refuses the object when the file differs (the error "
        "TIERED_EDITED).  imports is a sequence of (module, sofile, "
        "icurryfile, icurry_digest), the objects of the imports the "
        "interpreter runs, in dependency order: the swap maps each one whose "
        "module has no object before the object of the module, under the "
        "same check of its ICurry.");
    mod.def("tiered_file_digest", &tiered_file_digest, py::arg("path")
      , "The digest of a file for the check of the swap: its size and the "
        "CRC-32 of its bytes, as text; the empty string when the file cannot "
        "be read.");
    mod.attr("TIERED_EDITED") = TIERED_EDITED;
    mod.def("tiered_adopt", &tiered_adopt_
      , py::arg("module"), py::arg("shims"), py::arg("sofile"), py::arg("steps")
      , "Loads the object of a module compiled in this process and swaps the "
        "steps at once (the compile on first use under interpret:off).  shims "
        "and steps are as for tiered_submit.  Returns the result as a dict "
        "with the keys of tiered_results.");
    mod.def("tiered_poll", []{ tiered_apply_pending(false); }
      , "Applies the compiled objects that finished in the background.  Call "
        "it from the thread that evaluates.");
    mod.def("tiered_results", &tiered_results_
      , "The results applied since the last call: dicts with the keys "
        "module, sofile, ok, in_evaluation, swapped, mapped (the imports "
        "whose objects the swap mapped), seconds, error, output.");
    mod.def("tiered_status", &tiered_status_
      , "The counts of tiered execution: queued, running, swapped_functions, "
        "swapped_modules, failed_modules, applied_in_evaluation.");
    mod.def("tiered_wait", &tiered_wait_, py::arg("seconds")
      , "Waits until no job is queued or running, or until the seconds "
        "passed.  Returns True when the worker is idle.");
    mod.def("tiered_cancel", &tiered_cancel
      , "Drops the queued jobs and kills the running compile.");
    mod.def("tiered_build_shim", &tiered_build_shim_
      , py::arg("shimfile"), py::arg("argv"), py::arg("envp")
      , "Links a shim with the given command, unless the file exists.  "
        "Raises RuntimeError when the command fails.");
    mod.def("tiered_load_shim", &tiered_load_shim_, py::arg("shimfile")
      , "Loads a shim into the global scope; a shim loaded already is kept.  "
        "Raises RuntimeError when the load fails.");
  }
}}
