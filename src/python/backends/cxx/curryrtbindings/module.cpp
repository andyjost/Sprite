#include "heap.hpp"
#include "curryrt/curryrt.hpp"
#include "curryrt/bigint.hpp"
#include "curryrt/currylib/prelude.hpp"
#include "curryrt/currylib/library.hpp"
#include "curryrt/graph/memory.hpp"
#include <algorithm>
#include <cstring>
#include "pybind11/pybind11.h"
#include "pybind11/stl.h"
#include "curryrt/module.hpp"
#include "curryrt/state/rts.hpp"
#include "curryrt/utf8.hpp"
#include <string>
#include <vector>

namespace py = pybind11;
static auto constexpr reference = py::return_value_policy::reference;

namespace
{
  using namespace curryrt;

  Node * conversion_target(Node * node)
  {
    Node * slow = node;
    bool advance = false;
    while(node->info->tag == T_FWD)
    {
      node = NodeU{node}.fwd->target;
      if(advance) slow = NodeU{slow}.fwd->target;
      advance = !advance;
      if(node == slow)
        throw py::value_error("cyclic forward chain in list conversion");
    }
    return node;
  }

  Py_UCS4 conversion_char(Node * node)
  {
    auto cp = NodeU{node}.char_->value;
    // Match the node successor caster, including unchecked prim_chr values.
    return cp > MAX_CODE_POINT ? REPLACEMENT_CHAR : cp;
  }

  // Callbacks may allocate and request collection. Keep pending child addresses
  // stable as well as the rooted input graph while holding the heap gate and GIL.
  // Frames avoid using the C++ call stack for deeply nested normal forms.
  py::object convert_value(Node * node, py::function fallback, py::object char_type,
      py::function list_type, py::function component_types,
      bool strings, py::object type)
  {
    py::gil_scoped_acquire gil;
    GcClamp clamp;
    struct Frame
    {
      std::vector<Node *> children;
      py::object types;
      py::list items;
      bool tuple, join;
      size_t next = 0;
    };
    std::vector<Frame> stack;
    py::object result;
    while(true)
    {
      auto info = node->info;
      if(is_int(*info))
      {
        if(!is_bigint(node)) result = py::int_(NodeU{node}.int_->value);
        else
        {
          auto digits = integer_string(node);
          // Preserve unbounded Ints even with Python's decimal digit limit.
          if(digits.size() > 500)
            result = py::module_::import("curry.utility.strings").attr("parse_int")(digits);
          else
          {
            result = py::reinterpret_steal<py::object>(PyLong_FromString(
                const_cast<char *>(digits.c_str()), nullptr, 10));
            if(!result) throw py::error_already_set();
          }
        }
      }
      else if(is_float(*info)) result = py::float_(NodeU{node}.float_->value);
      else if(is_char(*info))
      {
        auto text = py::reinterpret_steal<py::object>(
            PyUnicode_FromOrdinal(conversion_char(node)));
        if(!text) throw py::error_already_set();
        result = char_type(text);
      }
      else if(info == &True_Info || info == &False_Info)
        result = py::bool_(info == &True_Info);
      else if(is_list(*info))
      {
        auto policy = list_type(type).cast<py::tuple>();
        py::object elemtype = policy[0];
        int mode = policy[1].cast<int>();
        std::vector<Node *> children;
        std::vector<Py_UCS4> chars;
        bool all_chars = true;
        Node * tail = node;
        while(tail->info == &Cons_Info)
        {
          auto head = conversion_target(tail->successors()[0].node);
          children.push_back(head);
          if(is_char(*head->info)) chars.push_back(conversion_char(head));
          else all_chars = false;
          tail = conversion_target(tail->successors()[1].node);
        }
        if(tail->info != &Nil_Info)
          result = fallback(py::cast(node, reference), strings, type);
        else if(strings && all_chars && (mode == 2 || (mode == 1 && !children.empty())))
        {
          result = py::reinterpret_steal<py::object>(PyUnicode_FromKindAndData(
              PyUnicode_4BYTE_KIND, chars.data(), chars.size()));
          if(!result) throw py::error_already_set();
        }
        else if(children.empty()) result = py::list();
        else
        {
          node = children.front();
          stack.push_back({std::move(children), elemtype, py::list(), false,
                           strings && mode == 2});
          type = elemtype;
          continue;
        }
      }
      else if(is_tuple(*info) || (info->name[0] == '(' &&
          std::string(info->name).find_first_not_of(',', 1) == std::strlen(info->name) - 1 &&
          info->name[std::strlen(info->name) - 1] == ')'))
      {
        std::vector<Node *> children;
        for(index_type i = 0; i < info->arity; ++i)
          children.push_back(node->successors()[i].node);
        if(children.empty()) result = py::tuple();
        else
        {
          auto types = component_types(type, children.size());
          node = children.front();
          type = types[py::int_(0)];
          stack.push_back({std::move(children), types, py::list(), true, false});
          continue;
        }
      }
      else result = fallback(py::cast(node, reference), strings, type);

      while(!stack.empty())
      {
        auto & frame = stack.back();
        frame.items.append(result);
        if(++frame.next < frame.children.size())
        {
          node = frame.children[frame.next];
          type = frame.tuple ? frame.types[py::int_(frame.next)] : frame.types;
          break;
        }
        result = frame.tuple ? py::object(py::tuple(frame.items)) : py::object(frame.items);
        if(frame.join)
        {
          bool text = true;
          for(auto item: frame.items) text = text && PyUnicode_Check(item.ptr());
          if(text) result = py::str("").attr("join")(frame.items);
        }
        stack.pop_back();
      }
      if(stack.empty()) return result;
    }
  }

