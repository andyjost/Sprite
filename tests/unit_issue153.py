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
// Compile the adapter with a throwing creation function.  pthread_create
// itself returns an error code; C++ allocation and synchronization throw.
#define pthread_create create_worker
#include "curryrt/evaluation.cpp"
#undef pthread_create
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
    pthread_join(w.thread, nullptr);
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
