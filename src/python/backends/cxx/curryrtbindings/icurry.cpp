#include "curryrt/bigint.hpp"
#include "heap.hpp"
#include <cstdint>
#include <memory>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>
#include "curryrt/builtins.hpp"
#include "curryrt/graph/infotable.hpp"
#include "curryrt/graph/node.hpp"
#include "curryrt/icurry.hpp"
#include "pybind11/pybind11.h"
#include "pybind11/stl.h"

namespace py = pybind11;

// The bindings of the ICurry interpreter (curryrt/icurry.hpp).  The emitter of
// the C++ backend (backends/cxx/bytecode.py) hands the code and the constants
// of a function to icurry_attach.  A constant is an InfoTable, a DataType, or
// a tuple that names a value the runtime makes here:
//
//     ('I', value)            a node of an Int literal
//     ('C', codepoint)        a node of a Char literal
//     ('F', value)            a node of a Float literal
//     ('S', text)             the text of a string literal
//     ('P', info, missing)    a partial application without arguments
//     ('V', kind, values)     the value set of a literal case
//
// A literal node lives as long as the process (literal_node), one per value
// in the process: the table nodes serve the small values, and a map here
// serves the others.
namespace curryrt { namespace python
{
  [[noreturn]] void raise_int_range_error(py::handle value); // graph.cpp
}}

namespace
{
  using namespace curryrt;

  // Decode an inline literal or an entry of a word-only case table. Big
  // literals take the canonical digit factory before reaching this helper.
  unboxed_int_type int_literal_value(py::handle value)
  {
    static_assert(sizeof(unboxed_int_type) == sizeof(long long), "assumes a 64-bit long long");
    int overflow = 0;
    long long const result = PyLong_AsLongLongAndOverflow(value.ptr(), &overflow);
    if(overflow)
      curryrt::python::raise_int_range_error(value);
    if(result == -1 && PyErr_Occurred())
      throw py::error_already_set();
    return result;
  }

  // Literal-map lookup, allocation and insertion run under icurry_attach
  // heap_access. They do not rely on Python's GIL.
  std::unordered_map<unboxed_int_type, Node *> g_int_nodes;
  std::unordered_map<unboxed_char_type, Node *> g_char_nodes;
  std::unordered_map<uint64_t, Node *> g_float_nodes;

  Node * int_literal(unboxed_int_type value)
  {
    if(SMALL_INT_MIN <= value && value <= SMALL_INT_MAX)
      return int_(value);
    Node *& node = g_int_nodes[value];
    if(!node)
      node = literal_node(&Int_Info, Arg(value));
    return node;
  }

  Node * char_literal(unboxed_char_type value)
  {
    if(value <= SMALL_CHAR_MAX)
      return char_(value);
    Node *& node = g_char_nodes[value];
    if(!node)
      node = literal_node(&Char_Info, Arg(value));
    return node;
  }

  Node * float_literal(unboxed_float_type value)
  {
    // Keyed by the bits: -0.0 and 0.0 are two literals, as the generated
    // code spells them.
    uint64_t bits;
    static_assert(sizeof(bits) == sizeof(value), "");
    std::memcpy(&bits, &value, sizeof(bits));
    Node *& node = g_float_nodes[bits];
    if(!node)
      node = literal_node(&Float_Info, Arg(value));
    return node;
  }

  unboxed_char_type code_point(py::handle obj)
  {
    if(py::isinstance<py::str>(obj))
    {
      if(PyUnicode_GetLength(obj.ptr()) != 1)
        throw py::value_error("expected a string of length one");
      return (unboxed_char_type) PyUnicode_ReadChar(obj.ptr(), 0);
    }
    return (unboxed_char_type) obj.cast<uint32_t>();
  }

  void const * make_constant(Bytecode & bc, py::handle item)
  {
    if(py::isinstance<InfoTable>(item))
      return item.cast<InfoTable const *>();
    if(py::isinstance<DataType>(item))
      return item.cast<DataType const *>();
    if(!py::isinstance<py::tuple>(item))
      throw py::type_error(
          "a constant is an InfoTable, a DataType, or a tuple; got "
          + std::string(py::str(py::type::of(item)))
        );
    py::tuple tup = item.cast<py::tuple>();
    if(tup.size() < 2)
      throw py::value_error("a constant tuple needs a kind and a value");
    std::string const kind = tup[0].cast<std::string>();
    if(kind == "I")
    {
      int overflow = 0;
      PyLong_AsLongAndOverflow(tup[1].ptr(), &overflow);
      if(overflow)
        return integer(py::module_::import("curry.utility.strings").attr("int_text")(tup[1]).cast<std::string>().c_str(), true);
      return int_literal(int_literal_value(tup[1]));
    }
    if(kind == "C")
      return char_literal(code_point(tup[1]));
    if(kind == "F")
      return float_literal(tup[1].cast<unboxed_float_type>());
    if(kind == "S")
    {
      bc.strings.push_back(tup[1].cast<std::string>());
      return bc.strings.back().c_str();
    }
    if(kind == "P")
    {
      if(tup.size() != 3)
        throw py::value_error("a partial constant is ('P', info, missing)");
      InfoTable const * head = tup[1].cast<InfoTable const *>();
      return partial_node(head, tup[2].cast<unboxed_int_type>());
    }
    if(kind == "V")
    {
      if(tup.size() != 3)
        throw py::value_error("a value set is ('V', kind, values)");
      std::string const vkind = tup[1].cast<std::string>();
      if(vkind.size() != 1
          || std::string("icfp").find(vkind) == std::string::npos)
        throw py::value_error("the kind of a value set is 'i', 'c', or 'f'");
      py::sequence values = tup[2].cast<py::sequence>();
      bc.valuesets.emplace_back();
      ValueSetData & data = bc.valuesets.back();
      for(py::handle value: values)
      {
        switch(vkind[0])
        {
          case 'p':
            data.args.push_back(Arg((Node *) make_constant(bc, py::make_tuple("I", value))));
            break;
          case 'i':
            data.args.push_back(Arg(int_literal_value(value)));
            break;
          case 'c':
            data.args.push_back(Arg(code_point(value)));
            break;
          case 'f':
            data.args.push_back(Arg(value.cast<unboxed_float_type>()));
            break;
        }
      }
      data.set.args = data.args.data();
      data.set.size = (index_type) data.args.size();
      data.set.kind = vkind[0];
      return &data.set;
    }
    throw py::value_error("unknown constant kind " + kind);
  }