  struct PythonPrimitive
  {
    std::string name, qualified_name, format;
    mutable py::object callable;
    InfoTable info;
    PythonPrimitive(std::string name, index_type arity, py::object callable,
                    bool monadic, stepfunc_type step)
      : name(std::move(name)), format(arity, 'p'), callable(std::move(callable)),
        info(T_FUNC, arity, sizeof(void *) * std::max<int>(arity + 1, 2),
             F_STATIC_OBJECT | (monadic ? F_MONADIC : 0),
             this->name.c_str(), format.c_str(), step, nullptr)
    { info.aux = this; }
  };

  // Arguments are already normalized before Python acquires the GIL.
  tag_type to_python(RuntimeState * rts, Configuration * C, Cursor value,
                     py::object & result)
  {
    tag_type tag = T_CTOR;
    Node * node = value;
    if(is_int(*node->info))
    {
      auto digits = integer_string(node);
      result = py::reinterpret_steal<py::object>(PyLong_FromString(
          const_cast<char *>(digits.c_str()), nullptr, 10));
      if(!result) throw py::error_already_set();
    }
    else if(is_float(*node->info)) result = py::float_(NodeU{node}.float_->value);
    else if(is_char(*node->info))
      result = py::reinterpret_steal<py::object>(
          PyUnicode_FromOrdinal(NodeU{node}.char_->value));
    else if(node->info == &True_Info || node->info == &False_Info)
      result = py::bool_(node->info == &True_Info);
    else if(node->info == &Unit_Info) result = py::none();
    else if(is_list(*node->info))
    {
      py::list items;
      std::string text;
      bool chars = false, first = true;
      while(true)
      {

        if(value->info == &Nil_Info) break;
        Cursor head = value[0].target;

        if(first) { chars = is_char(*head->info); first = false; }
        py::object item;
        tag = to_python(rts, C, head, item);
        if(tag < T_CTOR) return tag;
        if(chars) text += item.cast<std::string>();
        else items.append(item);
        value = value[1].target;
      }
      result = chars ? py::object(py::str(text)) : py::object(items);
    }
    else if(node->info == &Pair_Info)
    {
      py::tuple pair(2);
      for(int i=0; i<2; ++i)
      {
        py::object item;
        tag = to_python(rts, C, value[i].target, item);
        if(tag < T_CTOR) return tag;
        pair[i] = item;
      }
      result = pair;
    }
    else throw py::type_error("primitive argument is not a scalar, list or pair");
    return T_CTOR;
  }

