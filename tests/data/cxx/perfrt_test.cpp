// Native checks driven by unit_cxx_perfrt.py.
#include "curryrt/unionfind.hpp"
#include "curryrt/platform.hpp"
#include <cstdio>
#include <cstdlib>
#include <thread>
#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#elif defined(__linux__) || defined(__APPLE__)
#include <pthread.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <unistd.h>
#endif
using namespace curryrt;
#define CHECK(c) do { if(!(c)) { std::printf("failed: %s at %d\n", #c, __LINE__); std::exit(1); } } while(0)

#if defined(__linux__) || defined(__APPLE__) || defined(_WIN32)
static char const * probe()
{
#if defined(_WIN32)
  ULONG_PTR low = 0, high = 0;
  GetCurrentThreadStackLimits(&low, &high);
  CHECK(low != 0 && high > low);
  return reinterpret_cast<char const *>(low);
#elif defined(__APPLE__)
  auto top = static_cast<char const *>(pthread_get_stackaddr_np(pthread_self()));
  auto size = pthread_get_stacksize_np(pthread_self());
  CHECK(top != nullptr && size != 0);
  return top - size;
#else
  pthread_attr_t attr;
  CHECK(pthread_getattr_np(pthread_self(), &attr) == 0);
  void * address = nullptr;
  size_t size = 0;
  CHECK(pthread_attr_getstack(&attr, &address, &size) == 0);
  pthread_attr_destroy(&attr);
  return static_cast<char const *>(address);
#endif
}
#endif

static void floor_tests()
{
  auto floor = platform::stack_floor_of_this_thread();
  CHECK(floor == platform::stack_floor_of_this_thread());
#if defined(__linux__) || defined(__APPLE__) || defined(_WIN32)
  CHECK(floor == probe());
#endif
  std::thread worker([floor] {
    auto own = platform::stack_floor_of_this_thread();
    CHECK(own == platform::stack_floor_of_this_thread());
#if defined(__linux__) || defined(__APPLE__) || defined(_WIN32)
    CHECK(own == probe());
    CHECK(own != floor);
#endif
#if defined(__linux__) || defined(__APPLE__)
    // Fork with the worker's TLS already warm, then compare independently.
    pid_t child = fork();
    CHECK(child >= 0);
    if(child == 0)
    {
      CHECK(platform::stack_floor_of_this_thread() == probe());
      _exit(0);
    }
    int status = 0;
    CHECK(waitpid(child, &status, 0) == child);
    CHECK(WIFEXITED(status) && WEXITSTATUS(status) == 0);
#endif
  });
  worker.join();
#if defined(__linux__)
  pid_t child = fork();
  CHECK(child >= 0);
  if(child == 0)
  {
    // Change the main thread's reservation so an inherited cached answer
    // cannot accidentally pass the independent probe comparison.
    struct rlimit limit;
    CHECK(getrlimit(RLIMIT_STACK, &limit) == 0);
    limit.rlim_cur = limit.rlim_cur == RLIM_INFINITY ? (2 << 20) : limit.rlim_cur / 2;
    CHECK(setrlimit(RLIMIT_STACK, &limit) == 0);
    auto expected = probe();
    CHECK(expected != floor);
    CHECK(platform::stack_floor_of_this_thread() == expected);
    _exit(0);
  }
  int status = 0;
  CHECK(waitpid(child, &status, 0) == child);
  CHECK(WIFEXITED(status) && WEXITSTATUS(status) == 0);
  CHECK(platform::stack_floor_of_this_thread() == floor);
#endif
}

static void union_tests()
{
  // Replayed equalities historically increase representative weights.
  // Keep that tie-breaking behavior while omitting duplicate log pairs.
  UnionFind weighted;
  weighted.unite(1, 2);
  weighted.unite(1, 2);
  weighted.unite(3, 4);
  weighted.unite(3, 5);
  CHECK(weighted.united.size() == 6);
  weighted.unite(3, 1);
  CHECK(weighted.root(3) == 1);

  UnionFind parent;
  xid_type const high = xid_type(1) << 40;
  CHECK(parent.root(high) == high);
  CHECK(parent.data.empty());
  parent.unite(high, high + 1);
  CHECK(parent.find(high, high + 1));
  CHECK(!parent.find(high, high + 2));
  CHECK(parent.data.size() == 2);
  auto log_size = parent.united.size();
  for(int i = 0; i < 100; ++i)
  {
    parent.unite(high, high + 1);
    parent.unite(high + 1, high);
    parent.unite(high, high);
  }
  CHECK(parent.united.size() == log_size);
  CHECK(parent.data.at(parent.root(high)).size == 0);
  UnionFind child(parent);
  CHECK(child.united.capacity() >= child.united.size() + 2);
  child.unite(high + 1, high + 2);
  CHECK(child.find(high, high + 2));
  CHECK(!parent.find(high, high + 2));
  CHECK(parent.united.size() == log_size);
  parent.unite(1, 2);
  CHECK(!child.find(1, 2));
  for(xid_type i = 3; i < 100; ++i) parent.unite(i - 1, i);
  for(xid_type i = 1; i < 100; ++i) CHECK(parent.find(1, i));
  CHECK(!parent.find(1, high));
  for(auto id: parent.united) CHECK(parent.root(id) == parent.root(parent.root(id)));
}

int main()
{
  floor_tests();
  union_tests();
  std::puts("ok");
}
