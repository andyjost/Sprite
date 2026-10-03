'''
The child program of the expression item of the compile suite.

Usage: python probe.py [EXPRESSION [TYPE]]

Imports the curry package, imports the Prelude, compiles the expression of
the given Curry type with curry.compile, and evaluates it to its first value.
Prints one JSON object with the seconds of each step (import, prelude,
compile, first_value), the value, and the fields of curry.stats().  The
harness measures the process from the outside as well; see
suites.ExpressionItem.
'''

import json, sys, time

STEPS = ('import', 'prelude', 'compile', 'first_value')

def main(argv=None):
  argv = sys.argv[1:] if argv is None else argv
  text = argv[0] if argv else '1+2'
  exprtype = argv[1] if len(argv) > 1 else 'Int'
  marks = [time.perf_counter()]
  import curry
  marks.append(time.perf_counter())
  curry.import_('Prelude')
  marks.append(time.perf_counter())
  expr = curry.compile(text, mode='expr', exprtype=exprtype)
  marks.append(time.perf_counter())
  value = next(iter(curry.eval(expr)))
  marks.append(time.perf_counter())
  stats = curry.stats()
  report = dict(zip(STEPS, [b - a for a, b in zip(marks, marks[1:])]))
  report['value'] = curry.show_value(value)
  report['stats'] = dict(stats)
  print(json.dumps(report))
  return 0

if __name__ == '__main__':
  sys.exit(main())
