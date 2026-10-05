#include <cassert>
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <string>
#include "cyrt/builtins.hpp"
#include "cyrt/graph/infotable.hpp"
#include "cyrt/graph/memory.hpp"
#include "cyrt/graph/node.hpp"
#include "cyrt/state/rts.hpp"
#include "cyrt/utf8.hpp"
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
    EvaluationScope evaluation_scope;
    rts->set_goal(root);
    info->step(rts, rts->C());
    rts->drop();
  }

  // One rewrite step at the root of ``root``, outside procD, for
  // evaluator.single_step.  The step is counted as procS counts it: only a
  // completed rewrite (a status of E_RESTART or above) is a step.  The
  // evaluator makes the state for ``root``, so the front configuration holds
  // it already and takes the step; a state made for another goal gets a
  // configuration for the step, dropped afterwards.  So the queue holds one
  // configuration during the step, as the scheduler counters expect of a
  // step outside a search.
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
    EvaluationScope evaluation_scope;
    bool const own = !rts->Q()->empty() && rts->C()->root_storage == root;
    if(!own)
      rts->set_goal(root);
    xid_type const xid0 = rts->istate.xidfactory;
    auto status = root->info->step(rts, rts->C());
    if(status >= E_RESTART)
      rts->count_step();
    if(!own)
      rts->drop();
    // The variables the step created outlive this state.  Count them (the
    // ids of the choices made by the step share the factory, so the count
    // may exceed the variables), so that set_goal registers them when a
    // later goal holds them.  The table itself is the weak table of the
    // interpreter state, which the collector may sweep in the meantime.
    rts->istate.external_freevars += rts->istate.xidfactory - xid0;
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
      { if(node) gc_add_root(node); }
    RootHolder(RootHolder const & other) : node(other.node)
      { if(node) gc_add_root(node); }
    RootHolder & operator=(RootHolder const &) = delete;
    ~RootHolder() { if(node) gc_remove_root(node); }
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
  // interpreter lock held, as every entry into the runtime holds it.
  void py_generator_acquire(void * data)
  {
    Py_INCREF((PyObject *) data);
  }

  void py_generator_release(void * data)
  {
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
  void register_graph(pybind11::module_ mod)
  {
    // Tell the cyrt library how to interact with a Python iterator.
    register_generator_funcs(
        &generator_next, &py_generator_acquire, &py_generator_release
      );

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
      .def_property_readonly("address"
        , [](InfoTable const & self) { return (uintptr_t) &self; }
        , "The address of the table in the process (see "
          "curry.backends.cxx.tiered).")
      .def_property_readonly("has_step"
        , [](InfoTable const & self) { return self.step != nullptr; }
        , "Whether the table has a step function: compiled, interpreted, or "
          "built in.")
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
      // A str of length one gives the code point of its character.
      .def(py::init([](py::str str) {
          if(PyUnicode_GetLength(str.ptr()) != 1)
            throw py::value_error("expected a string of length one");
          return Arg((unboxed_char_type) PyUnicode_ReadChar(str.ptr(), 0));
        }))
      // An Arg borrows a Python object.  Node.create takes the reference a
      // generator node owns (see Node_create).
      .def(py::init([](py::handle obj) { return Arg(obj.ptr()); }))
      .def("__repr__", &Arg::repr)
      ;

    // A wrapper keeps its node alive: see RootHolder.  The collector frees
    // the node after the last wrapper is destroyed and nothing else reaches
    // it.
    py::class_<Node, RootHolder<Node>>(mod, "Node")
      .def_static("create", &Node_create, reference)
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
          )
      .def("forward_to", &forward_node)
      .def_readonly("info", &Node::info, reference_internal)
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
          )
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

    // The collector.  See cyrt/graph/gc/wdgc.cpp.
    mod.def("gc_collect", &gc_collect
      , "Runs a collection between evaluations; returns the number of nodes reclaimed.");
    mod.def("gc_verify", &gc_verify_
      , "Runs a collection with the heap verifier between evaluations; "
        "returns the first problem found, or None.");
    mod.def("gc_block_count", &gc_num_blocks
      , "The number of heap blocks that hold nodes, the spans of large nodes included.");
    mod.def("gc_heap_bytes", &gc_heap_bytes
      , "The bytes the node heap holds from the system, in use or pooled.");
    mod.def("gc_node_count", &gc_num_nodes
      , "The number of nodes allocated and not yet reclaimed.");
    mod.def("gc_allocation_count", &gc_num_allocations
      , "The number of nodes allocated since the start, reclaimed or not.");
    mod.def("gc_root_count", [](Node * node) { return node ? gc_root_count(node) : 0; }
      , "The number of registrations of a node as a root.");
    mod.def("gc_num_roots", &gc_num_roots
      , "The number of nodes registered as roots.");
    mod.def("gc_literal_count", &gc_num_literals
      , "The number of literal nodes: the tables of the small values and the "
        "literals of the loaded modules.");
    mod.def("gc_is_literal", [](Node * node) { return node && gc_is_literal(node); }
      , "Whether a node is a literal node, which the collector never frees.");
    mod.def("gc_freevar_count", &gc_num_freevars
      , "The entries of the free-variable tables: the free variables the "
        "collector keeps.");
    mod.def("small_int"
      , [](unboxed_int_type value) -> Node *
        {
          if(value < SMALL_INT_MIN || value > SMALL_INT_MAX)
            throw py::value_error("not a small integer");
          return g_small_ints[value - SMALL_INT_MIN];
        }
      , reference
      , "The shared node of an integer from SMALL_INT_MIN to SMALL_INT_MAX.");
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
      , "The shared node of a character up to SMALL_CHAR_MAX.");
    mod.def("gc_collections", &gc_num_collections
      , "The number of collections run so far.");
    mod.def("gc_backend", &gc_backend_name
      , "The collector of the runtime: 'wdgc' (the block heap and the "
        "mark-and-sweep collector) or 'mps' (the Memory Pool System).");
    mod.def("gc_fault_count", &gc_fault_count
      , "The barrier faults the collector handled; zero for wdgc.");
    mod.def("gc_backend_stats"
      , []()
        {
          py::dict stats;
          for(auto const & pair: gc_backend_stats())
            stats[py::str(pair.first)] = pair.second;
          return stats;
        }
      , "Statistics of the collector by name; empty for wdgc.");
    mod.def("gc_seconds", &gc_seconds
      , "The time spent in collections, in seconds.");
    mod.def("gc_threshold", &gc_threshold
      , "The number of nodes at which the next collection runs.");
    mod.def("gc_set_threshold", &gc_set_threshold
      , "Sets the collection threshold; the adaptive policy never goes below it.");
    mod.def("gc_growth", &gc_growth
      , "The growth factor: after a collection the threshold is this many times the survivors.");
    mod.def("gc_stress", &gc_stress
      , "True when the collector runs at every safepoint (SPRITE_GC_STRESS=1).");
    mod.def("gc_eval_depth", &gc_eval_depth
      , "The number of evaluations on the C stack.");
    // The objects of the scheduler, for leak checks.  See state/queue.hpp.
    mod.def("gc_configuration_count", &gc_num_configurations
      , "The number of configurations alive, in every queue of every evaluation.");
    mod.def("gc_queue_count", &gc_num_queues
      , "The number of queues alive: the outermost queue of every evaluation, "
        "and the queues of set functions not yet freed.");
    mod.def("gc_set_count", &gc_num_sets
      , "The number of sets of set functions alive.");
    mod.def("gc_queue_lengths", &gc_queue_lengths
      , "The number of configurations in each queue alive, in no particular order.");

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
      .def_property_readonly("address"
        , [](DataType const & self) { return (uintptr_t) &self; }
        , "The address of the type in the process (see "
          "curry.backends.cxx.tiered).")
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
    py::class_<InterpreterState>(mod, "InterpreterState")
      .def(py::init<>())
      .def_readwrite(
          "external_freevars", &InterpreterState::external_freevars
        , "The free variables made outside an evaluation; see state/rts.hpp."
        )
      ;

    mod.def("scheduler_counters_enabled", &scheduler_counters_enabled
      , "True when the runtime was built with the scheduler counters "
        "(make COUNTERS=1).");

    py::class_<RuntimeState>(mod, "RuntimeStateBase")
      .def(py::init<InterpreterState &, Node *, bool, SetFStrategy, size_t>())
      .def_readonly("steps_total", &RuntimeState::steps_total)
      .def_readonly("forks_total", &RuntimeState::forks_total)
      .def_property_readonly("vtable", &RuntimeState_vtable
        , "The variable table as a dict from id to node.")
      .def("scheduler_counters", &RuntimeState_scheduler_counters
        , "The scheduler counters of this evaluation as a dict, or None in a "
          "plain build.")
      .def("single_step", &RuntimeState_single_step)
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
