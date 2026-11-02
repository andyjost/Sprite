'''
The child program of the compile expression and throughput CPU items.

Usage: python probe.py [EXPRESSION [TYPE]]
       python probe.py --throughput MODULE GOAL

Imports the curry package, imports the Prelude, compiles the expression of
the given Curry type with curry.parse, and evaluates it to its first value.
Prints one JSON object with the seconds of each step (import, prelude,
compile, first_value), the value, and the fields of curry.stats().  The
harness measures the process from the outside as well; see
suites.ExpressionItem.
'''

import json, sys, time

STEPS = ('import', 'prelude', 'compile', 'first_value')

def main(argv=None):
  argv = sys.argv[1:] if argv is None else argv
  if argv and argv[0] == '--throughput':
    return throughput(argv[1], argv[2])
  text = argv[0] if argv else '1+2'
  exprtype = argv[1] if len(argv) > 1 else 'Int'
  marks = [time.perf_counter()]
  import curry
  marks.append(time.perf_counter())
  curry.import_('Prelude')
  marks.append(time.perf_counter())
  expr = curry.parse('(%s) :: %s' % (text, exprtype))
  marks.append(time.perf_counter())
  value = next(iter(curry.eval(expr)))
  marks.append(time.perf_counter())
  stats = curry.stats()
  report = dict(zip(STEPS, [b - a for a, b in zip(marks, marks[1:])]))
  report['value'] = curry.show(value)
  report['stats'] = dict(stats)
  print(json.dumps(report))
  return 0

def throughput(module_name, goal_text):
  # Load and construct before timing, as sprite-exec does for a named goal.
  import curry
  from curry.tools.evaluation import evaluate
  module = curry.import_(module_name)
  goal = module.main if goal_text == 'main' else curry.parse(goal_text, imports=[module])
  wall, cpu = time.perf_counter(), time.process_time()
  status = evaluate(goal, action=lambda answer: None, quiet=True)
  cpu, wall = time.process_time() - cpu, time.perf_counter() - wall
  print(json.dumps(dict(eval_cpu=cpu, eval_wall=wall)))
  sys.stderr.write('%s\n' % curry.stats())
  return status or 0


if __name__ == '__main__':
  sys.exit(main())
