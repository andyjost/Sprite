#include "pybind11/pybind11.h"
#include "pybind11/stl.h"
#include "cyrt/module.hpp"
#include "cyrt/state/rts.hpp"
#include <string>

namespace py = pybind11;
static auto constexpr reference = py::return_value_policy::reference;

namespace
{
  using namespace cyrt;

  // The Python hook of the trap step (set_trap_hook).  A pointer, never
  // destroyed: a py::object destroyed after the interpreter ended is an
  // error.
  py::object * g_trap_hook = nullptr;

  // Calls the Python hook with the table and returns the reason it gave,
  // or the empty string.  An exception of the hook is a reason too: the
  // trap runs inside a rewrite step, which reports an error by its status.
  // An interrupt and an exit pass, so that a long compile can be stopped.
  std::string call_trap_hook(InfoTable const * info)
  {
    py::gil_scoped_acquire gil;
    try
    {
      py::object result = (*g_trap_hook)(py::cast(info, reference));
      if(result.is_none())
        return {};
      return py::str(result).cast<std::string>();
    }
    catch(py::error_already_set & exc)
    {
      if(exc.matches(PyExc_KeyboardInterrupt) || exc.matches(PyExc_SystemExit))
        throw;
      std::string text;
      try
      {
        text = py::str(exc.type().attr("__name__")).cast<std::string>()
             + ": " + py::str(exc.value()).cast<std::string>();
      }
      catch(...)
      {
        text = "an exception of the hook";
      }
      exc.restore();
      PyErr_Clear();
      return text;
    }
    catch(std::exception const & exc)
    {
      return exc.what();
    }
  }
}

namespace cyrt { namespace python
{
  void register_module(pybind11::module_ mod)
  {
    mod.def("set_trap_hook"
      , [](py::object hook)
        {
          if(!g_trap_hook)
            g_trap_hook = new py::object();
          *g_trap_hook = hook;
          set_trap_hook(hook.is_none() ? nullptr : &call_trap_hook);
        }
      , py::arg("hook")
      , "Installs the hook of the trap step (cyrt/module.hpp): a callable "
        "of one info table that gives the table its code and returns None, "
        "or returns the reason it did not.  None removes the hook.");
    mod.def("install_trap", &install_trap, py::arg("info")
      , "Gives a function table made at run time the trap step: a step that "
        "calls the hook and raises when the table still has no code.");
    mod.def("is_trapped"
      , [](InfoTable const * info) { return is_trapped(info); }
      , py::arg("info")
      , "Whether the step of an info table is the trap step.");
    mod.def("trap_owner", &owner_of, py::arg("info")
      , "The name of the loaded module that owns a table, or ''.");
    py::class_<Module, std::shared_ptr<Module>>(mod, "Module")
      .def("create_infotable", &Module::create_infotable, reference)
      .def("create_type", &Module::create_type, reference)
      .def("get_infotable", &Module::get_infotable, reference)
      .def("get_type", &Module::get_type, reference)
      .def("get_builtin_symbol", &Module::get_builtin_symbol, reference)
      .def("get_builtin_type", &Module::get_builtin_type, reference)
      .def("link", &Module::link)
      .def("keep_tables", &Module::keep_tables
        , "Keeps the tables made at run time for the life of the process.")
      .def_property_readonly("shlib", &Module::shlib
        , "The compiled object linked to the module, or None.")
      .def_readonly("name", &Module::name)
      .def_static("find_or_create", &Module::find_or_create)
      .def_static("getall", &Module::getall)
      ;
  }
}}
