'''
A build system: the decisions of make in Curry, the work of make in Python.

Python writes a small C project into a temporary directory, scans the
includes, reads the stamps of the files, and runs the recipes in a thread
pool.  Curry decides: which rule builds a target, what a target reads, what is
stale, what to build and in which order, what can run now, what a change
touches, and which targets two rules claim.

Usage: python go.py [--jobs N] [--trace]
       python go.py --serve PORT [--jobs N]
'''
import argparse
import concurrent.futures
import html
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import curry

# Find Build.curry next to this file, whatever the working directory is.
curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import Build

# The toy project: four sources, two headers, a library of two objects, and a
# program.  shape.h reads vec.h, so a change of vec.h reaches every object.
FILES = {
    'vec.h': '''\
#ifndef VEC_H
#define VEC_H
struct vec { double x, y; };
double vec_cross(struct vec a, struct vec b);
#endif
''',
    'shape.h': '''\
#ifndef SHAPE_H
#define SHAPE_H
#include "vec.h"
double triangle_area(struct vec a, struct vec b, struct vec c);
#endif
''',
    'vec.c': '''\
#include "vec.h"
double vec_cross(struct vec a, struct vec b) { return a.x * b.y - a.y * b.x; }
''',
    'shape.c': '''\
#include "shape.h"
double triangle_area(struct vec a, struct vec b, struct vec c)
{
  struct vec ab = { b.x - a.x, b.y - a.y };
  struct vec ac = { c.x - a.x, c.y - a.y };
  double cross = vec_cross(ab, ac);
  return (cross < 0 ? -cross : cross) / 2;
}
''',
    'report.c': '''\
#include <stdio.h>
#include "vec.h"
void report(const char *label, struct vec v)
{
  printf("%s = (%g, %g)\\n", label, v.x, v.y);
}
''',
    'main.c': '''\
#include <stdio.h>
#include "shape.h"
void report(const char *label, struct vec v);
int main(void)
{
  struct vec a = { 0, 0 }, b = { 4, 0 }, c = { 0, 3 };
  report("c", c);
  printf("area = %g\\n", triangle_area(a, b, c));
  return 0;
}
''',
  }
LIBRARY = ('libgeom.a', ['vec.o', 'shape.o'])
PROGRAM = ('demo', ['main.o', 'report.o'])

# A second rule for one target, for the lint: the same target as the pattern
# rule %.o: %.c, with another recipe.
EXTRA_RULE = (
    'main.o', ['main.c'], ['cc', '-c', '-O2', '-o', 'main.o', 'main.c']
  )

# A rule that closes a cycle: the program writes a header that its own
# objects include.  The plan has no value then.
CYCLE_RULE = ('shape.h', ['demo'], ['./demo', '--emit-header', 'shape.h'])

# The include scan: the quoted includes of a file.
INCLUDE = re.compile(r'^\s*#\s*include\s*"([^"]+)"', re.MULTILINE)

JOBS = 4  # the default width of the thread pool

def ask(goal, *args):
  '''The one value of a deterministic goal, as Python data.  Every question
  of Build has a value for a well-formed project, except the plan on a
  cycle, which show_plan reads itself.'''
  values = curry.eval(goal, *args, converter='topython')
  try:
    return next(values)
  except StopIteration:
    raise ValueError('%s has no value' % goal.fullname) from None

def answers(goal, *args):
  '''Every value of a goal, sorted.  Curry promises no order.'''
  return sorted(curry.eval(goal, *args, converter='topython'))

