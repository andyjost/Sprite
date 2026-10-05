#pragma once
#include <cstdint>
#include <deque>
#include <memory>
#include <string>
#include <vector>
#include "cyrt/fwd.hpp"
#include "cyrt/graph/infotable.hpp"

// The ICurry interpreter of the runtime.
//
// A function of a module compiled by g++ has a step function of its own.  An
// interpreted function has the step function icurry_step, shared by every
// interpreted function, and a Bytecode in the aux field of its info table.
// The bytecode is a compact form of the ICurry body of the function, written
// by the emitter of the C++ backend (backends/cxx/bytecode.py) and attached
// with icurry_attach when the module loads.  The interpreter makes the same
// calls into the runtime as the generated code makes (Variable, hnf,
// Node::create, the in-place rewrite of the redex), so the two run the same
// scheduler on the same nodes, and a program may mix compiled and
// interpreted modules.
//
// The machine.  A step runs on one frame: the registers, plain Node *
// values for the arguments a step only passes on (the rule of
// backends/cxx/passthrough.py); the variables, Variable objects for the
// arguments a case scrutinizes and for the bases of paths; and an operand
// stack, on which the arguments of a node under construction are collected.
// The code is a sequence of 32-bit units: an opcode and its operands.  The
// operands name a register (r), a variable (v, w), a constant of the function
// (k), a successor index (i), a count (n), and the entries of a path (p...).
// ROOT_VAR as a variable names the redex.  The constants are pointers: an
// info table, a data type, a value set, a node that lives as long as the
// process (a literal or a partial application without arguments; see
// builtins.hpp), or the text of a string literal.
//
// Every block of ICurry ends with a return, an exempt, or a case, so a case
// needs no join: its branch table holds the position of each branch, and a
// branch runs to its own end.
namespace cyrt
{
  enum Opcode : uint32_t
  {
    // r i       regs[r] = the node in slot i of the redex
    OP_LOAD_ROOT_SUCC
    // r v i     regs[r] = the node in slot i of the target of vars[v]
  , OP_LOAD_VAR_SUCC
    // v n p...  vars[v] = redex[p0]...[pn-1] (the indexer)
  , OP_BIND_ROOT
    // v w n p...  vars[v] = vars[w][p0]...[pn-1]
  , OP_BIND_VAR
    // r s       regs[r] = regs[s]
  , OP_COPY_REG
    // v w       vars[v] = vars[w]
  , OP_COPY_VAR
    // r         regs[r] = a fresh free variable
  , OP_FREE_REG
    // r         push regs[r]
  , OP_PUSH_REG
    // v         push the value vars[v] denotes (rvalue)
  , OP_PUSH_VAR
    //           push the redex
  , OP_PUSH_ROOT
    // k         push the node consts[k]
  , OP_PUSH_CONST
    // s i       push the node in slot i of vars[s], or of the redex (ROOT_VAR)
  , OP_PUSH_SUCC
    // s n p...  push the value of vars[s][p0]...[pn-1] (ROOT_VAR: the redex)
  , OP_PUSH_PATH
    // k n       pop n arguments; push a node of info table consts[k]
  , OP_MAKE
    // k n       pop n arguments; push a partial application of consts[k]
  , OP_MAKE_PARTIAL
    // k         push a string node for the text consts[k]
  , OP_MAKE_STRING
    // r         regs[r] = pop
  , OP_STORE_REG
    // v         vars[v] = a variable of the node popped
  , OP_STORE_VAR
    // v n p...  (vars[v][p0]...[pn-2]).set_successor(pn-1, pop)
  , OP_SET_SUCC
    //           the step fails
  , OP_EXEMPT
    //           the result is the node popped (forward_or_copy)
  , OP_RET_REF
    // k n       pop n arguments; the result is a node of consts[k], written
    //           into the redex when it fits (Node::rewrite)
  , OP_RET_NODE
    // k         the result is the string literal consts[k]
  , OP_RET_STRING
    // v k ntab tab...  head-normalize vars[v] with the data type consts[k]
    //           and continue at tab[tag]; a tag without a branch, and a
    //           status below T_CTOR, is returned
  , OP_CASE_CONS
    // v k kind n (lo hi pc)...  head-normalize vars[v] with the value set
    //           consts[k]; continue at the branch whose 64-bit value (lo,
    //           hi) is the value of the node; no branch: the step fails
  , OP_CASE_LIT
  , NUM_OPCODES
  };

  // The redex as the base of a path, where a variable is named.
  static constexpr uint32_t ROOT_VAR = 0xffffffffu;
  // A constructor without a branch in a CASE_CONS table.
  static constexpr uint32_t NO_BRANCH = 0xffffffffu;

  // The values of a literal case, as hnf narrows a free variable with them
  // (see RuntimeState::replace_freevar).
  struct ValueSetData
  {
    std::vector<Arg> args;
    ValueSet set;
  };

  struct Bytecode
  {
    std::vector<uint32_t>     code;
    std::vector<void const *> consts;
    uint32_t                  nregs = 0;
    uint32_t                  nvars = 0;
    uint32_t                  nstack = 0;
    // The storage behind the constants that are not nodes or tables.
    std::deque<std::string>   strings;
    std::deque<ValueSetData>  valuesets;
  };

  // The step function of every interpreted function.
  tag_type icurry_step(RuntimeState *, Configuration *);

  // Makes ``info`` an interpreted function: its step becomes icurry_step and
  // its bytecode ``code``, which lives as long as the process.  ``info`` must
  // be a function table made at run time (Module::create_infotable) without a
  // step.  Throws std::invalid_argument otherwise.
  void icurry_attach(InfoTable *, std::unique_ptr<Bytecode> code);

  // The bytecode of an interpreted function, or null.
  Bytecode const * icurry_bytecode(InfoTable const *);

  // The number of interpreted functions in the process.
  size_t icurry_num_functions();

  // The name of an opcode, for the disassembler of the tests.
  char const * icurry_opcode_name(uint32_t);
}
