'''Deep evaluations escalate from the caller's stack to the heap's worker.'''
import cytest # from ./lib; must be first
import curry, json, os, shutil, subprocess, tempfile, unittest

CHILD = '''
import cytest, curry, json
from curry.backends.generic.eval.evaluator import Evaluator
curry.reset(backend='cxx', interpret='off', **%(flags)r)
M = curry.import_('StackGuard')
def run(n):
  ev = Evaluator(cytest.raw.interp(), cytest.raw.expr(M.deep, n, typed=True))
  values = [cytest.raw.interp().topython(v) for v in ev.evaluate()]
  return values, ev.rts.steps_total
'''

class TestIssue153(cytest.TestCase):
  def adapter_test(self, text):
    compiler = curry.config.cxx_tool()
    if compiler is None or os.name == 'nt':
      self.skipTest('the adapter harness needs a POSIX C++ compiler')
    with tempfile.TemporaryDirectory() as directory:
      source = os.path.join(directory, 'adapter.cpp')
      with open(source, 'w') as stream:
        stream.write(text)
      root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
      program = os.path.join(directory, 'adapter')
      proc = subprocess.run([compiler, '-std=c++17', source, '-o', program,
          '-I' + os.path.join(root, 'src'), '-pthread', '-ldl'],
          capture_output=True, text=True, timeout=120)
      self.assertEqual(proc.returncode, 0, proc.stderr)
      proc = subprocess.run([program], capture_output=True, text=True, timeout=5)
      self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

  @cytest.posix_only('injects an allocation failure after pthread_create')
  def test_handle_allocation_cannot_orphan_started_thread(self):
    self.adapter_test(r'''
#include <pthread.h>
#include <atomic>
#include <cstdlib>
#include <new>
#include <iostream>
#include <thread>
static std::atomic<bool> fail_next{false}, finish{false}, entered{false};
static pthread_t launched;
void *operator new(std::size_t size)
{
  if(fail_next.exchange(false)) throw std::bad_alloc();
  if(void *p = std::malloc(size)) return p;
  throw std::bad_alloc();
}
void operator delete(void *p) noexcept { std::free(p); }
void operator delete(void *p, std::size_t) noexcept { std::free(p); }
static int launch(pthread_t *id, pthread_attr_t const *attr,
    void *(*entry)(void *), void *arg)
{
  int rc = pthread_create(id, attr, entry, arg);
  if(rc == 0) { launched = *id; fail_next = true; }
  return rc;
}
#define pthread_create launch
#include "curryrt/platform.cpp"
#undef pthread_create
static void *run(void *)
{
  entered = true;
  while(!finish) std::this_thread::yield();
  return nullptr;
}
int main()
{
  curryrt::platform::Thread thread;
  try { curryrt::platform::start(thread, 0, run, nullptr, nullptr); }
  catch(std::bad_alloc const &) {}
  fail_next = false;
  while(!entered) std::this_thread::yield();
  finish = true;
  bool const owned = thread.started && thread.handle;
  if(owned) curryrt::platform::join(thread);
  else pthread_join(launched, nullptr); // Reap the orphan even on the base.
  if(!owned)
  {
    std::cerr << "started worker has no owner after allocation failure\n";
    return 1;
  }
  return 0;
}
''')

  def test_windows_stack_request_cannot_narrow(self):
    # Exercise the actual Windows adapter body with a recording CRT stub;
    # no Windows thread or multi-gigabyte reservation is needed.
    from pathlib import Path
    text = (Path(__file__).resolve().parent.parent /
            'src/curryrt/platform.cpp').read_text()
    start = text.index('  bool start(')
    end = text.index('\n  void join(', start)
    self.adapter_test(r'''
#include "curryrt/platform.hpp"
#include <cerrno>
#include <cstring>
#include <cstdint>
#include <limits>
#include <memory>
#include <iostream>
static unsigned recorded = 0;
static int calls = 0;
struct Start { void *(*main)(void *); void *arg; };
static unsigned trampoline(void *) { return 0; }
static constexpr unsigned STACK_SIZE_PARAM_IS_A_RESERVATION = 0x10000;
static uintptr_t _beginthreadex(void *, unsigned size, unsigned (*)(void *),
    Start *boxed, unsigned, void *)
{
  ++calls;
  recorded = size;
  delete boxed;
  return 1;
}
namespace curryrt { namespace platform {
''' + text[start:end] + r'''
}}
int main()
{
  if(sizeof(size_t) <= sizeof(unsigned)) return 0;
  curryrt::platform::Thread thread;
  std::string error;
  size_t const request = size_t(1) << 32;
  bool const accepted = curryrt::platform::start(thread, request, nullptr, nullptr, &error);
  if(accepted || calls || thread.started)
  {
    std::cerr << "unrepresentable reservation accepted: " << request
              << " became " << recorded << '\n';
    return 1;
  }
  if(!curryrt::platform::start(thread, request / 2, nullptr, nullptr, &error)
      || calls != 1 || recorded != request / 2) return 2;
}
''')

  @unittest.skipUnless(os.name == 'nt', 'actual reservations run in the Windows workflow')
  def test_windows_unrepresentable_reservation_halves(self):
    lines = self.child('''
ev = Evaluator(cytest.raw.interp(), cytest.raw.expr(M.deep, 3000, typed=True))
assert [cytest.raw.interp().topython(v) for v in ev.evaluate()] == [3000]
assert ev.rts._escalated
print(ev.rts._worker_attempts)
''', stack_limit=65536, worker_stack=1 << 32)
    sizes = [int(size) for size in lines[0].split(', ')]
    self.assertEqual(sizes[:2], [1 << 32, 1 << 31])
    self.assertLess(sizes[-1], 1 << 32)

  @cytest.posix_only('pthread_create fault injection')
  def test_creation_exceptions_are_refused_reservations(self):
    '''Exercise both exception paths at the POSIX thread adapter boundary.'''
    compiler = curry.config.cxx_tool()
    if compiler is None:
      self.skipTest('a C++ compiler is required for the thread fault injector')
    tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    self.addCleanup(shutil.rmtree, tmpdir)
    source = os.path.join(tmpdir, 'refusal.cpp')
    with open(source, 'w') as stream:
      stream.write(r'''
#include <pthread.h>
#include <new>
#include <system_error>
#include <iostream>
static bool all_sizes = false;
static bool bad_alloc = false;
static int create_worker(pthread_t *thread, pthread_attr_t const *attr,
    void *(*entry)(void *), void *arg)
{
  size_t size = 0;
  pthread_attr_getstacksize(attr, &size);
  if(size >= (size_t(1) << 30) || all_sizes)
  {
    if(bad_alloc) throw std::bad_alloc();
    throw std::system_error(std::make_error_code(std::errc::resource_unavailable_try_again));
  }
  return pthread_create(thread, attr, entry, arg);
}
// Compile the platform layer and the adapter with a throwing creation
// function.  pthread_create itself returns an error code; C++ allocation and
// synchronization throw.  The layer makes the call (platform::start).
#define pthread_create create_worker
#include "curryrt/platform.cpp"
#undef pthread_create
#include "curryrt/evaluation.cpp"
int main(int argc, char **argv)
{
  bad_alloc = argv[1][0] == 'b';
  all_sizes = argv[2][0] == 'a';
  try
  {
    auto &w = curryrt::get_worker(size_t(1) << 30);
    std::cout << w.attempts << '\n';
    {
      std::lock_guard<std::mutex> lock(w.mutex);
      w.stop = true;
      w.cv.notify_all();
    }
    curryrt::platform::join(w.thread);
  }
  catch(curryrt::EvaluationError const &error)
  { std::cout << error.what() << '\n'; }
}
''')
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    library = os.path.join(tmpdir, 'refusal')
    proc = subprocess.run([compiler, '-std=c++17', source, '-o', library,
        '-I' + os.path.join(root, 'src'), '-L' + os.path.join(curry.config.prefix(), 'lib'),
        '-Wl,-rpath,' + os.path.join(curry.config.prefix(), 'lib'), '-lcurryrt', '-pthread'],
        capture_output=True, text=True, timeout=120)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    for kind, name in [('b', 'std::bad_alloc'), ('s', 'std::system_error')]:
      for all_sizes in (False, True):
        with self.subTest(kind=name, all_sizes=all_sizes):
          proc = subprocess.run([library, kind, 'all' if all_sizes else 'one'],
              capture_output=True, text=True, timeout=30)
          self.assertEqual(proc.returncode, 0, proc.stderr)
          if all_sizes:
            self.assertIn(name, proc.stdout)
            self.assertIn('67108864', proc.stdout)
          else:
            self.assertEqual(proc.stdout.strip(), '1073741824, 536870912')

  def child(self, code, **flags):
    proc = cytest.run_in_subprocess(
        CHILD % {'flags': flags} + code, 120, address_space=4 << 30)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    return proc.stdout.splitlines()

  @cytest.skipIfGcStress('a million live cells under a collection per step')
  def test_deep_lengths(self):
    for n in (100000, 1000000):
      with self.subTest(n=n):
        line, = self.child('print(json.dumps(run(%d)[0]))' % n)
        self.assertEqual(json.loads(line), [n])

  def test_disabled_worker_keeps_guard_diagnostic(self):
    lines = self.child('''
try:
  run(100000)
except curry.StackLimitError as error:
  print(error)
''', worker_stack=None)
    self.assertEqual(len(lines), 1)
    self.assertRegex(lines[0], r'^stack limit of \d+ bytes exceeded \(flag stack_limit\)')

  def test_tiny_reservation_names_attempt_and_floor(self):
    lines = self.child('''
try:
  run(10000)
except curry.StackLimitError as error:
  print(error)
''', stack_limit=65536, worker_stack=1)
    self.assertEqual(len(lines), 1)
    self.assertIn('worker_stack', lines[0])
    self.assertIn('attempted sizes in bytes: 1', lines[0])
    self.assertIn('67108864', lines[0])

  def test_escalation_keeps_values_and_step_counts(self):
    line, = self.child('''
plain = run(3000)
curry.reset(backend='cxx', interpret='off', stack_limit=65536)
M = curry.import_('StackGuard')
deep = run(3000)
print(json.dumps([plain, deep]))
''')
    plain, deep = json.loads(line)
    self.assertEqual(plain, deep)
    self.assertEqual(plain[0], [3000])


  @cytest.linux_only('RLIMIT_AS is not enforced on macOS, and the test reads /proc/self/statm')
  def test_refused_reservation_halves_to_a_usable_stack(self):
    # Leave less than 1 GiB beyond the current mappings: the first stack
    # cannot fit, but a smaller one can, even with a free-threaded Python's
    # larger initial address space.  Build the goal before imposing the cap.
    line, = self.child('''
import os, resource
ev = Evaluator(cytest.raw.interp(), cytest.raw.expr(M.deep, 3000, typed=True))
with open('/proc/self/statm') as stream:
  mapped = int(stream.read().split()[0]) * os.sysconf('SC_PAGE_SIZE')
limit = mapped + (768 << 20)
resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
values = [cytest.raw.interp().topython(v) for v in ev.evaluate()]
assert values == [3000], values
assert ev.rts._escalated
print(ev.rts._worker_attempts)
''', stack_limit=65536)
    sizes = [int(size) for size in line.split(', ')]
    self.assertGreater(len(sizes), 1, sizes)
    self.assertEqual(sizes[0], 1 << 30)
    for before, after in zip(sizes, sizes[1:]):
      self.assertEqual(after, max(before // 2, 64 << 20))
