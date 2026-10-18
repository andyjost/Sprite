#include "heap.hpp"
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <string>
#include "cyrt/builtins.hpp"
#include "cyrt/checker.hpp"
#include "cyrt/exceptions.hpp"
#include "cyrt/graph/infotable.hpp"
#include "cyrt/graph/memory.hpp"
#include "cyrt/graph/node.hpp"
#include "cyrt/module.hpp"
#include "cyrt/state/rts.hpp"
#include "cyrt/ticker.hpp"
#include "cyrt/utf8.hpp"
#include "pybind11/pybind11.h"
#include "pybind11/stl.h"

namespace py = pybind11;
static auto constexpr reference = py::return_value_policy::reference;
static auto constexpr reference_internal = py::return_value_policy::reference_internal;

namespace cyrt { namespace python
{
  // Int is 64 bits.  A Python int outside the range is refused where it
  // would enter a node, with CurryTypeError and the message of the Python
  // backend (backends/py/graph/node.py), so the two backends agree (issue
  // #105).  The Arg binding below and the literals of the ICurry
  // interpreter (icurry.cpp) raise it.
  [[noreturn]] void raise_int_range_error(py::handle value)
  {
    std::string const message = std::string(py::str(value))
        + " is outside the range of Int (-9223372036854775808 to 9223372036854775807)";
    py::object const type =
        py::module_::import("curry.exceptions").attr("CurryTypeError");
    PyErr_SetString(type.ptr(), message.c_str());
    throw py::error_already_set();
  }
}}

