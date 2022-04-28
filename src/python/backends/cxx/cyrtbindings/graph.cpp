#include "pybind11/pybind11.h"
#include "pybind11/stl.h"
#include "cyrt/graph/infotable.hpp"
#include "cyrt/graph/node.hpp"
#include "cyrt/state/rts.hpp"

namespace py = pybind11;
static auto constexpr reference = py::return_value_policy::reference;

namespace
{
  using namespace cyrt;

  Node * Node_create(
      InfoTable const * info, std::vector<Arg> const & args
    , Node * target, bool partial
    )
  {
    Node * node = partial
        ? Node::create_partial(info, args.data(), args.size())
        : Node::create(info, args.data());
    if(target)
    {
      target->forward_to(node);
      return target;
    }
    else
      return node;
  }
}

namespace cyrt { namespace python
{
  void register_graph(pybind11::module_ mod)
  {
    py::class_<InfoTable>(mod, "InfoTable")
      .def_readonly("arity"   , &InfoTable::arity)
      .def_readonly("flags"   , &InfoTable::flags)
      .def_readonly("format"  , &InfoTable::format)
      .def_readonly("name"    , &InfoTable::name)
      .def_readonly("tag"     , &InfoTable::tag)
      .def_readwrite("typedef", &InfoTable::type)
      ;

    py::class_<Arg>(mod, "Arg")
      .def(py::init<Node *>())
      .def(py::init<unboxed_int_type>())
      .def(py::init<unboxed_float_type>())
      .def(py::init<unboxed_char_type>())
      .def("__repr__", &Arg::repr)
      ;

    py::class_<Node>(mod, "Node")
      // TODO attach a refcount.  Wild nodes attached to Python objects need to
      // be added to the GC roots.
      .def_static("create", &Node_create, reference)
      .def("__str__", (std::string(Node::*)()) &Node::str)
      .def("__repr__", (std::string(Node::*)()) &Node::repr)
      ;

    py::class_<DataType>(mod, "DataType")
      .def_property_readonly(
          "constructors"
        , [](DataType const & self)
              { return std::vector(self.ctors, self.ctors+self.size); }
        )
      .def_readonly("flags", &DataType::flags)
      .def_readonly("kind", &DataType::kind)
      .def_readonly("name", &DataType::name)
      .def_readonly("size", &DataType::size)
      ;
  }
}}