class World:
  '''The files of the project in one directory, and what Python knows about
  them: their text, their includes, and their stamps.  Curry sees the stamps
  as a table and never touches a file.'''

  def __init__(self, root):
    self.root = root
    for name, text in FILES.items():
      with open(self.path(name), 'w') as stream:
        stream.write(text)

  def path(self, name):
    return os.path.join(self.root, name)

  def touch(self, name):
    '''Gives a file the modification time of now, and waits for the clock
    when now is not newer than every other file.  A file system with a
    coarse clock gives the same result after a pause of one tick.'''
    path = self.path(name)
    newest = max(
        stamp for other, stamp in self.table(os.listdir(self.root))
            if other != name
      )
    while True:
      os.utime(path)
      if os.stat(path).st_mtime_ns > newest:
        return
      time.sleep(0.01)

  def includes(self):
    '''(file, headers) for each source and header, by the regular
    expression.'''
    table = []
    for name in sorted(FILES):
      with open(self.path(name)) as stream:
        table.append((name, INCLUDE.findall(stream.read())))
    return table

  def table(self, names):
    '''The stamps of the files that exist: the modification time in
    nanoseconds.  A missing file has no entry.'''
    table = []
    for name in names:
      try:
        table.append((name, os.stat(self.path(name)).st_mtime_ns))
      except FileNotFoundError:
        pass
    return table

def project(world, explicit=()):
  '''The Curry description of the project.  Every name is a Python str, which
  curry.expr converts to a String, the type the constructor expects.'''
  sources = [name for name in FILES if name.endswith('.c')]
  return curry.expr(
      Build.Project, sources, LIBRARY, PROGRAM, world.includes()
    , list(explicit)
    )

class Runner:
  '''Runs the recipes.  The word cc stands for the C compiler of the
  environment, CC or cc.  Without a compiler and ar on the PATH every recipe
  runs as a stand-in that writes a placeholder file, so the example runs on a
  machine without a compiler.'''

  def __init__(self, world):
    self.world = world
    self.cc = os.environ.get('CC') or 'cc'
    self.real = all(shutil.which(tool) for tool in (self.cc, 'ar'))
    if not self.real:
      print('note: no C compiler on the PATH; the recipes write placeholder '
            'files', file=sys.stderr)

  def run(self, target, inputs, words):
    '''Runs one recipe in the project directory and returns its status.'''
    if not self.real:
      with open(self.world.path(target), 'w') as stream:
        stream.write(
            'placeholder for %s from %s\n' % (target, ' '.join(inputs))
          )
      return 0
    command = [self.cc if words[0] == 'cc' else words[0]] + words[1:]
    proc = subprocess.run(
        command, cwd=self.world.root, capture_output=True, text=True
      )
    if proc.returncode:
      sys.stderr.write(proc.stderr)
    return proc.returncode

class Builder:
  '''The build loop.  Curry names the targets that can run now; the thread
  pool runs their recipes; after each completion the loop asks again.  Python
  holds no dependency and no order.  The table it hands to Curry omits the
  targets whose recipes run or failed: a compiler creates its output before
  it finishes, and a target that is missing to Curry is stale, so its
  dependents are not ready.'''

  def __init__(self, world, runner, jobs, trace):
    self.world, self.runner, self.jobs, self.trace = world, runner, jobs, trace

  def names(self, proj):
    '''Every file the table may hold: the sources, the headers, the targets.'''
    return list(dict.fromkeys(list(FILES) + ask(Build.targets, proj)))

  def table(self, proj, omit=()):
    '''The table Curry sees: the stamps of the files that exist, without the
    targets in omit.'''
    return self.world.table(n for n in self.names(proj) if n not in omit)

  def build(self, proj, recipes):
    '''Builds what is stale.  Returns the targets whose recipe ran, in the
    order of completion, and the targets whose recipe failed.'''
    built, failed, running = [], [], {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=self.jobs) as pool:
      while True:
        table = self.table(proj, omit=list(running) + failed)
        ready = ask(Build.ready, proj, table)
        self.trace('ready: %s' % (' '.join(ready) or '(none)'))
        for target in ready:
          if target in running or target in built or target in failed:
            continue
          inputs, words = recipes[target]
          running[target] = pool.submit(self.runner.run, target, inputs, words)
        if not running:
          break
        done, _ = concurrent.futures.wait(
            running.values(), return_when=concurrent.futures.FIRST_COMPLETED
          )
        for target in [t for t, future in running.items() if future in done]:
          status = running.pop(target).result()
          self.trace('done: %s (status %d)' % (target, status))
          (built if status == 0 else failed).append(target)
    return built, failed

  def status(self, proj, built, failed):
    '''One line per target: built, failed, up to date, or stale.'''
    table = self.table(proj, omit=failed)
    rows = []
    for target in ask(Build.targets, proj):
      if target in built:
        state = 'built'
      elif target in failed:
        state = 'failed'
      elif ask(Build.stale, proj, table, target):
        state = 'stale'
      else:
        state = 'up to date'
      rows.append((target, state))
    return rows

