#pragma once
#include "curryrt/export.hpp"
#include "curryrt/builtins.hpp"
#include <cstdint>
#include <string>

extern "C" { extern CURRYRT_DATA curryrt::InfoTable const BigInt_Info; }

namespace curryrt
{
  // Immutable, reference-counted libtommath storage, outside the node heap.
  // The public runtime headers deliberately do not expose libtommath.
  struct BigIntData;
  struct BigIntNode : Head { BigIntData * value; };
  inline bool is_bigint(Node const * node)
    { return reinterpret_cast<Head const *>(node)->info == &BigInt_Info; }
  void bigint_acquire(Node *);
  void bigint_release(Node *);
  void gc_register_bigint(Node *);
  size_t bigint_live_count();
  Node * integer(char const * digits, bool literal=false);
  Node * integer(double integral);
  Node * integer_binary(char op, Node *, Node *);
  int integer_compare(Node *, Node *);
  double integer_float(Node *);
  std::string integer_string(Node *);
  uint64_t integer_hash(Node *);
}
