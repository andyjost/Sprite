'''
Tests for the inline storage of Variable in the C++ runtime
(cyrt/smallvec.hpp, cyrt/graph/indexing.hxx).  Before this, every argument
access in a step built a Variable with two heap-backed vectors, so a step
made more heap calls for bookkeeping than for nodes.
'''
import cytest # from ./lib; must be first
from curry import config
import curry, os, re, shutil, subprocess, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))

# Call targets that a step function must not have: the allocators.
ALLOCATORS = re.compile(r'^(_Znwm|_Znam|_ZdlPv|_ZdaPv|malloc|calloc|realloc|free)$|^_ZdlPvm$')

# The indexer and rvalue of the former Variable, which were out of line in
# the runtime library.  Both are inline now.
OUT_OF_LINE = {
    '_ZN4cyrt8VariableC1EPNS_4NodeEtb'
  , '_ZN4cyrt8VariableC2EPNS_4NodeEtb'
  , '_ZNK4cyrt8Variable6rvalueEv'
  }

def step_function_calls(sofile):
  '''
  Maps each step function of a compiled module (a symbol CyF..., with its
  .cold part) to the set of symbols its code calls.  Reads the disassembly
  of objdump; a call line ends in the name of its target, as in
  ``call *0x4512(%rip) # 8f10 <_ZdlPvm@CXXABI_1.3.9>``.
  '''
  proc = subprocess.run(
      ['objdump', '-d', '--no-show-raw-insn', sofile]
    , capture_output=True, text=True, check=True
    )
  calls = {}
  current = None
  for line in proc.stdout.splitlines():
    match = re.match(r'^[0-9a-f]+ <([^>]+)>:$', line)
    if match:
      name = match.group(1)
      current = name if name.startswith('CyF') else None
      if current is not None:
        calls.setdefault(current, set())
      continue
    if current is None:
      continue
    match = re.search(r'\bcall\w*\s.*<([^>@]+)', line)
    if match:
      calls[current].add(match.group(1))
  return calls

@unittest.skipIf(config.cxx_tool() is None, 'no C++ compiler is installed')
class TestSmallVec(cytest.TestCase):
  '''
  SmallVec, the sequence with inline room that Variable keeps its path and
  its guards in.  The checks are a C++ program, data/cxx/smallvec_test.cpp,
  compiled against the installed runtime.
  '''
  TIMEOUT = 120

  def test_program(self):
    source = os.path.join(HERE, 'data', 'cxx', 'smallvec_test.cpp')
    libdir = config.installed_path('lib')
    tmpdir = tempfile.mkdtemp(prefix='sprite-smallvec-')
    try:
      exe = os.path.join(tmpdir, 'smallvec_test')
      cmd = [
          config.cxx_tool(), '-std=c++17', '-O2', '-Wall'
        , '-I%s' % config.installed_path('include')
        , source, '-o', exe
        , '-L%s' % libdir, '-lcyrt', '-Wl,-rpath,%s' % libdir
        ]
      proc = subprocess.run(cmd, capture_output=True, text=True)
      self.assertEqual(proc.returncode, 0, proc.stderr)
      self.assertEqual(proc.stderr, '', 'the compiler warned')
      proc = subprocess.run(
          ['timeout', str(self.TIMEOUT), exe], capture_output=True, text=True
        )
      self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
      self.assertEqual(proc.stdout, 'ok\n')
    finally:
      shutil.rmtree(tmpdir, ignore_errors=True)

@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'these tests drive the C++ backend'
  )
@unittest.skipIf(shutil.which('objdump') is None, 'objdump is not installed')
class TestStepFunctions(cytest.TestCase):
  '''
  The step functions of two benchmark programs make no heap call for an
  argument access: no allocator appears among their call targets, and the
  indexer is inline.  Before this, the step of fibgen called operator delete
  18 times and the out-of-line constructor of Variable three times.
  '''
  BENCHMARKS = os.path.join(HERE, 'data', 'curry', 'benchmarks')

  def sofile(self, name):
    '''Compiles a benchmark module, if needed, and returns its object.'''
    curry.import_(name, currypath=[self.BENCHMARKS] + curry.path)
    path = os.path.join(
        self.BENCHMARKS, '.curry', config.intermediate_subdir(), name + '.so'
      )
    self.assertTrue(os.path.exists(path), path)
    return path

  def test_no_allocator_in_steps(self):
    for name in 'Fib', 'Tak1':
      calls = step_function_calls(self.sofile(name))
      steps = [f for f in calls if not f.endswith('.cold')]
      self.assertGreaterEqual(len(steps), 4, name)
      for function, targets in sorted(calls.items()):
        bad = sorted(
            t for t in targets if ALLOCATORS.match(t) or t in OUT_OF_LINE
          )
        self.assertEqual(bad, [], '%s: %s calls %s' % (name, function, bad))

class TestPatterns(cytest.TestCase):
  '''
  Pattern matches that read their arguments through Variable: a path of two
  entries per step, forward nodes in the slots, set guards, and three nested
  set functions, whose innermost match carries more guards than the inline
  room of a Variable.  The programs are in data/curry/CxxVariable.curry.  The
  values are the same on both backends.
  '''
  def values(self, goal):
    return list(curry.eval(goal, converter='topython'))

  def test_deep_patterns(self):
    M = curry.import_('CxxVariable')
    self.assertEqual(self.values(M.deep), [7])
    self.assertEqual(self.values(M.literal), [9])
    self.assertEqual(self.values(M.shared), [(1, 2)])

  def test_set_functions(self):
    M = curry.import_('CxxVariable')
    self.assertEqual(self.values(M.setDeep), [[7]])
    self.assertEqual(sorted(self.values(M.setChoice)), [[3], [5]])
    self.assertEqual(self.values(M.setInner), [[4, 14]])

  def test_nested_set_functions(self):
    M = curry.import_('CxxVariable')
    self.assertEqual(self.values(M.nested), [[[[7]]]])