  void icurry_attach_(
      InfoTable * info, std::vector<uint32_t> code, py::sequence consts
    , uint32_t nregs, uint32_t nvars, uint32_t nstack
    )
  {
    if(!info)
      throw py::value_error("cannot attach bytecode to a null info table");
    auto bc = std::make_unique<Bytecode>();
    bc->code = std::move(code);
    bc->nregs = nregs;
    bc->nvars = nvars;
    bc->nstack = nstack;
    for(py::handle item: consts)
      bc->consts.push_back(make_constant(*bc, item));
    try
    {
      icurry_attach(info, std::move(bc));
    }
    catch(std::invalid_argument const & e)
    {
      throw py::value_error(e.what());
    }
  }

  py::object icurry_bytecode_(InfoTable const * info)
  {
    Bytecode const * bc = icurry_bytecode(info);
    if(!bc)
      return py::none();
    py::dict d;
    d["code"] = bc->code;
    d["nregs"] = bc->nregs;
    d["nvars"] = bc->nvars;
    d["nstack"] = bc->nstack;
    d["nconsts"] = bc->consts.size();
    // The constants as addresses, for the JIT (backends/cxx/llvmjit.py):
    // an info table, a data type, a value set, a node, or a text, each of
    // which lives as long as the process.
    std::vector<std::uintptr_t> consts;
    for(void const * k: bc->consts)
      consts.push_back(reinterpret_cast<std::uintptr_t>(k));
    d["consts"] = consts;
    return std::move(d);
  }

  void icurry_set_step_(InfoTable * info, std::uintptr_t address)
  {
    try
    {
      icurry_set_step(info, reinterpret_cast<stepfunc_type>(address));
    }
    catch(std::invalid_argument const & e)
    {
      throw py::value_error(e.what());
    }
  }

  py::dict jit_sizes_()
  {
    py::dict d;
    d["cursor"] = sizeof(Cursor);
    d["variable"] = sizeof(Variable);
    d["tag_bits"] = 8 * sizeof(tag_type);
    d["pointer_bits"] = 8 * sizeof(void *);
    return d;
  }

  std::vector<std::string> icurry_opcodes_()
  {
    std::vector<std::string> names;
    for(uint32_t i=0; i<NUM_OPCODES; ++i)
      names.push_back(icurry_opcode_name(i));
    return names;
  }
}

namespace curryrt { namespace python
{
  void register_icurry(pybind11::module_ mod)
  {
    mod.def("icurry_attach", &icurry_attach_
      , py::arg("info"), py::arg("code"), py::arg("consts"), py::arg("nregs")
      , py::arg("nvars"), py::arg("nstack")
      , "Makes a function table made at run time an interpreted function: "
        "attaches the bytecode and the constants of its body.", curryrt::python::heap_access{});
    mod.def("icurry_set_step", &icurry_set_step_
      , "Gives an interpreted function the step at an address: the code a JIT "
        "made from its bytecode.  The function must be interpreted at the "
        "call.", curryrt::python::heap_access{});
    mod.def("jit_sizes", &jit_sizes_
      , "The sizes the JIT needs: the bytes of a Cursor and of a Variable, "
        "the bits of a tag and of a pointer.");
    mod.def("icurry_bytecode", &icurry_bytecode_
      , "The bytecode of an interpreted function as a dict (code, nregs, "
        "nvars, nstack, nconsts), or None for any other info table.", curryrt::python::heap_access{});
    mod.def("icurry_is_jit", &icurry_is_jit
      , "Whether the step of an info table is code the JIT made from its "
        "bytecode (icurry_set_step).", curryrt::python::heap_access{});
    mod.def("icurry_is_interpreted"
      , [](InfoTable const * info)
          { return icurry_bytecode(info) != nullptr && !icurry_is_jit(info); }
      , "Whether the step of an info table is the ICurry interpreter.", curryrt::python::heap_access{});
    mod.def("icurry_opcodes", &icurry_opcodes_
      , "The names of the opcodes of the interpreter, in numeric order.", curryrt::python::heap_access{});
    mod.def("icurry_count", &icurry_num_functions
      , "The number of interpreted functions in the process.", curryrt::python::heap_access{});
    mod.attr("ROOT_VAR") = (uint32_t) ROOT_VAR;
    mod.attr("NO_BRANCH") = (uint32_t) NO_BRANCH;
  }
}}
