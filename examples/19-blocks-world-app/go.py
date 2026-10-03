'''
Blocks World as a command-line application.

Finds a shortest plan that carries blocks between three stacks.  Curry states
what a legal move is and which traces of at most n moves reach the goal.
Python parses the worlds, asks Curry for a plan under the bounds 0, 1, 2, ...
and takes the first plan it gets.  The first bound with a plan gives a
shortest plan.  Python then draws it.

Usage: python go.py START GOAL [--max-moves N]
       python go.py --serve PORT [--max-moves N]

A world is three stacks separated by slashes.  Write each stack from its top
block to its bottom block.  So ABC// puts A on B on C on the first stack and
leaves the other two stacks empty.
'''
import argparse
import os
import sys
import curry

# Find Blocks.curry next to this file, whatever the working directory is.
curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import Blocks

STACKS = 3
BLOCKS = 'ABCDE'   # the constructors of the Curry type Block
MAX_MOVES = 12     # the default bound at which the search gives up
PER_ROW = 6        # worlds drawn side by side before a new row starts

def parse_world(text):
  '''Checks the notation of a world and returns its stacks as strings.'''
  stacks = text.split('/')
  if len(stacks) != STACKS:
    raise ValueError('%s: a world has %d stacks separated by slashes' % (text, STACKS))
  letters = ''.join(stacks)
  for letter in letters:
    if letter not in BLOCKS:
      raise ValueError('%s: the blocks are %s' % (text, ', '.join(BLOCKS)))
  if len(set(letters)) != len(letters):
    raise ValueError('%s: a block appears twice' % text)
  return stacks

def to_curry(stacks):
  '''Builds the Curry World for the stacks: a tuple of three lists of blocks.

  Each block is the expression of a constructor, curry.expr(Blocks.A).  A
  Python list whose first element is a Curry symbol would be an application,
  not a list, so the stacks hold expressions rather than symbols.
  '''
  return tuple([curry.expr(getattr(Blocks, letter)) for letter in stack]
               for stack in stacks)

def first_plan(start, goal, bound):
  '''The first plan of at most bound moves, or None when there is none.

  One Curry call is a generator of plans.  next() takes the first one and
  stops the search.  A bound with no plan yields zero values, which is not an
  error.  The converter turns the trace into a Python list of tuples of lists.
  The blocks stay Curry constructors, and str() of one gives its name.
  '''
  values = curry.eval(Blocks.plan, bound, to_curry(start), to_curry(goal),
                      converter='topython')
  return next(values, None)

def show_world(world):
  '''The notation of a world: the stacks top to bottom, separated by slashes.'''
  return '/'.join(''.join(str(block) for block in stack) for stack in world)

def describe_move(before, after):
  '''"A to stack 3": the block that moved and the stack it moved to.'''
  for i in range(STACKS):
    if len(after[i]) > len(before[i]):
      return '%s to stack %d' % (after[i][0], i + 1)

def draw(trace):
  '''Draws the worlds of a trace side by side, each as three stacks.

  The rows run from the top block down to the base.  Every picture has one
  row per block, so the pictures of one trace line up.
  '''
  height = sum(len(stack) for stack in trace[0])
  width = max(len('step %d' % (len(trace) - 1)), 2 * STACKS - 1)
  base = ' '.join(str(i + 1) for i in range(STACKS))
  lines = []
  for first in range(0, len(trace), PER_ROW):
    group = trace[first:first + PER_ROW]
    rows = [['step %d' % (first + k) for k in range(len(group))]]
    for row in range(height):
      rows.append([' '.join(symbol(stack, row, height) for stack in world)
                   for world in group])
    rows.append([base] * len(group))
    for cells in rows:
      lines.append('   '.join(cell.ljust(width) for cell in cells).rstrip())
  return lines

def symbol(stack, row, height):
  '''The block of a stack in one row of the picture, or a dot above it.'''
  index = row - (height - len(stack))
  return str(stack[index]) if index >= 0 else '.'

def moves(n):
  '''"1 move" or "5 moves".'''
  return '%d move%s' % (n, '' if n == 1 else 's')

def solve(start_text, goal_text, max_moves, report):
  '''Finds a shortest plan by iterative deepening and reports it.

  Calls report with each line of the report as soon as it is known.  Returns
  the trace, or None when no plan of at most max_moves moves exists.
  '''
  start = parse_world(start_text)
  goal = parse_world(goal_text)
  if sorted(''.join(start)) != sorted(''.join(goal)):
    raise ValueError('the start and the goal must have the same blocks')
  report('start %s  goal %s' % ('/'.join(start), '/'.join(goal)))
  for bound in range(max_moves + 1):
    trace = first_plan(start, goal, bound)
    if trace is not None:
      break
    report('bound %d: no plan' % bound)
  else:
    report('no plan of at most %s' % moves(max_moves))
    return None
  report('shortest plan: %s' % moves(len(trace) - 1))
  for k in range(1, len(trace)):
    report('%3d. %-13s %s' % (k, describe_move(trace[k - 1], trace[k]),
                              show_world(trace[k])))
  for line in draw(trace):
    report(line)
  return trace

PAGE = '''<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Blocks World</title></head>
<body>
<h1>Blocks World</h1>
<form method="get">
  start <input name="start" value="%(start)s" size="12">
  goal <input name="goal" value="%(goal)s" size="12">
  <input type="submit" value="plan">
</form>
<p>Write each stack from its top block to its bottom block.  Separate the
three stacks with slashes.  For example: start ABC// and goal //ABC.</p>
<pre>%(report)s</pre>
</body></html>
'''

def serve(port, max_moves):
  '''Serves a web form on the local host.  Each request calls solve().'''
  import html
  import http.server
  import urllib.parse

  class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
      query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
      start = query.get('start', [''])[0]
      goal = query.get('goal', [''])[0]
      lines = []
      if start or goal:
        try:
          solve(start, goal, max_moves, lines.append)
        except ValueError as e:
          lines.append('error: %s' % e)
      page = PAGE % dict(start=html.escape(start), goal=html.escape(goal),
                         report=html.escape('\n'.join(lines)))
      data = page.encode('utf-8')
      self.send_response(200)
      self.send_header('Content-Type', 'text/html; charset=utf-8')
      self.send_header('Content-Length', str(len(data)))
      self.end_headers()
      self.wfile.write(data)

  server = http.server.HTTPServer(('127.0.0.1', port), Handler)
  print('serving on http://127.0.0.1:%d/  (press Ctrl-C to stop)' % server.server_port)
  sys.stdout.flush()
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    pass

def main(argv=None):
  parser = argparse.ArgumentParser(
      description='Finds a shortest plan that carries blocks between three stacks.')
  parser.add_argument('start', nargs='?', help='the start world, for example ABC//')
  parser.add_argument('goal', nargs='?', help='the goal world, for example //ABC')
  parser.add_argument('--max-moves', type=int, default=MAX_MOVES, metavar='N',
                      help='give up after the bound of N moves (default: %(default)s)')
  parser.add_argument('--serve', type=int, metavar='PORT',
                      help='serve a web form on this port of the local host instead')
  args = parser.parse_args(argv)
  if args.serve is not None:
    serve(args.serve, args.max_moves)
    return 0
  if args.start is None or args.goal is None:
    parser.error('give a start world and a goal world, or --serve PORT')
  try:
    trace = solve(args.start, args.goal, args.max_moves,
                  lambda line: print(line, flush=True))
  except ValueError as e:
    print('error: %s' % e, file=sys.stderr)
    return 2
  return 0 if trace is not None else 1

if __name__ == '__main__':
  sys.exit(main())