def show_rules(rules, out):
  '''Prints rules as rows: the target, its inputs, and its recipe.'''
  rows = [
      (target, ' '.join(inputs), ' '.join(words))
          for target, inputs, words in rules
    ]
  widths = [max(len(row[i]) for row in rows) for i in range(2)]
  for target, inputs, recipe in rows:
    out('  %-*s <- %-*s  %s' % (widths[0], target, widths[1], inputs, recipe))

def show_plan(proj, builder, out):
  '''Prints the plan and the waves and returns the recipes of the plan: an
  empty dict when there is nothing to do, and when the plan has no value,
  which is a cycle in the rules.'''
  table = builder.table(proj)
  plan = next(curry.eval(Build.plan, proj, table, converter='topython'), None)
  if plan is None:
    out('plan: no value (the rules have a cycle)')
    return {}
  if not plan:
    out('plan: nothing to do')
    return {}
  out('plan: %d target%s' % (len(plan), '' if len(plan) == 1 else 's'))
  show_rules(plan, out)
  waves = ask(Build.waves, proj, table)
  out('waves: ' + ' '.join('[%s]' % ' '.join(wave) for wave in waves))
  return {target: (inputs, words) for target, inputs, words in plan}

def run_build(proj, builder, out):
  '''Lints, prints the plan, builds, and prints what was built and the
  status.  A target that two rules claim stops the build before the plan.'''
  if not lint(proj, out):
    out('refused: the build does not start')
    return []
  recipes = show_plan(proj, builder, out)
  built, failed = builder.build(proj, recipes) if recipes else ([], [])
  if built:
    # The pool returns the targets in the order of completion; sort them.
    out('built: ' + ' '.join(sorted(built)))
  if failed:
    out('failed: ' + ' '.join(sorted(failed)))
  out('status:')
  for target, state in builder.status(proj, built, failed):
    out('  %-10s %s' % (target, state))
  return built

def lint(proj, out):
  '''Reports every target that two rules claim.  True when there is none.'''
  problems = ask(Build.ambiguous, proj)
  for target, rules in problems:
    out('ambiguous: %s has %d rules' % (target, len(rules)))
    show_rules(rules, out)
  return not problems

def demo(world, builder, out):
  '''The tested run: a full build, a build with nothing to do, a touch of a
  header with the prediction of the inverse query, the lint, and a cycle.'''
  proj = project(world)
  out('sources: ' + ' '.join(name for name in FILES if name.endswith('.c')))
  out('headers: ' + ' '.join(name for name in FILES if name.endswith('.h')))
  out('includes: ' + '; '.join(
      '%s -> %s' % (name, ' '.join(headers))
          for name, headers in world.includes() if headers
    ))
  out('targets: ' + ' '.join(ask(Build.targets, proj)))

  out('')
  out('1. full build')
  run_build(proj, builder, out)

  out('')
  out('2. build again')
  run_build(proj, builder, out)

  out('')
  out('3. touch shape.h')
  world.touch('shape.h')
  affected = answers(Build.affected, proj, 'shape.h')
  out('affected: ' + ' '.join(affected))
  built = run_build(proj, builder, out)
  out('rebuilt the affected set: %s'
      % ('yes' if sorted(built) == affected else 'no'))

  out('')
  out('4. a second rule for main.o')
  extra = project(world, [EXTRA_RULE])
  out('explicit:')
  show_rules([EXTRA_RULE], out)
  run_build(extra, builder, out)

  out('')
  out('5. a rule that closes a cycle')
  cyclic = project(world, [CYCLE_RULE])
  out('explicit:')
  show_rules([CYCLE_RULE], out)
  run_build(cyclic, builder, out)

