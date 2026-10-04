// Checks SmallVec, the inline storage of Variable (see cyrt/smallvec.hpp).
// unit_cxx_variable.py compiles this program against the installed runtime
// and runs it.  It prints the first failed check and exits with status 1;
// it prints "ok" and exits with status 0 when every check passes.
#include "cyrt/graph/cursor.hpp"
#include "cyrt/smallvec.hpp"
#include <cstdio>
#include <cstdlib>
#include <initializer_list>
#include <utility>

using namespace cyrt;

#define CHECK(cond) \
    do { if(!(cond)) { std::printf("failed: %s (line %d)\n", #cond, __LINE__); std::exit(1); } } while(0)

using Vec = SmallVec<index_type, 4>;

static bool holds(Vec const & vec, std::initializer_list<index_type> values)
{
  if(vec.size() != values.size())
    return false;
  size_t i = 0;
  for(index_type value: values)
    if(vec[i++] != value)
      return false;
  return true;
}

static Vec make(size_t count, index_type first=0)
{
  Vec vec;
  for(size_t i=0; i<count; ++i)
    vec.push_back(index_type(first + i));
  return vec;
}

// An alias the compiler cannot see through, for the self-assignment checks.
__attribute__((noipa)) static Vec & opaque(Vec & vec) { return vec; }

// The layout that the step functions were compiled against.
static_assert(sizeof(RealPath) == 24, "RealPath has 8 inline entries");
static_assert(sizeof(GuardList) == 24, "GuardList has 2 inline entries");
static_assert(sizeof(Variable) == 64, "Variable is as large as before");
static_assert(RealPath::inline_capacity == 8, "");
static_assert(GuardList::inline_capacity == 2, "");

int main()
{
  // Empty.
  {
    Vec vec;
    CHECK(vec.empty());
    CHECK(vec.size() == 0);
    CHECK(vec.is_inline());
    CHECK(vec.capacity() == 4);
    CHECK(vec.begin() == vec.end());
  }

  // Within the inline room.
  {
    Vec vec = make(4, 10);
    CHECK(holds(vec, {10, 11, 12, 13}));
    CHECK(vec.is_inline());
    CHECK(vec.back() == 13);
    vec.pop_back();
    CHECK(holds(vec, {10, 11, 12}));
    CHECK(vec.is_inline());
  }

  // Growth to the heap, and growth again.
  {
    Vec vec = make(5);
    CHECK(holds(vec, {0, 1, 2, 3, 4}));
    CHECK(!vec.is_inline());
    CHECK(vec.capacity() >= 5);
    size_t const capacity = vec.capacity();
    for(index_type i=5; i<100; ++i)
      vec.push_back(i);
    CHECK(vec.size() == 100);
    CHECK(vec.capacity() > capacity);
    for(size_t i=0; i<100; ++i)
      CHECK(vec[i] == i);
    vec.clear();
    CHECK(vec.empty());
    CHECK(!vec.is_inline()); // clear keeps the block
    vec.push_back(7);
    CHECK(holds(vec, {7}));
  }

  // Copies: inline to inline, heap to inline, inline to heap, heap to heap.
  {
    Vec small = make(3);
    Vec large = make(9);
    Vec a(small);
    CHECK(holds(a, {0, 1, 2}));
    CHECK(a.is_inline());
    Vec b(large);
    CHECK(b == large);
    CHECK(!b.is_inline());
    CHECK(b.data() != large.data()); // its own block
    Vec c = make(2, 50);
    c = large;
    CHECK(c == large);
    CHECK(!c.is_inline());
    Vec d = make(6, 50);
    index_type const * block = d.data();
    d = small;
    CHECK(holds(d, {0, 1, 2}));
    CHECK(d.data() == block); // the block is kept
    Vec e = make(6, 50);
    e = large;
    CHECK(e == large);
    // The sources are unchanged.
    CHECK(holds(small, {0, 1, 2}));
    CHECK(large.size() == 9 && large.back() == 8);
  }

  // Moves: an inline source is copied, a heap source gives up its block.
  {
    Vec small = make(2, 20);
    Vec a(std::move(small));
    CHECK(holds(a, {20, 21}));
    CHECK(small.empty());
    CHECK(small.is_inline());
    Vec large = make(7);
    index_type const * block = large.data();
    Vec b(std::move(large));
    CHECK(b.size() == 7 && b.data() == block);
    CHECK(large.empty());
    CHECK(large.is_inline());
    large.push_back(1); // the source is usable again
    CHECK(holds(large, {1}));
    Vec c = make(8, 30);
    c = std::move(b);
    CHECK(c.size() == 7 && c.data() == block);
    CHECK(b.empty() && b.is_inline());
    Vec d = make(1);
    d = std::move(a);
    CHECK(holds(d, {20, 21}));
    CHECK(a.empty());
  }

  // Self-assignment of a heap-backed object keeps its block.  (back comes
  // before size in the checks: after a check of the size, g++ 13 warns about
  // the subscript on the inline room of a path it cannot rule out.)
  {
    Vec vec = make(6);
    index_type const * block = vec.data();
    vec = opaque(vec);
    CHECK(vec.back() == 5);
    CHECK(vec.data() == block && vec.size() == 6);
    vec = std::move(opaque(vec));
    CHECK(vec.back() == 5);
    CHECK(vec.data() == block && vec.size() == 6);
  }

  // append, with and without growth.
  {
    Vec vec = make(2);
    Vec more = make(3, 10);
    vec.append(more.begin(), more.end());
    CHECK(holds(vec, {0, 1, 10, 11, 12}));
    CHECK(!vec.is_inline());
    Vec none;
    vec.append(none.begin(), none.end());
    CHECK(vec.size() == 5);
    Vec two = make(2);
    two.append(none.begin(), none.end());
    CHECK(two.is_inline() && two.size() == 2);
  }

  // resize: growth value-initializes, shrinking keeps the block.
  {
    Vec vec = make(2);
    vec.resize(3);
    CHECK(holds(vec, {0, 1, 0}) && vec.is_inline());
    vec.resize(6);
    CHECK(holds(vec, {0, 1, 0, 0, 0, 0}) && !vec.is_inline());
    index_type const * block = vec.data();
    vec.resize(1);
    CHECK(holds(vec, {0}) && vec.data() == block);
    vec.resize(0);
    CHECK(vec.empty() && vec.data() == block);
  }

  // Equality compares the values, not the storage.
  {
    Vec a = make(3);
    Vec b = make(9);
    for(int i=0; i<6; ++i)
      b.pop_back();
    CHECK(a.is_inline() && !b.is_inline());
    CHECK(a == b);
    b.push_back(3);
    CHECK(a != b);
  }

  // Pointers as values, as GuardList holds them.
  {
    int x, y, z;
    SmallVec<int *, 2> ptrs;
    ptrs.push_back(&x);
    ptrs.push_back(&y);
    CHECK(ptrs.is_inline());
    ptrs.push_back(&z);
    CHECK(!ptrs.is_inline());
    CHECK(ptrs[0] == &x && ptrs[1] == &y && ptrs[2] == &z);
    int count = 0;
    for(int * p: ptrs)
      count += (p != nullptr);
    CHECK(count == 3);
  }

  std::printf("ok\n");
  return 0;
}
