'''
The child program of the overloads item on the backend clang: the overload
resolution of clang itself, timed with -ftime-trace.

Usage: python clangprobe.py [N] [--keep DIR]

The program writes two translation units with the overload set of the
workload of overloads.py and a variable template ``call<A, B>``, whose
requires-expression calls the overload set on two parameters of the types
A and B: one unit with one instantiation per call of the N distinct calls,
and one without the calls.  The requirement is dependent, so an ambiguous
call and a call without a viable function make the requires-expression
false and are not errors; a requirement that is not dependent and fails
makes the program ill-formed ([expr.prim.req.general]), and clang reports
it.  It compiles both units with ``clang++ -std=c++20 -fsyntax-only
-ftime-trace`` and reads the duration of the event "Frontend" of each
trace.  The difference, divided by N, is the cost of one call: process
start and the parse of the declarations are the same in both units and
cancel; the instantiation of the requires-expression of a call stays
inside the number.  The program prints one JSON
object: ``solve`` (the difference in seconds), ``per_call``, the two
frontend seconds, the compiler and its version.  Without clang++ on PATH it
prints the object with ``error`` set and exits with status 3; the harness
skips the item before it gets there.
'''

import json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
LIBDIR = os.path.dirname(os.path.dirname(HERE))
if LIBDIR not in sys.path:
  sys.path.insert(0, LIBDIR)

from benchmarks.apps import cxxoverload, overloads

MISSING_STATUS = 3
# The event of the trace whose duration is the time of the front end.
EVENT = 'Frontend'


def spelling(t):
  '''The type ``t`` of the workload as a C++ template argument.'''
  if t == ('fund', 'NullptrT'):
    return 'decltype(nullptr)'
  return cxxoverload.show_cxx(t)


def unit(workload):
  '''
  The translation unit of the workload: the classes, the overload set, the
  variable template ``call``, whose requires-expression calls the overload
  set on two parameters of dependent types, and one instantiation of it
  per call.  A requirement that is dependent and fails makes the
  requires-expression false; one that is not dependent and fails is an
  error, so the arguments are the parameters of the requires-expression,
  not variables of the unit.
  '''
  names = sorted(set(name for name, _ in overloads.CANDIDATES))
  if len(names) != 1:
    raise ValueError('the overload set has one name, not %r' % (names,))
  lines = ['struct Base {};', 'struct Derived : Base {};']
  for name, params in overloads.CANDIDATES:
    lines.append('void %s(%s);' % (
        name, ', '.join(cxxoverload.show_cxx(p) for p in params)
      ))
  lines.append(
      'template<class A, class B> constexpr bool call = '
      'requires (A a, B b) { %s(a, b); };' % names[0]
    )
  for i, args in enumerate(workload):
    lines.append('constexpr bool c%d = call<%s>;' % (
        i, ', '.join(spelling(a) for a in args)
      ))
  return '\n'.join(lines) + '\n'


def frontend_seconds(trace):
  '''The duration of the event EVENT of a time trace, in seconds.'''
  for event in trace.get('traceEvents', []):
    if event.get('name') == EVENT and 'dur' in event:
      return event['dur'] / 1e6
  raise ValueError('no event %r in the trace' % EVENT)


def compile_unit(clang, directory, name, text):
  '''Compiles ``text`` with -fsyntax-only and returns its frontend seconds.'''
  source = os.path.join(directory, name + '.cpp')
  trace = os.path.join(directory, name + '.json')
  with open(source, 'w') as stream:
    stream.write(text)
  cmd = [
      clang, '-std=c++20', '-fsyntax-only', '-ftime-trace=' + trace, source
    ]
  proc = subprocess.run(cmd, capture_output=True, text=True)
  if proc.returncode != 0:
    raise RuntimeError('%s failed: %s' % (' '.join(cmd), proc.stderr.strip()))
  with open(trace) as stream:
    return frontend_seconds(json.load(stream))


def main(argv=None):
  argv = list(sys.argv[1:] if argv is None else argv)
  keep = None
  if '--keep' in argv:
    i = argv.index('--keep')
    keep = argv[i + 1]
    del argv[i:i + 2]
  n = int(argv[0]) if argv else overloads.DEFAULT_CALLS
  clang = shutil.which('clang++')
  report = {'side': 'clang', 'calls': n, 'compiler': clang}
  if clang is None:
    report['error'] = 'clang++ is not on PATH'
    print(json.dumps(report))
    return MISSING_STATUS
  version = subprocess.run(
      [clang, '--version'], capture_output=True, text=True
    ).stdout.strip().splitlines()
  report['version'] = version[0] if version else None
  workload = overloads.calls(n)
  directory = keep or tempfile.mkdtemp(prefix='clangprobe-')
  try:
    with_calls = compile_unit(clang, directory, 'calls', unit(workload))
    without = compile_unit(clang, directory, 'baseline', unit([]))
  finally:
    if keep is None:
      shutil.rmtree(directory, ignore_errors=True)
  report.update({
      'frontend_with_calls': with_calls, 'frontend_without': without
    , 'solve': with_calls - without, 'per_call': (with_calls - without) / n
    })
  print(json.dumps(report))
  return 0


if __name__ == '__main__':
  sys.exit(main())