namespace
{
  using namespace cyrt;
  using cyrt::python::raise_int_range_error;

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
      gc_count_write(source);
      NodeU{source}.fwd->target = target;
      return;
    }
    if(is_pinned(*source->info))
      throw py::value_error(
          std::string("cannot forward the shared node ") + source->info->name
        );
    // A node of a primitive value may be one of the shared literal nodes
    // (see builtins.hpp); no value is ever a redex.
    if(is_primitive(*source->info))
      throw py::value_error(
          std::string("cannot forward a value of type ") + source->info->name
        );
    // Nor is a shared partial application (partial_node), or any other node
    // of the arena.
    if(gc_is_literal(source))
      throw py::value_error(
          std::string("cannot forward the shared node ") + source->info->name
        );
    if(source->info->alloc_size < sizeof(FwdNode))
      throw py::value_error(
          std::string("node ") + source->info->name + " is too small to forward"
        );
    gc_count_write(source);
    source->forward_to(target);
  }

  Node * Node_create(
      InfoTable const * info, std::vector<Arg> const & args
    , Node * target, bool partial
    )
  {
    // The count must match the arity, or be below it for a partial
    // application.  Node::create packs the arguments by the format of the
    // table and never counts them, so a surplus would be dropped in silence
    // and a shortfall read past the vector.  The message is the one the
    // Python backend raises.
    size_t const nargs = args.size();
    if(partial ? nargs >= info->arity : nargs != info->arity)
      throw py::type_error(
          std::string("cannot ") + (partial ? "curry" : "construct") + " '"
            + info->name + "' (arity=" + std::to_string(info->arity)
            + "), with " + std::to_string(nargs)
            + (nargs == 1 ? " arg" : " args")
        );
    Node * node = partial
        ? Node::create_partial(info, args.data(), args.size())
        : Node::create(info, args.data());
    // A generator node owns a reference to its Python iterator (see
    // biGeneratorNode in builtins.hpp).  The Arg only borrowed it.
    if(!partial && info == &_biGenerator_Info && !args.empty())
      generator_acquire((void *) args[0].blob);
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
    // A step may rewrite its redex in place, within the block of a node of
    // its own info table.
    if(!root || root->info != info)
      throw py::value_error(
          std::string("the node is not an application of ") + info->name
        );
    // The step runs outside procD.  A set function inside it starts a
    // nested evaluation, whose collections must keep the nodes this step
    // holds.
    py::gil_scoped_release release;
    HeapScope heap;
    EvaluationScope evaluation_scope;
    rts->set_goal(root);
    info->step(rts, rts->C());
    gc_count_redex_write(root);
    rts->drop();
  }

  // One rewrite step at the root of ``root``, outside procD, for
  // evaluator.single_step.  The step is counted as procS counts it: only a
  // completed rewrite (a status of E_RESTART or above) is a step.  The
  // evaluator makes the state for ``root``, so the front configuration holds
  // it already and takes the step; a state made for another goal gets a
  // configuration for the step, dropped afterwards.  So the queue holds one
  // configuration during the step, as the scheduler counters expect of a
  // step outside a search.  A step that reports an error (E_ERROR: the
  // error primitive, or the trap step of a function without code) raises
  // it, as procD would.
  void RuntimeState_single_step(RuntimeState * rts, Node * root)
  {
    // Only a function node has a step.  A constructor, a value, or a
    // forward node has none (a pinned constructor keeps its static object
    // in that field), so the request is an error, not a call.
    if(!root || root->info->tag != T_FUNC)
      throw py::value_error(
          std::string("cannot step a node that is not a function application: ")
          + (root ? root->info->name : "null")
        );
    py::gil_scoped_release release;
    HeapScope heap;
    EvaluationScope evaluation_scope;
    bool const own = !rts->Q()->empty() && rts->C()->root_storage == root;
    if(!own)
      rts->set_goal(root);
    xid_type const xid0 = rts->istate.xidfactory;
    auto status = root->info->step(rts, rts->C());
    gc_count_redex_write(root);
    if(status >= E_RESTART)
      rts->count_step();
    std::string error;
    if(status == E_ERROR)
      error = rts->C()->pop_error().second;
    if(!own)
      rts->drop();
    // The variables the step created outlive this state.  Count them (the
    // ids of the choices made by the step share the factory, so the count
    // may exceed the variables), so that set_goal registers them when a
    // later goal holds them.  The table itself is the weak table of the
    // interpreter state, which the collector may sweep in the meantime.
    rts->istate.external_freevars += rts->istate.xidfactory - xid0;
    if(status == E_ERROR)
      throw EvaluationError(error);
  }

  // The variable table as a dict from id to node, for the tests of the
  // registration in set_goal.  The table is the weak table of the
  // interpreter state (see state/rts.hpp).  The wrappers root the nodes
  // while they live.
  py::dict RuntimeState_vtable(RuntimeState & rts)
  {
    py::dict table;
    for(auto const & entry: rts.istate.vtable)
      table[py::int_(entry.first)] = py::cast(entry.second, reference);
    return table;
  }

  template<typename T>
  struct ByValueHolder
  {
    ByValueHolder(T arg) : data(arg) {}
    T data;
    T * get() { return &data; }
  };

  // The holder of a Node wrapper.  The node is a root of the collector for
  // as long as the wrapper lives.  pybind11 constructs one holder per
  // wrapper (always_construct_holder), and one wrapper per node address.
  template<typename T>
  struct RootHolder
  {
    explicit RootHolder(T * node) : node(node)
      { if(node) { cyrt::python::HeapAccessScope lock(false); gc_add_root(node); } }
    RootHolder(RootHolder const & other) : node(other.node)
      { if(node) { cyrt::python::HeapAccessScope lock(false); gc_add_root(node); } }
    RootHolder & operator=(RootHolder const &) = delete;
    ~RootHolder() { if(node) { cyrt::python::HeapAccessScope lock(false); gc_remove_root(node); } }
    T * get() const { return node; }
    T * node;
  };

  // Runs a collection on behalf of Python.  Returns the number of nodes
  // reclaimed.
  size_t gc_collect()
  {
    if(gc_eval_depth() != 0)
      throw std::runtime_error(
          "cannot run the collector while an evaluation is active"
        );
    size_t const before = gc_num_nodes();
    run_gc();
    return before - gc_num_nodes();
  }

  // The counters of the collector as a dict, in the order of the fields.
  py::dict counters_dict(GcCounters const & c)
  {
    py::dict dict;
    dict["roots_seconds"] = c.roots_seconds;
    dict["trace_seconds"] = c.trace_seconds;
    dict["sweep_seconds"] = c.sweep_seconds;
    dict["registries_seconds"] = c.registries_seconds;
    dict["marked"] = c.marked;
    dict["marked_old"] = c.marked_old;
    dict["marked_young"] = c.marked_young;
    dict["configurations_pushed"] = c.configurations_pushed;
    dict["queues_destroyed"] = c.queues_destroyed;
    dict["configurations_destroyed"] = c.configurations_destroyed;
    dict["old_redexes"] = c.old_redexes;
    dict["old_slot_writes"] = c.old_slot_writes;
    dict["old_nodes_written"] = c.old_nodes_written;
    dict["old_blocks"] = c.old_blocks;
    return dict;
  }

  // Runs a collection with the heap verifier.  Returns the problem found,
  // or None.
  py::object gc_verify_()
  {
    std::string const problem = gc_verify();
    if(problem.empty())
      return py::none();
    return py::str(problem);
  }

  // The Python str of length one for a code point.  Returns a new reference.
  py::handle char_to_python(unboxed_char_type cp)
  {
    // A value above the last code point (prim_chr does not check its
    // argument) becomes REPLACEMENT_CHAR, as utf8_encode writes it, so that
    // a traversal of a value does not raise from the caster.
    if(cp > MAX_CODE_POINT)
      cp = REPLACEMENT_CHAR;
    PyObject * str = PyUnicode_FromOrdinal((int) cp);
    if(!str)
      throw py::error_already_set();
    return str;
  }

  Node * generator_next(void * data)
  {
    py::gil_scoped_acquire gil;
    assert(data);
    auto * pyobj = (PyObject *) data;
    py::object value = py::reinterpret_steal<py::object>(PyIter_Next(pyobj));
    if(PyErr_Occurred()) { throw py::error_already_set(); }
    // Note: the Node * is not owned directly by the PyObject but rather by the
    // garbage collector.  So it is safe to extract the Node * and return it
    // this way.
    return value.ptr() ? py::cast<Node *>(value) : (Node *) nullptr;
  }

  // The reference a generator node owns (see biGeneratorNode in
  // builtins.hpp).  The release may run Python code: the finalizer of a
  // generator object.  The collector calls it after its sweep, with the
  // heap lock held; the binding acquires the GIL for the finalizer.
  void py_generator_acquire(void * data)
  {
    py::gil_scoped_acquire gil;
    Py_INCREF((PyObject *) data);
  }

  void py_generator_release(void * data)
  {
    py::gil_scoped_acquire gil;
    Py_DECREF((PyObject *) data);
  }
}