  Node * from_python(py::handle value)
  {
    if(py::isinstance<Node>(value)) return value.cast<Node *>();
    if(value.is_none()) return unit();
    if(py::isinstance<py::bool_>(value)) return value.cast<bool>() ? true_() : false_();
    if(py::isinstance<py::int_>(value))
      return integer(py::str(value).cast<std::string>().c_str());
    if(py::isinstance<py::float_>(value)) return float_(value.cast<double>());
    if(py::isinstance<py::str>(value))
    {
      Node * result = nil();
      for(Py_ssize_t i=PyUnicode_GetLength(value.ptr()); i-- > 0;)
        result = Node::create(&Cons_Info, char_(PyUnicode_ReadChar(value.ptr(), i)), result);
      return result;
    }
    if(py::isinstance<py::list>(value))
    {
      auto values = py::reinterpret_borrow<py::list>(value);
      Node * result = nil();
      for(py::ssize_t i=values.size(); i-- > 0;)
        result = Node::create(&Cons_Info, from_python(values[i]), result);
      return result;
    }
    if(py::isinstance<py::tuple>(value) && py::len(value) == 2)
    {
      auto pair = py::reinterpret_borrow<py::tuple>(value);
      return Node::create(&Pair_Info, from_python(pair[0]), from_python(pair[1]));
    }
    throw py::type_error("primitive result is not a scalar, list, pair or None");
  }

  tag_type python_primitive_step(RuntimeState * rts, Configuration * C)
  {
    Cursor root = C->cursor();
    // Keep one path and extend it in place; copying a Variable per list
    // cell would copy every prefix of the list's path.
    struct Frame { Cursor cursor; index_type next, end; size_t path, guards; };
    std::vector<Frame> pending{{root, 0, root->info->arity, 0, 0}};
    Variable value;
    while(!pending.empty())
    {
      auto & frame = pending.back();
      if(frame.next == frame.end) { pending.pop_back(); continue; }
      value.realpath.resize(frame.path);
      value.guards.resize(frame.guards);
      auto child = frame.cursor[frame.next++];
      value.target = child.target;
      value.realpath.append(child.realpath.begin(), child.realpath.end());
      value.guards.append(child.guards.begin(), child.guards.end());
      auto tag = rts->hnf(C, &value);
      if(tag < T_CTOR) return tag;
      if(is_list(*value.target->info) || value.target->info == &Pair_Info)
        pending.push_back({value.target, 0, value.target->info->arity,
                           value.realpath.size(), value.guards.size()});
    }
    py::gil_scoped_acquire gil;
    auto primitive = static_cast<PythonPrimitive const *>(root->info->aux);
    std::string error;
    try
    {
      py::tuple args(root->info->arity);
      for(index_type i=0; i<root->info->arity; ++i)
      {
        py::object arg;
        auto tag = to_python(rts, C, root[i].target, arg);
        if(tag < T_CTOR) return tag;
        args[i] = arg;
      }
      py::object callable = primitive->callable; // retain across replacement
      py::object interp = py::cast(rts, reference).attr("interp");
      if(interp.is_none())
        throw py::value_error(
            "no interpreter owns this evaluation; primitives need one");
      py::object result = callable(interp, *args);
      fork_check();
      Node * node = from_python(result);
      root->forward_to(is_monadic(primitive->info) ? io(node) : node);
      return T_FWD;
    }
    catch(py::error_already_set & exc)
    {
      fork_check();
      if(exc.matches(PyExc_KeyboardInterrupt) || exc.matches(PyExc_SystemExit))
        throw;
      try
      {
        error = py::str(exc.type().attr("__name__")).cast<std::string>() +
            ": " + py::str(exc.value()).cast<std::string>();
      }
      catch(...)
      {
        error = "an exception of the primitive";
      }
      exc.restore();
      PyErr_Clear();
    }
    catch(ForkError const &) { throw; }
    catch(std::exception const & exc) { error = exc.what(); }
    error = "primitive " + primitive->qualified_name + ": " + error;
    if(is_monadic(primitive->info))
      C->set_error(Node::create(ioerror_info(rts, IO_ERROR),
          build_curry_string(error.c_str())), "i/o error: " + error, ErrorKind::io);
    else C->set_error(error);
    return E_ERROR;
  }

