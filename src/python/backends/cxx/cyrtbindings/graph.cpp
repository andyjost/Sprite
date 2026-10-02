#include <cassert>
#include <cstdint>
#include <cstdio>
#include <string>
#include "cyrt/builtins.hpp"
#include "cyrt/graph/infotable.hpp"
#include "cyrt/graph/node.hpp"
#include "cyrt/state/rts.hpp"
#include "pybind11/pybind11.h"
#include "pybind11/stl.h"

namespace py = pybind11;
static auto constexpr reference = py::return_value_policy::reference;
static auto constexpr reference_internal = py::return_value_policy::reference_internal;

namespace
{
  using namespace cyrt;

  // Forward ``source`` to ``target`` on behalf of Python code.  Node::forward_to
  // asserts its preconditions; here a bad request becomes a Python exception.
  void forward_node(Node * source, Node * target)
  {
    if(!source || !target)
      throw py::value_error("cannot forward a null node");
    if(source->info->tag == T_FWD)
    {
      // A forward node is retargeted in place.  Node::forward_to rejects it
      // because a FwdSz node must keep its original size.
      NodeU{source}.fwd->target = target;
      return;
    }
    if(is_pinned(*source->info))
      throw py::value_error(
          std::string("cannot forward the shared node ") + source->info->name
        );
    if(source->info->alloc_size < sizeof(FwdNode))
      throw py::value_error(
          std::string("node ") + source->info->name + " is too small to forward"
        );
    source->forward_to(target);
  }

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
      forward_node(target, node);
      return target;
    }
    else
      return node;
  }

  void InfoTable_step(InfoTable * info, RuntimeState * rts, Node * root)
  {
    rts->set_goal(root);
    info->step(rts, rts->C());
    rts->drop();
  }

  template<typename T>
  struct ByValueHolder
  {
    ByValueHolder(T arg) : data(arg) {}
    T data;
    T * get() { return &data; }
  };

  Node * generator_next(void * data)
  {
    assert(data);
    auto * pyobj = (PyObject *) data;
    py::object value = py::reinterpret_steal<py::object>(PyIter_Next(pyobj));
    if(PyErr_Occurred()) { throw py::error_already_set(); }
    // Note: the Node * is not owned directly by the PyObject but rather by the
    // garbage collector.  So it is safe to extract the Node * and return it
    // this way.
    return value.ptr() ? py::cast<Node *>(value) : (Node *) nullptr;
  }
}

PYBIND11_DECLARE_HOLDER_TYPE(T, ByValueHolder<T>, true)

namespace pybind11 { namespace detail
{
  template <> struct type_caster<cyrt::Expr>
  {
    // Note: _ is named const_name in later versions of pybind11.
    PYBIND11_TYPE_CASTER(cyrt::Expr, _("Expr"));
    bool load(handle src, bool) { return false; }
    static handle cast(cyrt::Expr src, return_value_policy /* policy */, handle /* parent */)
    {
      switch(src.kind)
      {
        case 'p': return py::cast(src.arg.node).inc_ref(); // TODO: review this
        case 'i': return py::cast(src.arg.ub_int).inc_ref();
        case 'f': return py::cast(src.arg.ub_float).inc_ref();
        case 'c': { char buf[2] = {src.arg.ub_char, '\0'};
                    return py::cast(&buf[0]).inc_ref(); }
        // An unboxed pointer (a set guard's Set *, a partial application's
        // InfoTable *) is exposed as the integer value of the pointer.  A set
        // guard built from Python with an integer id yields that id, which is
        // what inspect.get_set_id returns on the Python backend.
        case 'x': return py::cast((uintptr_t) src.arg.blob).inc_ref();
        case 'u': return py::none().inc_ref();
        default :
          throw py::type_error(
              std::string("cannot convert an Expr of kind '") + src.kind + "'"
            );
      }
    }
  };
}}

