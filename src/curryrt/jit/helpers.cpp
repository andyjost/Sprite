// The helper surface of the JIT (backends/cxx/llvmjit.py).
//
// The operations of the opcodes of the interpreter (curryrt/icurry.hpp) as
// C functions over the inline code of the runtime headers.  clang compiles
// this file to LLVM bitcode (lib/curryrt-helpers.bc, the CMake target
// jit_helpers); the JIT links the bitcode into the module it makes from the
// bytecode of a function, and the optimizer inlines every helper
// (always_inline) into the step, so the step holds the same inline code as
// a function g++ compiled from the generated C++: the allocation fast path,
// the reads of the successors, the rewrite of the redex.  What the headers
// declare out of line (RuntimeState::hnf, node_refill, the indexer) stays a
// call into the runtime library, as it is in compiled code.
//
// This file is not part of the runtime library.  Its functions take and
// return the plain types of the ABI: a Cursor or a Variable is storage the
// step allocates on its stack, sized by jit_sizeof_cursor and
// jit_sizeof_variable, and lives between jit_var_init and jit_var_destroy.
#include "curryrt/bigint.hpp"
#include "curryrt/builtins.hpp"
#include "curryrt/graph/node.hpp"
#include "curryrt/icurry.hpp"
#include "curryrt/state/rts.hpp"
#include <cstdint>
#include <new>

#define JIT_HELPER extern "C" __attribute__((always_inline))

using namespace curryrt;

// The sizes of the storage the step allocates.
JIT_HELPER uint32_t jit_sizeof_cursor() { return sizeof(Cursor); }
JIT_HELPER uint32_t jit_sizeof_variable() { return sizeof(Variable); }

// The redex: Cursor _0 = C->cursor().
JIT_HELPER void jit_cursor(Configuration * C, Cursor * out)
  { new (out) Cursor(C->cursor()); }
JIT_HELPER Node * jit_redex(Cursor const * c) { return **c; }

// LOAD_ROOT_SUCC, LOAD_VAR_SUCC, PUSH_SUCC: a pass-through argument.
JIT_HELPER Node * jit_root_succ(Cursor const * c, uint32_t i)
  { return (**c)->successor_node((index_type) i); }
JIT_HELPER Node * jit_var_succ(Variable const * v, uint32_t i)
  { return v->successor_node((index_type) i); }

// The frame of variables.
JIT_HELPER void jit_var_init(Variable * v) { new (v) Variable(); }
JIT_HELPER void jit_var_destroy(Variable * v) { v->~Variable(); }
// COPY_VAR.
JIT_HELPER void jit_var_copy(Variable * dst, Variable const * src)
  { *dst = *src; }
// BIND_ROOT and BIND_VAR, one entry of the path at a time (the indexer).
JIT_HELPER void jit_bind_root(Cursor const * c, Variable * v, uint32_t i)
  { *v = Variable(**c, (index_type) i); }
JIT_HELPER void jit_bind_var(Variable * v, Variable const * w, uint32_t i)
  { *v = (*w)[(index_type) i]; }

// FREE_REG.
JIT_HELPER Node * jit_freshvar(RuntimeState * rts) { return rts->freshvar(); }
// PUSH_VAR and PUSH_PATH: the value a variable denotes.
JIT_HELPER Node * jit_rvalue(Variable const * v) { return v->rvalue(); }

// MAKE, MAKE_PARTIAL, MAKE_STRING.
JIT_HELPER Node * jit_make(InfoTable const * info, Node * const * args, uint32_t n)
  { return icurry_make_node(info, args, n); }
JIT_HELPER Node * jit_make_partial(InfoTable const * info, Node * const * args, uint32_t n)
  { return Node::create_partial(info, (Arg const *) args, (size_t) n); }
JIT_HELPER Node * jit_cstring(char const * text) { return cstring(text); }

// STORE_VAR: the variable targets a cell of the frame, with no path and no
// guard, as the generated code does for a variable assigned a new node.
JIT_HELPER void jit_store_var(Variable * v, Node ** cell, Node * value)
{
  *cell = value;
  *v = Variable();
  v->target = Cursor(*cell);
}
// SET_SUCC: the patch of a recursive let.
JIT_HELPER void jit_set_succ(Variable const * v, uint32_t i, Node * value)
  { v->set_successor((index_type) i, value); }

// EXEMPT, RET_REF, RET_NODE, RET_STRING.
JIT_HELPER tag_type jit_exempt(Cursor const * c) { return (**c)->make_failure(); }
JIT_HELPER tag_type jit_ret_ref(Cursor const * c, Node * value)
  { return (**c)->forward_or_copy(value); }
JIT_HELPER tag_type jit_ret_node(
    Cursor const * c, InfoTable const * info, Node * const * args, uint32_t n
  )
{
  Node * const redex = **c;
  // The result is written into the redex when it fits the block
  // (Node::rewrite); a pinned constructor is never written into a redex.
  if(!is_pinned(*info) && info->alloc_size <= redex->info->alloc_size)
  {
    size_t const old_bytes = redex->info->alloc_size;
    RawNodeMemory mem{redex};
    *mem.info++ = info;
    for(uint32_t i=0; i<n; ++i)
      *mem.boxed++ = args[i];
    gc_pad_slack(redex, old_bytes, info->alloc_size);
    return info->tag;
  }
  redex->forward_to(icurry_make_node(info, args, n));
  return T_FWD;
}
JIT_HELPER tag_type jit_ret_string(Cursor const * c, char const * text)
  { return (**c)->rewrite(&_biString_Info, text); }

// CASE_CONS and CASE_LIT: the head normal form of a variable, with a data
// type or a value set, then the node it denotes and the value of a literal.
JIT_HELPER tag_type jit_hnf(
    RuntimeState * rts, Configuration * C, Variable * v, void const * typeinfo
  )
  { return rts->hnf(C, v, typeinfo); }
JIT_HELPER Node * jit_var_target(Variable const * v) { return *v->target; }
JIT_HELPER int32_t jit_is_bigint(Node const * node) { return is_bigint(node); }
JIT_HELPER int64_t jit_int_value(Node * node) { return NodeU{node}.int_->value; }
JIT_HELPER uint32_t jit_char_value(Node * node)
  { return (uint32_t) NodeU{node}.char_->value; }
JIT_HELPER double jit_float_value(Node * node) { return NodeU{node}.float_->value; }
JIT_HELPER int32_t jit_integer_compare(Node * a, Node * b)
  { return integer_compare(a, b); }