PAGE = '''<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Build</title></head>
<body>
<h1>Build</h1>
<form method="get">
  <button name="build" value="1">build</button>
  touch <select name="touch"><option value=""></option>%(options)s</select>
  <button>touch</button>
  <a href="/status.json">status.json</a>
</form>
<pre>%(report)s</pre>
</body></html>
'''

def status_json(world, builder):
  '''The state of the project as JSON: the targets with their inputs, the
  plan, and the ready set.'''
  proj = project(world)
  table = builder.table(proj)
  return {
      'targets': [
          { 'name': target
          , 'inputs': ask(Build.inputs, proj, target)
          , 'stale': ask(Build.stale, proj, table, target)
          }
          for target in ask(Build.targets, proj)
        ]
    , 'plan': ask(Build.plan, proj, table)
    , 'ready': ask(Build.ready, proj, table)
    }

def serve(port, world, builder):
  '''Serves a status page on the local host.  A request can touch a file or
  build; /status.json gives the state as JSON.'''
  class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
      url = urllib.parse.urlparse(self.path)
      query = urllib.parse.parse_qs(url.query)
      if url.path == '/status.json':
        text = json.dumps(status_json(world, builder), indent=1)
        self.reply(text, 'application/json')
        return
      lines = []
      touched = query.get('touch', [''])[0]
      if touched in FILES:
        world.touch(touched)
        lines.append('touched %s' % touched)
        affected = answers(Build.affected, project(world), touched)
        lines.append('affected: ' + ' '.join(affected))
      if query.get('build'):
        run_build(project(world), builder, lines.append)
      if not lines:
        for target, state in builder.status(project(world), [], []):
          lines.append('  %-10s %s' % (target, state))
      options = ''.join('<option>%s</option>' % name for name in FILES)
      page = PAGE % dict(options=options, report=html.escape('\n'.join(lines)))
      self.reply(page, 'text/html; charset=utf-8')

    def reply(self, text, content_type):
      data = text.encode('utf-8')
      self.send_response(200)
      self.send_header('Content-Type', content_type)
      self.send_header('Content-Length', str(len(data)))
      self.end_headers()
      self.wfile.write(data)

  server = http.server.HTTPServer(('127.0.0.1', port), Handler)
  print('serving on http://127.0.0.1:%d/  (press Ctrl-C to stop)'
        % server.server_port)
  sys.stdout.flush()
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    pass

def main(argv=None):
  parser = argparse.ArgumentParser(
      description='Builds a toy C project.  Curry decides, Python works.'
    )
  parser.add_argument(
      '--jobs', type=int, default=JOBS, metavar='N'
    , help='the width of the thread pool (default: %(default)s)'
    )
  parser.add_argument(
      '--trace', action='store_true'
    , help='print each ready set and each completion to stderr'
    )
  parser.add_argument(
      '--serve', type=int, metavar='PORT'
    , help='serve a status page on this port of the local host'
    )
  args = parser.parse_args(argv)
  if args.trace:
    trace = lambda line: print(line, file=sys.stderr, flush=True)
  else:
    trace = lambda line: None
  with tempfile.TemporaryDirectory(prefix='build-') as root:
    world = World(root)
    builder = Builder(world, Runner(world), args.jobs, trace)
    if args.serve is not None:
      serve(args.serve, world, builder)
    else:
      demo(world, builder, lambda line: print(line, flush=True))
  return 0

if __name__ == '__main__':
  sys.exit(main())
