#include "heap.hpp"
#include "pybind11/pybind11.h"
#include "curryrt/fingerprint.hpp"
#include <functional>
#include <map>

using namespace curryrt;
namespace py = pybind11;

namespace
{
  void Fingerprint__setitem__(Fingerprint & self, size_t id, ChoiceState lr)
  {
    switch(lr)
    {
      case ChoiceState::LEFT:  self.set_left(id); break;
      case ChoiceState::RIGHT: self.set_right(id); break;
      default: throw std::invalid_argument("expected LEFT or RIGHT");
    }
  }

  py::object Fingerprint__tree__(Fingerprint const & self)
  {
    std::map<fingerprints::Branch const *, py::object> branches;
    std::function<py::object(fingerprints::Node const *, size_t)> buildtree;
    buildtree = [&](fingerprints::Node const * node, size_t depth) -> py::object
    {
      if(depth == self.depth())
        return py::cast(node->block);
      auto const * branch = node->branch;
      if(branches.count(branch) == 0)
      {
        py::list args;
        for(size_t i=0; i<FP_BRANCH_SIZE; ++i)
          args.append(buildtree(&branch->next[i], depth+1));
        branches[branch] = py::tuple(args);
      }
      return branches[branch];
    };
    return buildtree(&self.root(), 0);
  }
}

namespace curryrt { namespace python
{
  void register_fingerprint(py::module_ mod)
  {
    py::enum_<ChoiceState>(mod, "ChoiceState")
        .value("UNDETERMINED", ChoiceState::UNDETERMINED)
        .value("LEFT", ChoiceState::LEFT)
        .value("RIGHT", ChoiceState::RIGHT)
        .export_values();

    py::class_<Fingerprint>(mod, "Fingerprint")
      .def(py::init<>(), curryrt::python::heap_access{})
      .def(py::init<Fingerprint const &>(), curryrt::python::heap_access{})
      .def("__copy__", +[](Fingerprint const & self)->Fingerprint{return self;}, curryrt::python::heap_access{})
      .def("get", +[](Fingerprint & self, size_t id, ChoiceState default_)
          -> ChoiceState
          {
            auto lr = self.test(id);
            return lr == ChoiceState::UNDETERMINED ? default_ : lr;
          }
        , py::arg("id")
        , py::arg("default")=ChoiceState::UNDETERMINED
        , curryrt::python::heap_access{})
      .def("set_left", &Fingerprint::set_left, curryrt::python::heap_access{})
      .def("set_right", &Fingerprint::set_right, curryrt::python::heap_access{})
      .def("__contains__", +[](Fingerprint const & self, size_t id) -> bool
          { return self.test(id) != ChoiceState::UNDETERMINED; }
        , curryrt::python::heap_access{})
      .def("__setitem__", &Fingerprint__setitem__, curryrt::python::heap_access{})
      .def("__getitem__", &Fingerprint::test, curryrt::python::heap_access{})
      .def_property_readonly("capacity", &Fingerprint::capacity, curryrt::python::heap_access{})
      .def_property_readonly("depth", &Fingerprint::depth, curryrt::python::heap_access{})
      .def_static("BASIC_SIZE", +[]{return FP_BLOCK_SIZE;}, curryrt::python::heap_access{})
      .def_static("BRANCHING_FACTOR", +[]{return FP_BRANCH_SIZE;}, curryrt::python::heap_access{})
      .def("tree", Fingerprint__tree__
        , "Builds a Python representation of the internal tree.  For testing."
        , curryrt::python::heap_access{})
      ;

    // For testing.
    py::class_<fingerprints::Block>(mod, "Block")
      .def_readonly("used", &fingerprints::Block::used, curryrt::python::heap_access{})
      .def_readonly("lr", &fingerprints::Block::lr, curryrt::python::heap_access{})
      .def("values", +[](fingerprints::Block const & self) -> py::object
        {
          py::list values;
          for(size_t i=0; i<FP_BLOCK_SIZE; ++i)
            values.append(
                (self.used & (1<<i)) ? (self.lr & (1<<i)) ? 1 : -1 : 0
              );
          return values;
        }, curryrt::python::heap_access{})
      .def("__eq__", +[](
          fingerprints::Block const & lhs, fingerprints::Block const & rhs
        ) -> bool
        { return lhs.used == rhs.used && lhs.lr == rhs.lr; }, curryrt::python::heap_access{})
      .def("__repr__", +[](py::object const & self) -> py::object
        {
          return py::str(self.attr("values")());
        }, curryrt::python::heap_access{})
      ;
  }
}}