PYBIND11_DECLARE_HOLDER_TYPE(T, ByValueHolder<T>, true)
PYBIND11_DECLARE_HOLDER_TYPE(T, RootHolder<T>, true)

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
        // A Char is a code point; Python sees a str of length one.
        case 'c': return char_to_python(src.arg.ub_char);
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
  py::object RuntimeState_next(RuntimeState & rts, bool event)
  {
    // Root the result while the heap is still protected. Returning a Python
    // object lets this hot entry use a stack scope instead of a loader
    // patient, without unlocking before pybind11 registers the node's root.
    HeapAccessScope heap;
    struct FlushStdout { ~FlushStdout() { std::fflush(stdout); } } flush;
    Expr result;
    {
      py::gil_scoped_release release;
      result = rts.root_queue ? rts.procD() : Expr{};
    }
    py::object value = py::cast(result);
    if(event && !value.is_none())
      return py::make_tuple(rts.stream_yielded, value);
    return value;
  }

  void register_graph(pybind11::module_ mod)
  {
    // Tell the cyrt library how to interact with a Python iterator.
    register_generator_funcs(
        &generator_next, &py_generator_acquire, &py_generator_release
      );

    py::class_<InfoTable>(mod, "InfoTable")
      .def_readonly("arity"   , &InfoTable::arity, cyrt::python::heap_access{})
      .def_readonly("flags"   , &InfoTable::flags, cyrt::python::heap_access{})
      .def_readonly("format"  , &InfoTable::format, cyrt::python::heap_access{})
      .def_readonly("name"    , &InfoTable::name, cyrt::python::heap_access{})
      .def_readonly("tag"     , &InfoTable::tag, cyrt::python::heap_access{})
      .def_readwrite("typedef", &InfoTable::type, cyrt::python::heap_access{})
      .def_property_readonly("typetag", &typetag, cyrt::python::heap_access{})
      .def_property_readonly("is_special", &is_special, cyrt::python::heap_access{})
      .def_property_readonly("is_primitive", &is_primitive, cyrt::python::heap_access{})
      .def_property_readonly("is_int", &is_int, cyrt::python::heap_access{})
      .def_property_readonly("is_char", &is_char, cyrt::python::heap_access{})
      .def_property_readonly("is_float", &is_float, cyrt::python::heap_access{})
      .def_property_readonly("is_bool", &is_bool, cyrt::python::heap_access{})
      .def_property_readonly("is_list", &is_list, cyrt::python::heap_access{})
      .def_property_readonly("is_tuple", &is_tuple, cyrt::python::heap_access{})
      .def_property_readonly("is_io", &is_io, cyrt::python::heap_access{})
      .def_property_readonly("is_partial", &is_partial, cyrt::python::heap_access{})
      .def_property_readonly("is_monadic", &is_monadic, cyrt::python::heap_access{})
      .def_property_readonly("is_operator", &is_operator, cyrt::python::heap_access{})
      .def("__repr__", &InfoTable::repr, cyrt::python::heap_access{})
      .def("step", &InfoTable_step, cyrt::python::heap_access{})
      .def_property_readonly("address"
        , [](InfoTable const & self) { return (uintptr_t) &self; }
        , "The address of the table in the process (see "
          "curry.backends.cxx.tiered).", cyrt::python::heap_access{})
      .def_property_readonly("has_step"
        , [](InfoTable const & self)
            { return self.step != nullptr && !is_trapped(&self); }
        , "Whether the table has a step function: compiled, interpreted, or "
          "built in.  The trap step of a function without code (see "
          "install_trap) is not one.", cyrt::python::heap_access{})
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
      .def(py::init<Node *>(), cyrt::python::heap_access{})
      .def(py::init<unboxed_int_type>(), cyrt::python::heap_access{})
      // A Python int that the 64-bit overload refused is outside the range
      // of Int.  Without this overload the one below took it, and the node
      // held the bits of a double.
      .def(py::init([](py::int_ value) -> Arg { raise_int_range_error(value); }), cyrt::python::heap_access{})
      .def(py::init<unboxed_float_type>(), cyrt::python::heap_access{})
      // A str of length one gives the code point of its character.
      .def(py::init([](py::str str) {
          if(PyUnicode_GetLength(str.ptr()) != 1)
            throw py::value_error("expected a string of length one");
          return Arg((unboxed_char_type) PyUnicode_ReadChar(str.ptr(), 0));
        }), cyrt::python::heap_access{})
      // An Arg borrows a Python object.  Node.create takes the reference a
      // generator node owns (see Node_create).
      .def(py::init([](py::handle obj) { return Arg(obj.ptr()); }), cyrt::python::heap_access{})
      .def("__repr__", &Arg::repr, cyrt::python::heap_access{})
      ;

    // A wrapper keeps its node alive: see RootHolder.  The collector frees
    // the node after the last wrapper is destroyed and nothing else reaches
    // it.
    py::class_<Node, RootHolder<Node>>(mod, "Node")
      .def_static("create", &Node_create, reference, cyrt::python::heap_access{})
      // A Curry string from a Python str, in one call: the list of Char
      // nodes the step of _biString builds (build_curry_string), one node
      // per code point, with the text taken by its length, so that a NUL
      // inside the text is a character.  A biStringNode points at a buffer
      // the runtime does not own: compiled code points its nodes at static
      // literals, and a buffer owned by a node would need a finalizer in
      // every collector and in the copier.  So the typed builder asks for
      // the list the step would make.  With ``target``, the target is
      // forwarded to the list and returned.
      .def_static("create_string"
          , [](py::str text, Node * target) -> Node *
            {
              Py_ssize_t size = 0;
              char const * pos = PyUnicode_AsUTF8AndSize(text.ptr(), &size);
              if(!pos)
                throw py::error_already_set();
              char const * const end = pos + size;
              Node * head = nil();
              Node ** tail = &head;
              while(pos != end)
              {
                *tail = cons(char_(utf8_decode(pos, end)), nil());
                tail = &NodeU{*tail}.cons->tail;
              }
              if(target)
              {
                forward_node(target, head);
                return target;
              }
              return head;
            }
          , py::arg("text"), py::arg("target") = nullptr
          , reference
          , cyrt::python::heap_access{})
      .def("forward_to", &forward_node, cyrt::python::heap_access{})
      .def_readonly("info", &Node::info, reference_internal, cyrt::python::heap_access{})
      // The info table of the head of a partial application, or None.  The
      // typed builder types such a value by the scheme of its head.
      .def_property_readonly("partial_head"
          , [](Node & self) -> InfoTable const *
            {
              if(!is_partial(*self.info))
                return nullptr;
              return NodeU{&self}.partapplic->head_info;
            }
          , reference
          , cyrt::python::heap_access{})
      .def("successor"
          , [](Node & self, index_type pos) -> Expr { return self.successor(pos); }
          , cyrt::python::heap_access{})
      .def_property_readonly("successors"
          , [](Node & self) -> std::vector<Expr>
            {
              std::vector<Expr> vec;
              for(index_type i=0; i<self.size(); ++i)
                vec.push_back(self.successor(i));
              return vec;
            }
          , cyrt::python::heap_access{})
      .def("set_successor"
          , [](Node & self, index_type pos, Node * value)
            {
              if(pos >= self.size())
                throw py::index_error("node index out of range");
              if(self.info->format[pos] != 'p')
                throw py::type_error("successor is not a node");
              gc_count_write(&self);
              *self.successor(pos) = value;
            }
          , cyrt::python::heap_access{})
      .def("__str__", (std::string(Node::*)()) &Node::str, cyrt::python::heap_access{})
      .def("__repr__", (std::string(Node::*)()) &Node::repr, cyrt::python::heap_access{})
      .def("id", [](Node * self) { return (uintptr_t) self; }, cyrt::python::heap_access{})
      .def("copy", &Node::copy, reference, cyrt::python::heap_access{})
      .def("__copy__", &Node::copy, reference, cyrt::python::heap_access{})
      .def("__deepcopy__"
          , [](py::object self, py::object memo) -> py::object
            {
              if(memo.is_none())
                return py::cast(self.cast<Node *>()->deepcopy(), reference);
              py::dict table = memo.cast<py::dict>();
              py::int_ const key(reinterpret_cast<uintptr_t>(self.ptr()));
              if(table.contains(key))
                return table[key];
              py::object copy = py::cast(
                  self.cast<Node *>()->deepcopy(), reference
                );
              table[key] = copy;
              // Keep the original alive while its Python id is in the memo.
              py::int_ const keepkey(reinterpret_cast<uintptr_t>(memo.ptr()));
              table.attr("setdefault")(keepkey, py::list()).attr("append")(self);
              return copy;
            }
          , py::arg("memo") = py::none()
          , cyrt::python::heap_access{})
      .def("__getitem__"
          , [](Node & self, py::int_ index) -> Expr
            {
              int overflow = 0;
              long pos = PyLong_AsLongAndOverflow(index.ptr(), &overflow);
              if(pos == -1 && PyErr_Occurred())
                throw py::error_already_set();
              long const arity = self.size();
              if(overflow || pos < -arity || pos >= arity)
              {
                py::object const type =
                    py::module_::import("curry.exceptions").attr("CurryIndexError");
                PyErr_SetString(type.ptr(), "node index out of range");
                throw py::error_already_set();
              }
              if(pos < 0)
                pos += arity;
              return self[static_cast<index_type>(pos)];
            }
          , cyrt::python::heap_access{})
      .def("__hash__", &Node::hash, cyrt::python::heap_access{})
      // A value that is not a node is never equal to one.  The operator tag
      // turns the failed argument cast into NotImplemented, so Python
      // answers False for == and True for != against a foreign object, as
      // its data model expects (the Python backend answers the same way).
      .def("__eq__", &Node::operator==, py::is_operator(), cyrt::python::heap_access{})
      .def("__ne__", &Node::operator!=, py::is_operator(), cyrt::python::heap_access{})
      ;

    // The collector.  See cyrt/graph/gc/wdgc.cpp.
    mod.def("gc_collect", &gc_collect
      , "Runs a collection between evaluations; returns the number of nodes reclaimed.", cyrt::python::heap_access{});
    mod.def("gc_verify", &gc_verify_
      , "Runs a collection with the heap verifier between evaluations; "
        "returns the first problem found, or None.", cyrt::python::heap_access{});
    mod.def("gc_block_count", &gc_num_blocks
      , "The number of heap blocks that hold nodes, the spans of large nodes included.", cyrt::python::heap_access{});
    mod.def("gc_heap_bytes", &gc_heap_bytes
      , "The bytes the node heap holds from the system, in use or pooled.", cyrt::python::heap_access{});
    mod.def("gc_node_count", &gc_num_nodes
      , "The number of nodes allocated and not yet reclaimed.", cyrt::python::heap_access{});
    mod.def("gc_allocation_count", &gc_num_allocations
      , "The number of nodes allocated since the start, reclaimed or not.", cyrt::python::heap_access{});
    mod.def("gc_root_count", [](Node * node) { return node ? gc_root_count(node) : 0; }
      , "The number of registrations of a node as a root.", cyrt::python::heap_access{});
    mod.def("gc_num_roots", &gc_num_roots
      , "The number of nodes registered as roots.", cyrt::python::heap_access{});
    mod.def("gc_literal_count", &gc_num_literals
      , "The number of literal nodes: the tables of the small values and the "
        "literals of the loaded modules.", cyrt::python::heap_access{});
    mod.def("gc_is_literal", [](Node * node) { return node && gc_is_literal(node); }
      , "Whether a node is a literal node, which the collector never frees.", cyrt::python::heap_access{});
    mod.def("gc_freevar_count", &gc_num_freevars
      , "The entries of the free-variable tables: the free variables the "
        "collector keeps.", cyrt::python::heap_access{});
    mod.def("small_int"
      , [](unboxed_int_type value) -> Node *
        {
          if(value < SMALL_INT_MIN || value > SMALL_INT_MAX)
            throw py::value_error("not a small integer");
          return g_small_ints[value - SMALL_INT_MIN];
        }
      , reference
      , "The shared node of an integer from SMALL_INT_MIN to SMALL_INT_MAX.", cyrt::python::heap_access{});
    mod.def("small_char"
      , [](py::str str) -> Node *
        {
          if(PyUnicode_GetLength(str.ptr()) != 1)
            throw py::value_error("expected a string of length one");
          auto const cp = (unboxed_char_type) PyUnicode_ReadChar(str.ptr(), 0);
          if(cp > SMALL_CHAR_MAX)
            throw py::value_error("not an ASCII character");
          return g_small_chars[cp];
        }
      , reference
      , "The shared node of a character up to SMALL_CHAR_MAX.", cyrt::python::heap_access{});
    mod.def("gc_collections", &gc_num_collections
      , "The number of collections run so far.", cyrt::python::heap_access{});
    mod.def("gc_backend", &gc_backend_name
      , "The collector of the runtime: 'wdgc' (the block heap and the "
        "mark-and-sweep collector) or 'mps' (the Memory Pool System).", cyrt::python::heap_access{});
    mod.def("gc_fault_count", &gc_fault_count
      , "The barrier faults the collector handled; zero for wdgc.", cyrt::python::heap_access{});
    mod.def("gc_backend_stats"
      , []()
        {
          py::dict stats;
          for(auto const & pair: gc_backend_stats())
            stats[py::str(pair.first)] = pair.second;
          return stats;
        }
      , "Statistics of the collector by name; empty for wdgc.", cyrt::python::heap_access{});
    mod.def("gc_seconds", &gc_seconds
      , "The time spent in collections, in seconds.", cyrt::python::heap_access{});
    mod.def("gc_counters", []() { return counters_dict(gc_counters()); }
      , "The counters of the collector summed over the collections of the "
        "process: the seconds of the phases, the nodes marked by age, the "
        "configurations pushed, the queues and configurations destroyed, "
        "and the writes into old nodes.", cyrt::python::heap_access{});
    mod.def("gc_last_collection"
      , []() { return counters_dict(gc_last_collection()); }
      , "The counters of the last collection.", cyrt::python::heap_access{});
    mod.def("gc_old_node_count", &gc_num_old_nodes
      , "The number of old nodes: the nodes marked in the last collection.", cyrt::python::heap_access{});
    mod.def("gc_write_counters_enabled", &gc_write_counters_enabled
      , "True when the runtime counts the writes into old nodes "
        "(SPRITE_GC_WRITE_COUNTERS).", cyrt::python::heap_access{});
    mod.def("gc_threshold", &gc_threshold
      , "The number of nodes at which the next collection runs.", cyrt::python::heap_access{});
    mod.def("gc_set_threshold", &gc_set_threshold
      , "Sets the collection threshold; the adaptive policy never goes below it.", cyrt::python::heap_access{});
    mod.def("gc_growth", &gc_growth
      , "The growth factor: after a collection the threshold is this many times the survivors.", cyrt::python::heap_access{});
    mod.def("gc_stress", &gc_stress
      , "True when the collector runs at every safepoint (SPRITE_GC_STRESS=1).", cyrt::python::heap_access{});
    mod.def("gc_eval_depth", &gc_eval_depth
      , "The number of evaluations on the C stack.", cyrt::python::heap_access{});
    // The ticker of time mode (cyrt/ticker.hpp), for the tests.
    mod.def("ticker_status"
      , []()
        {
          TickerStatus const status = ticker_status();
          py::dict out;
          out["started"] = status.started;
          out["parked"] = status.parked;
          out["active"] = status.active;
          out["ticks"] = status.ticks;
          out["quantum_ns"] = status.quantum_ns;
          return out;
        }
      , "The state of the ticker thread of time mode: started (the thread "
        "exists in this process), parked (it waits for an evaluation), "
        "active (the evaluations in time mode on the C stack), ticks (the "
        "ticks set since the start of the process), and quantum_ns.", cyrt::python::heap_access{});
    // The count of the evaluations in time mode, for the tests: what the
    // outermost scheduler of such an evaluation does on entry and exit.
    mod.def("ticker_enter", &ticker_enter, py::arg("quantum_ns")
      , "Counts an evaluation in time mode on the C stack, as the outermost "
        "scheduler of such an evaluation does: the first one starts the "
        "ticker thread or wakes it.  For the tests; every call needs a "
        "ticker_leave.  A quantum of zero is a ValueError; a thread that "
        "cannot start is a RuntimeError, and the count is unchanged.", cyrt::python::heap_access{});
    mod.def("ticker_leave", &ticker_leave
      , "Ends the count of a ticker_enter.", cyrt::python::heap_access{});
    // The objects of the scheduler, for leak checks.  See state/queue.hpp.
    mod.def("gc_configuration_count", &gc_num_configurations
      , "The number of configurations alive, in every queue of every evaluation.", cyrt::python::heap_access{});
    mod.def("gc_queue_count", &gc_num_queues
      , "The number of queues alive: the outermost queue of every evaluation, "
        "and the queues of set functions not yet freed.", cyrt::python::heap_access{});
    mod.def("gc_set_count", &gc_num_sets
      , "The number of sets of set functions alive.", cyrt::python::heap_access{});
    mod.def("gc_queue_lengths", &gc_queue_lengths
      , "The number of configurations in each queue alive, in no particular order.", cyrt::python::heap_access{});

    py::class_<DataType>(mod, "DataType")
      .def_property_readonly(
          "constructors"
        , [](DataType const & self)
              { return std::vector(self.ctors, self.ctors+self.size); }
        , cyrt::python::heap_access{})
      .def_readonly("flags", &DataType::flags, cyrt::python::heap_access{})
      .def_readonly("kind", &DataType::kind, cyrt::python::heap_access{})
      .def_readonly("name", &DataType::name, cyrt::python::heap_access{})
      .def_readonly("size", &DataType::size, cyrt::python::heap_access{})
      .def_property_readonly("address"
        , [](DataType const & self) { return (uintptr_t) &self; }
        , "The address of the type in the process (see "
          "curry.backends.cxx.tiered).", cyrt::python::heap_access{})
      ;
  }

  // The scheduler counters of a runtime state (cyrt/state/counters.hpp) as a
  // dict of plain values and lists, for Interpreter.stats, which sums the
  // dicts of the evaluations of an interpreter.  None in a plain build.  The
  // configurations still in the outermost queue have not ended; they are
  // reported as "left" with their steps so far.  The queues of set functions
  // hang off SetEval nodes, so their left configurations are not known.
  py::object RuntimeState_scheduler_counters(RuntimeState & rts)
  {
    #ifdef SPRITE_SCHEDULER_COUNTERS
    SchedulerCounters const & c = rts.counters;
    auto histogram = [](StepHistogram const & h)
    {
      py::dict d;
      d["count"] = h.count;
      d["sum"] = h.sum;
      d["max"] = h.max;
      d["exact"] = std::vector<size_t>(h.exact, h.exact + StepHistogram::EXACT);
      d["coarse"] = std::vector<size_t>(
          h.coarse, h.coarse + StepHistogram::COARSE
        );
      return d;
    };
    auto queue = [&](size_t i, size_t left, size_t left_steps)
    {
      py::dict d;
      d["values"] = c.ended[i][END_VALUE];
      d["failures"] = c.ended[i][END_FAILURE];
      d["forked"] = c.ended[i][END_FORK];
      d["left"] = left;
      d["value_steps"] = c.end_steps[i][END_VALUE];
      d["failure_steps"] = c.end_steps[i][END_FAILURE];
      d["fork_steps"] = c.end_steps[i][END_FORK];
      d["left_steps"] = left_steps;
      d["lifetimes"] = histogram(c.lifetimes[i]);
      return d;
    };
    size_t left = 0, left_steps = 0;
    for(Configuration * C: *rts.root_queue)
    {
      ++left;
      left_steps += C->steps;
    }
    py::dict d;
    d["serial_steps"] = c.steps_serial;
    d["nested_steps"] = c.steps_nested;
    d["shared_steps"] = c.steps_shared;
    d["queue_max"] = c.queue_max;
    d["outer"] = queue(0, left, left_steps);
    d["nested"] = queue(1, 0, 0);
    return std::move(d);
    #else
    return py::none();
    #endif
  }

  bool scheduler_counters_enabled()
  {
    #ifdef SPRITE_SCHEDULER_COUNTERS
    return true;
    #else
    return false;
    #endif
  }

  void register_evaluator(pybind11::module_ mod)
  {
    py::class_<InterpreterState, HeapOwned<InterpreterState>>(mod, "InterpreterState")
      .def(py::init<>(), cyrt::python::heap_access{})
      .def_readwrite(
          "external_freevars", &InterpreterState::external_freevars
        , "The free variables made outside an evaluation; see state/rts.hpp."
        , cyrt::python::heap_access{})
      ;

    mod.def("_heap_status", []
      {
        auto counts = heap_status();
        py::dict result;
        result["entries"] = counts.entries;
        result["waits"] = counts.waits;
        result["handoffs"] = counts.handoffs;
        return result;
      }, heap_access{});

    mod.def("scheduler_counters_enabled", &scheduler_counters_enabled
      , "True when the runtime was built with the scheduler counters "
        "(make COUNTERS=1).", cyrt::python::heap_access{});

    py::class_<RuntimeState, HeapOwned<RuntimeState>>(mod, "RuntimeStateBase")
      // The fourth and fifth arguments are the rotation cadence: the
      // completed steps between two rotation checks (0 selects time mode)
      // and the quantum of time mode in nanoseconds (see cyrt/ticker.hpp).
      // The last one turns the checker of the run-time invariants on (see
      // cyrt/checker.hpp).
      .def(py::init<
          InterpreterState &, Node *, bool, size_t, size_t, uint64_t, bool, size_t
        >(), cyrt::python::heap_access{})
      .def(py::init<
          InterpreterState &, Node *, bool, size_t, size_t, uint64_t, bool
        >(), cyrt::python::heap_access{})
      // Without the last argument the checker is off (the tests of the
      // rotation build a state this way).
      .def(py::init<
          InterpreterState &, Node *, bool, size_t, size_t, uint64_t
        >(), cyrt::python::heap_access{})
      .def_readonly("_worker_attempts", &RuntimeState::worker_attempts, heap_access{})
      .def_readonly("_escalated", &RuntimeState::escalated, heap_access{})
      .def_readonly("steps_total", &RuntimeState::steps_total, cyrt::python::heap_access{})
      .def_readonly("forks_total", &RuntimeState::forks_total, cyrt::python::heap_access{})
      .def_readonly("stream_yielded", &RuntimeState::stream_yielded, cyrt::python::heap_access{})
      .def_property_readonly("queue_size", [](RuntimeState & rts)
        { return rts.root_queue ? rts.root_queue->size() : 0; }, cyrt::python::heap_access{})
      .def("close", [](RuntimeState & rts)
        {
          delete rts.checker;
          rts.checker = nullptr;
          #ifdef SPRITE_TRACE_ENABLED
          rts.trace.reset();
          #endif
          rts.qstack.clear();
          rts.root_queue.reset();
          rts.stream_event = nullptr;
          rts.stream_yielded = false;
        }, cyrt::python::heap_access{})
      .def_readwrite("step_limit", &RuntimeState::step_limit
        , "The step limit of the evaluation: NOLIMIT, or the value of "
          "steps_total after which the scheduler stops with StepLimitReached "
          "(see cyrt/state/rts.hpp).  RuntimeState.stepcounter sets it.", cyrt::python::heap_access{})
      .def_property_readonly("vtable", &RuntimeState_vtable
        , "The variable table as a dict from id to node.", cyrt::python::heap_access{})
      .def("scheduler_counters", &RuntimeState_scheduler_counters
        , "The scheduler counters of this evaluation as a dict, or None in a "
          "plain build.", cyrt::python::heap_access{})
      .def("single_step", &RuntimeState_single_step, cyrt::python::heap_access{})
      // The Curry program writes to the C standard output, and Python keeps
      // its own buffer on the same file descriptor.  Flush the C buffer when
      // control returns to Python, with a value or with an error, so the
      // program's output precedes what Python prints next.
      .def("next", [](RuntimeState & rts) { return RuntimeState_next(rts, false); })
      // Fetch the flag with the value, under the same lock and GIL release.
      .def("_next_event", [](RuntimeState & rts) { return RuntimeState_next(rts, true); })
      ;
  }
}}