namespace cyrt { namespace python
{
  void register_graph(pybind11::module_ mod)
  {
    // Tell the cyrt library how to interact with a Python iterator.
    register_generator_funcs(&generator_next);

    py::class_<InfoTable>(mod, "InfoTable")
      .def_readonly("arity"   , &InfoTable::arity)
      .def_readonly("flags"   , &InfoTable::flags)
      .def_readonly("format"  , &InfoTable::format)
      .def_readonly("name"    , &InfoTable::name)
      .def_readonly("tag"     , &InfoTable::tag)
      .def_readwrite("typedef", &InfoTable::type)
      .def_property_readonly("typetag", &typetag)
      .def_property_readonly("is_special", &is_special)
      .def_property_readonly("is_primitive", &is_primitive)
      .def_property_readonly("is_int", &is_int)
      .def_property_readonly("is_char", &is_char)
      .def_property_readonly("is_float", &is_float)
      .def_property_readonly("is_bool", &is_bool)
      .def_property_readonly("is_list", &is_list)
      .def_property_readonly("is_tuple", &is_tuple)
      .def_property_readonly("is_io", &is_io)
      .def_property_readonly("is_partial", &is_partial)
      .def_property_readonly("is_monadic", &is_monadic)
      .def_property_readonly("is_operator", &is_operator)
      .def("__repr__", &InfoTable::repr)
      .def("step", &InfoTable_step)
      ;

    // Fundamental symbols.
    mod.attr("Choice")              = py::cast(&Choice_Info             , reference);
    mod.attr("Failure")             = py::cast(&Fail_Info               , reference);
    mod.attr("Free")                = py::cast(&Free_Info               , reference);
    mod.attr("Fwd")                 = py::cast(&Fwd_Info                , reference);
    mod.attr("NonStrictConstraint") = py::cast(&NonStrictConstraint_Info, reference);
    mod.attr("PartApplic")          = py::cast(&PartApplic_Info         , reference);
    mod.attr("SetGuard")            = py::cast(&SetGuard_Info           , reference);
    mod.attr("StrictConstraint")    = py::cast(&StrictConstraint_Info   , reference);
    mod.attr("ValueBinding")        = py::cast(&ValueBinding_Info       , reference);

    py::class_<Arg, ByValueHolder<Arg>>(mod, "Arg")
      .def(py::init<Node *>())
      .def(py::init<unboxed_int_type>())
      .def(py::init<unboxed_float_type>())
      .def(py::init([](char const * str) {
          if(!str || !str[0] || str[1])
            throw py::value_error("expected a string of length one");
          return Arg(str[0]);
        }))
      .def(py::init([](py::handle obj) {
          obj.inc_ref(); // FIXME: leak
          return Arg(obj.ptr());
        }))
      .def("__repr__", &Arg::repr)
      ;

    py::class_<Node>(mod, "Node")
      // TODO attach a refcount.  Wild nodes attached to Python objects need to
      // be added to the GC roots.
      .def_static("create", &Node_create, reference) // FIXME: never delete Nodes (for now)
      .def("forward_to", &forward_node)
      .def_readonly("info", &Node::info, reference_internal)
      .def("successor"
          , [](Node & self, index_type pos) -> Expr { return self.successor(pos); }
          )
      .def_property_readonly("successors"
          , [](Node & self) -> std::vector<Expr>
            {
              std::vector<Expr> vec;
              for(index_type i=0; i<self.size(); ++i)
                vec.push_back(self.successor(i));
              return vec;
            }
          )
      .def("set_successor"
          , [](Node & self, index_type pos, Node * value)
            {
              if(pos >= self.size())
                throw py::index_error("node index out of range");
              if(self.info->format[pos] != 'p')
                throw py::type_error("successor is not a node");
              *self.successor(pos) = value;
            }
          )
      .def("__str__", (std::string(Node::*)()) &Node::str)
      .def("__repr__", (std::string(Node::*)()) &Node::repr)
      .def("id", [](Node * self) { return (uintptr_t) self; })
      .def("copy", &Node::copy, reference)
      .def("__copy__", &Node::copy, reference)
      .def("__deepcopy__", &Node::deepcopy, reference)
      .def("__getitem__", [](Node & self, index_type pos) -> Expr { return self[pos]; })
      .def("__hash__", &Node::hash)
      .def("__eq__", &Node::operator==)
      .def("__ne__", &Node::operator!=)
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

  void register_evaluator(pybind11::module_ mod)
  {
    py::class_<InterpreterState>(mod, "InterpreterState")
      .def(py::init<>())
      ;

    py::class_<RuntimeState>(mod, "RuntimeStateBase")
      .def(py::init<InterpreterState &, Node *, bool, SetFStrategy, size_t>())
      .def_readonly("steps_total", &RuntimeState::steps_total)
      // The Curry program writes to the C standard output, and Python keeps
      // its own buffer on the same file descriptor.  Flush the C buffer when
      // control returns to Python, with a value or with an error, so the
      // program's output precedes what Python prints next.
      .def("next", [](RuntimeState & rts) -> Expr
        {
          struct FlushStdout { ~FlushStdout() { std::fflush(stdout); } } flush;
          return rts.procD();
        })
      ;
  }
}}