  // The Python hook of the trap step (set_trap_hook).  A pointer, never
  // destroyed: a py::object destroyed after the interpreter ended is an
  // error.
  // Both installation and invocation own the runtime heap gate. The
  // Python thread-state attachment below is not a mutual-exclusion lock.
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
      py::object hook = *g_trap_hook; // retain across a reentrant replacement
      py::object result = hook(py::cast(info, reference));
      fork_check();
      if(result.is_none())
        return {};
      return py::str(result).cast<std::string>();
    }
    catch(py::error_already_set & exc)
    {
      fork_check();
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
    catch(ForkError const &) { throw; }
    catch(std::exception const & exc)
    {
      return exc.what();
    }
  }
}

namespace curryrt { namespace python
{
  void register_module(pybind11::module_ mod)
  {
    py::register_local_exception_translator([](std::exception_ptr error) {
      try { if(error) std::rethrow_exception(error); }
      catch(stream_control const & control)
      {
        try { std::rethrow_exception(control.cause); }
        catch(py::error_already_set & exc) { exc.restore(); }
      }
    });
    mod.def("_test_handle_shutdown_race", &test_handle_shutdown_race, heap_access{});
    mod.def("_test_handle_mutex_held", &test_handle_mutex_held);
    mod.def("shutdown_handles", &shutdown_handles, heap_access{});
    mod.def("set_stream_hook", [](py::object callable) {
      auto retained = new py::object(std::move(callable));
      set_stream_hook([retained](int stream, std::string const & operation,
                                std::string const & text, long long value) {
        py::gil_scoped_acquire gil;
        try
        {
          auto result = (*retained)(stream, operation, text, value);
          fork_check();
          return result.cast<std::string>();
        }
        catch(py::error_already_set & exc)
        {
          if(exc.matches(PyExc_KeyboardInterrupt) || exc.matches(PyExc_SystemExit))
            throw stream_control{std::current_exception()};
          throw;
        }
      });
    }, heap_access{});
    mod.def("is_handle", &is_handle, heap_access{});
    mod.def("convert_value", &convert_value, heap_access{});
    mod.def("builtin_module_names", &Module::builtin_module_names, heap_access{});
    mod.def("registered_names", &Module::registered_names, heap_access{});
    mod.def("is_io_ref", &is_io_ref, heap_access{});
    mod.def("set_install_prefix", &set_install_prefix, heap_access{});
    mod.def("primitive_kind", [](InfoTable const * info) {
      return info->step == python_primitive_step ? "Python" : "C++";
    }, heap_access{});
    mod.def("register_primitive", [](std::string const & name, int arity,
                                   py::object callable, bool monadic) {
      if(arity < 0 || arity > 255) throw py::value_error("invalid primitive arity");
      if(!PyCallable_Check(callable.ptr())) throw py::type_error("expected a callable");
      auto dot = name.rfind('.');
      if(dot == std::string::npos || !dot || dot + 1 == name.size())
        throw py::value_error("a primitive needs a qualified name");
      auto existing = Module::builtin_symbol(name.substr(0, dot), name.substr(dot + 1));
      if(existing)
      {
        if(existing->step != python_primitive_step)
          throw py::value_error("primitive " + name + " is registered in C++");
        if(existing->arity != arity ||
            bool(is_monadic(*existing)) != monadic)
          throw py::value_error("primitive already registered with another shape: " + name);
        static_cast<PythonPrimitive const *>(existing->aux)->callable = callable;
        return;
      }
      if(Module::find(process_registry(), name.substr(0, dot)))
        throw py::value_error("new primitive; register before the import: " + name);
      // Kept for the process; Python objects must not die after finalization.
      auto primitive = new PythonPrimitive(name.substr(dot + 1), arity,
          callable, monadic, python_primitive_step);
      primitive->qualified_name = name;
      try { Module::register_primitive(name, &primitive->info); }
      catch(...) { delete primitive; throw; }
    }, py::arg("name"), py::arg("arity"), py::arg("callable"),
       py::arg("monadic")=false, heap_access{});
    mod.def("set_trap_hook"
      , [](py::object hook)
        {
          if(!g_trap_hook)
            g_trap_hook = new py::object();
          *g_trap_hook = hook;
          set_trap_hook(hook.is_none() ? nullptr : &call_trap_hook);
        }
      , py::arg("hook")
      , "Installs the hook of the trap step (curryrt/module.hpp): a callable "
        "of one info table that gives the table its code and returns None, "
        "or returns the reason it did not.  None removes the hook.", curryrt::python::heap_access{});
    mod.def("install_trap", &install_trap, py::arg("info")
      , "Gives a function table made at run time the trap step: a step that "
        "calls the hook and raises when the table still has no code.", curryrt::python::heap_access{});
    mod.def("is_trapped"
      , [](InfoTable const * info) { return is_trapped(info); }
      , py::arg("info")
      , "Whether the step of an info table is the trap step.", curryrt::python::heap_access{});
    mod.def("trap_owner", &owner_of, py::arg("info")
      , "The name of the loaded module that owns a table, or ''.", curryrt::python::heap_access{});
    py::class_<Module, std::shared_ptr<Module>>(mod, "Module")
      .def("create_infotable", &Module::create_infotable, reference, curryrt::python::heap_access{})
      .def("create_type", &Module::create_type, reference, curryrt::python::heap_access{})
      .def("get_infotable", &Module::get_infotable, reference, curryrt::python::heap_access{})
      .def("get_type", &Module::get_type, reference, curryrt::python::heap_access{})
      .def("bind_builtin_symbol", &Module::bind_builtin_symbol, reference, curryrt::python::heap_access{})
      .def("get_builtin_symbol", &Module::get_builtin_symbol, reference, curryrt::python::heap_access{})
      .def("get_builtin_type", &Module::get_builtin_type, reference, curryrt::python::heap_access{})
      .def_property_readonly("shared", &Module::shared, curryrt::python::heap_access{})
      .def("link", &Module::link, curryrt::python::heap_access{})
      .def("keep_tables", &Module::keep_tables
        , "Keeps the tables made at run time for the life of the process.", curryrt::python::heap_access{})
      .def("retire", [](Module & module, InterpreterState & state)
        {
          if(!module.shared()) module.retire();
          state.modules.storage->modules.erase(module.name);
        }
        , "Hands the tables made at run time to the kept store and clears "
          "the module, so a module of the same name made later takes them "
          "back without their steps (issue #114).", curryrt::python::heap_access{})

      .def_property_readonly("shlib", &Module::shlib
        , "The compiled object linked to the module, or None.", curryrt::python::heap_access{})
      .def_readonly("name", &Module::name, curryrt::python::heap_access{})
      .def_static("find_or_create", [](InterpreterState & state, std::string name,
          bool compiled, bool runtime_tables)
        {
          auto module = Module::find_or_create(
              compiled ? process_registry() : state.modules, name, runtime_tables && !compiled);
          if(compiled) state.modules.storage->modules[name] = module;
          return module;
        }, py::arg("state"), py::arg("name"), py::arg("compiled") = false,
        py::arg("runtime_tables") = false, curryrt::python::heap_access{})
      .def_static("getall", [](InterpreterState * state)
        { return Module::getall(state ? state->modules : process_registry()); }, py::arg("state") = nullptr, curryrt::python::heap_access{})
      ;
  }
}}
