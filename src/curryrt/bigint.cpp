#include "curryrt/bigint.hpp"
#include "curryrt/graph/node.hpp"
#include "tommath.h"
#include <cstdlib>
#include <limits>
#include <memory>
#include <stdexcept>
#include <vector>

extern "C"
{
  curryrt::InfoTable const BigInt_Info {
      curryrt::T_CTOR, 1, sizeof(curryrt::BigIntNode)
    , curryrt::F_INT_TYPE | curryrt::F_STATIC_OBJECT
    , "Int", "x", nullptr, &Int_Type
    };
}

namespace curryrt
{
  static size_t live = 0;
  static void checked(mp_err error)
  {
    if(error == MP_MEM) throw std::bad_alloc();
    if(error != MP_OKAY) throw std::runtime_error(mp_error_to_string(error));
  }
  struct BigIntData
  {
    mp_int number;
    size_t refs = 0;
    BigIntData() { checked(mp_init(&number)); ++live; }
    ~BigIntData() { mp_clear(&number); --live; }
    BigIntData(BigIntData const &) = delete;
  };
  static BigIntData * data(Node * n)
    { return reinterpret_cast<BigIntNode *>(n)->value; }
  void bigint_acquire(Node * n) { ++data(n)->refs; }
  void bigint_release(Node * n)
  {
    BigIntData * p = data(n);
    if(--p->refs == 0) delete p;
  }
  size_t bigint_live_count() { return live; }

  // Always demote, including -2^63, before a node escapes this factory.
  static Node * box(std::unique_ptr<BigIntData> p, bool literal=false)
  {
    mp_int const * a = &p->number;
    int const bits = mp_count_bits(a);
    if(bits < 64 || (bits == 64 && mp_isneg(a)
        && mp_get_mag_u64(a) == (uint64_t(1) << 63)))
    {
      unboxed_int_type const value = mp_get_i64(a);
      return literal ? literal_node(&Int_Info, Arg(value)) : int_(value);
    }
    Arg payload(p.get());
    // The array overload registers owning nodes. The variadic overload is
    // the allocation-only fast path used by generated function nodes.
    Node * n = literal ? literal_node(&BigInt_Info, payload)
                      : Node::create(&BigInt_Info, &payload);
    // Node::create acquired the heap node's reference.  Literal storage
    // lives with its module for the process lifetime.
    if(literal) ++p->refs;
    p.release();
    return n;
  }
  Node * integer(char const * digits, bool literal)
  {
    auto p = std::make_unique<BigIntData>();
    checked(mp_read_radix(&p->number, digits, 10));
    return box(std::move(p), literal);
  }
  Node * integer(double integral)
  {
    auto p = std::make_unique<BigIntData>();
    checked(mp_set_double(&p->number, integral));
    return box(std::move(p));
  }
  static mp_int const * number(Node * n, BigIntData & scratch)
  {
    if(is_bigint(n)) return &data(n)->number;
    mp_set_i64(&scratch.number, NodeU{n}.int_->value);
    return &scratch.number;
  }
  Node * integer_binary(char op, Node * x, Node * y)
  {
    BigIntData sx, sy;
    auto a = number(x, sx), b = number(y, sy);
    auto p = std::make_unique<BigIntData>();
    switch(op)
    {
      case '+': checked(mp_add(a, b, &p->number)); break;
      case '-': checked(mp_sub(a, b, &p->number)); break;
      case '*': checked(mp_mul(a, b, &p->number)); break;
      default:
      {
        BigIntData q, r;
        checked(mp_div(a, b, &q.number, &r.number));
        // LibTomMath divides toward zero.  div/mod round toward -infinity.
        if((op == 'd' || op == 'm') && !mp_iszero(&r.number)
            && mp_isneg(a) != mp_isneg(b))
        {
          checked(mp_decr(&q.number));
          checked(mp_add(&r.number, b, &r.number));
        }
        checked(mp_copy(op == 'd' || op == 'q' ? &q.number : &r.number, &p->number));
      }
    }
    return box(std::move(p));
  }
  int integer_compare(Node * x, Node * y)
  {
    if(!is_bigint(x) && !is_bigint(y))
    {
      auto a = NodeU{x}.int_->value, b = NodeU{y}.int_->value;
      return (a > b) - (a < b);
    }
    BigIntData sx, sy;
    return mp_cmp(number(x, sx), number(y, sy));
  }
  double integer_float(Node * n)
  {
    if(!is_bigint(n)) return double(NodeU{n}.int_->value);
    auto const * a = &data(n)->number;
    if(mp_count_bits(a) > std::numeric_limits<double>::max_exponent)
      return mp_isneg(a) ? -std::numeric_limits<double>::infinity()
                         : std::numeric_limits<double>::infinity();
    // Converting one limb at a time can double-round halfway cases, e.g.
    // 2^120 + 2^67 + 1 with 60-bit limbs. strtod rounds the exact decimal
    // value once, as the inline integer conversion does.
    return std::strtod(integer_string(n).c_str(), nullptr);
  }
  std::string integer_string(Node * n)
  {
    if(!is_bigint(n)) return std::to_string(NodeU{n}.int_->value);
    int size;
    checked(mp_radix_size(&data(n)->number, 10, &size));
    std::vector<char> text(size);
    checked(mp_to_radix(&data(n)->number, text.data(), text.size(), nullptr, 10));
    return text.data();
  }
  uint64_t integer_hash(Node * n)
  {
    if(!is_bigint(n)) return uint64_t(NodeU{n}.int_->value);
    // Stable by value, independent of allocation or the arithmetic route.
    uint64_t hash = 14695981039346656037ULL;
    for(unsigned char ch: integer_string(n))
      hash = (hash ^ ch) * 1099511628211ULL;
    return hash;
  }
}
