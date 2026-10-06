'''
A driver for a makefile written in Curry.

The makefile is a Curry module beside the sources of a project.  It defines
rule, a function from a target to its rule, and goal, the default goal; the
library Make.curry beside this script asks the questions of make over that
function.  A makefile may define makefiles instead of rule, a list of named
makefiles, as a toolchain matrix does.  This driver owns the world: it scans
the includes of the sources, reads the stamps of the files, runs the commands
in a thread pool, and prints the plan, the waves and a status table.  Nothing
here names a file of the project.  The include scan is the one piece of
knowledge of the language: the driver is generic for a C project.

Usage: python make.py [-f FILE] [-C DIR] [-j N] [-n] [--touch FILE]
                      [--affected FILE] [--trace] [GOAL]
       python make.py [-f FILE] [-C DIR] [-j N] --serve PORT
'''
import argparse
import concurrent.futures
import html
import http.server
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import urllib.parse
import curry

# Find Make.curry, the library, next to this script, whatever the working
# directory is.
HERE = os.path.dirname(os.path.abspath(__file__))
curry.path.insert(0, HERE)
from curry.lib import Make

# The include scan: the quoted includes of a C file.  Make reads the same
# list from the .d files of the compiler.
INCLUDE = re.compile(r'^\s*#\s*include\s*"([^"]+)"', re.MULTILINE)
SCANNED = ('.c', '.h')

JOBS = 4  # the default width of the thread pool; make's default is 1

def stop(message):
  '''Prints an error and exits with the status 2 of make.'''
  print('make.py: %s' % message, file=sys.stderr)
  raise SystemExit(2)

def ask(goal, *args):
  '''The one value of a deterministic goal, as Python data, or None when the
  goal has no value.'''
  return next(curry.eval(goal, *args, converter='topython'), None)

def answers(goal, *args):
  '''Every value of a goal, sorted.  Curry promises no order.'''
  return sorted(curry.eval(goal, *args, converter='topython'))

def rules(goal, *args):
  '''The value of a goal whose value is a list of rules, as a list of
  (target, inputs, command) tuples, or None.  Make.rows turns the rules into
  tuples, which the converter knows.'''
  return ask(Make.rows, curry.expr(goal, *args))

def load_makefile(path):
  '''Imports the makefile as a Curry module.  Its directory goes on the Curry
  path first, so the module finds the modules beside it.  A link to a
  makefile is read at its target, so the compiled form lives beside the
  original.'''
  if not os.path.isfile(path):
    stop('no makefile %s' % path)
  directory, filename = os.path.split(os.path.realpath(path))
  stem, suffix = os.path.splitext(filename)
  if suffix != '.curry':
    stop('%s: a makefile is a .curry file' % path)
  curry.path.insert(0, directory)
  return curry.import_(stem)

def makefiles(module):
  '''The makefiles of the module as (name, rule function) pairs: rule alone,
  with the empty name, or the entries of makefiles.'''
  if hasattr(module, 'makefiles'):
    return ask(module.makefiles)
  if hasattr(module, 'rule'):
    return [('', module.rule)]
  stop('the makefile defines neither rule nor makefiles')

class World:
  '''The files of the project in one directory, and what Python knows about
  them: their includes and their stamps.  Curry sees the stamps as a table
  and never touches a file.'''

  def __init__(self, root):
    self.root = root

  def path(self, name):
    return os.path.join(self.root, name)

  def includes(self):
    '''(file, headers) for each C source and header of the directory, by
    the regular expression: the automatic dependencies of make.'''
    table = []
    for name in sorted(os.listdir(self.root)):
      if name.endswith(SCANNED):
        with open(self.path(name), encoding='utf-8', errors='replace') as stream:
          table.append((name, INCLUDE.findall(stream.read())))
    return table

  def stamps(self, names):
    '''The stamps of the files that exist: the modification time in
    nanoseconds.  A missing file has no entry.'''
    table = []
    for name in names:
      try:
        table.append((name, os.stat(self.path(name)).st_mtime_ns))
      except FileNotFoundError:
        pass
    return table

  def touch(self, name, others):
    '''Gives a file the modification time of now, and waits for the clock
    when now is not newer than every other file of the build.  A file system
    with a coarse clock gives the same result after a pause of one tick.'''
    newest = max(
        [stamp for other, stamp in self.stamps(others) if other != name]
      , default=0
      )
    while True:
      os.utime(self.path(name))
      if os.stat(self.path(name)).st_mtime_ns > newest:
        return
      time.sleep(0.01)

def programs(plan):
  '''The programs the commands of a plan run: the first word of each.'''
  return sorted(set(shlex.split(command)[0] for target, inputs, command in plan))

def missing(plan):
  '''The programs of a plan that are not on the PATH.'''
  return [p for p in programs(plan) if not shutil.which(p)]

class Runner:
  '''Runs the commands in the project directory, each as one process without
  a shell, split into words as a shell would split them.  When a program of
  the plan is not on the PATH, every command runs as a stand-in that writes a
  placeholder file in place of the target, so the example runs on a machine
  without a compiler.  The output is the same.'''

  def __init__(self, world, plan):
    self.world = world
    absent = missing(plan)
    self.real = not absent
    if absent:
      print('note: %s not on the PATH; the commands write placeholder files'
            % ', '.join(absent), file=sys.stderr)

  def run(self, target, inputs, command):
    '''Runs one command and returns its status.'''
    if not self.real:
      with open(self.world.path(target), 'w') as stream:
        stream.write(
            'placeholder for %s from %s\n' % (target, ' '.join(inputs))
          )
      return 0
    proc = subprocess.run(
        shlex.split(command), cwd=self.world.root, capture_output=True, text=True
      )
    if proc.returncode:
      sys.stderr.write(proc.stderr)
    return proc.returncode

class Build:
  '''One build: a makefile read from the goal down, with the automatic
  dependencies, in one Curry value that every question shares.  Curry answers
  the questions; the build loop runs the commands.'''

  def __init__(self, name, rule, world, goal, jobs, trace):
    self.name = name
    self.world = world
    self.goal = goal
    self.jobs = jobs
    self.trace = trace
    self.build = curry.expr(Make.build, rule, world.includes(), goal)
    # The names of the build: the goal, what it reads, and so on.  The
    # targets are the names with a command; the rest are sources.
    self.names = ask(Make.names, self.build)
    self.targets = ask(Make.targets, self.build)

  def table(self, omit=()):
    '''The table Curry sees: the stamps of the files of the build that
    exist, without the targets in omit.'''
    return self.world.stamps(n for n in self.names if n not in omit)

  def ambiguous(self):
    '''The targets that two rules claim, each with its rules.'''
    groups = {}
    for rule in rules(Make.ambiguous, self.build):
      groups.setdefault(rule[0], []).append(rule)
    return groups

  def missing(self):
    '''The sources that do not exist, each with the targets that read it.'''
    return ask(Make.missing, self.build, self.table())

  def plan(self):
    '''The plan, or None on a cycle in the rules.'''
    return rules(Make.plan, self.build, self.table())

  def waves(self):
    return ask(Make.waves, self.build, self.table())

  def ready(self, omit):
    return ask(Make.ready, self.build, self.table(omit))

  def stale(self, target, omit=()):
    return ask(Make.stale, self.build, self.table(omit), target)

  def inputs(self, target):
    return ask(Make.inputs, self.build, target)

  def affected(self, name):
    return answers(Make.affected, self.build, name)

  def run(self, plan):
    '''Builds what is stale.  Curry names the targets that can run now; the
    thread pool runs their commands; after each completion the loop asks
    again.  Python holds no dependency and no order.  The table it hands to
    Curry omits the targets whose commands run or failed: a compiler creates
    its output before it finishes, and a target that is missing to Curry is
    stale, so its dependents are not ready.  Returns the targets whose
    command ran, in the order of completion, and the targets whose command
    failed.'''
    recipes = {target: (inputs, command) for target, inputs, command in plan}
    runner = Runner(self.world, plan)
    built, failed, running = [], [], {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=self.jobs) as pool:
      while True:
        ready = self.ready(omit=list(running) + failed)
        self.trace('ready: %s' % (' '.join(ready) or '(none)'))
        for target in ready:
          if target in running or target in built or target in failed:
            continue
          inputs, command = recipes[target]
          running[target] = pool.submit(runner.run, target, inputs, command)
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

  def status(self, built, failed):
    '''One line per target: built, failed, up to date, or stale.'''
    rows = []
    for target in self.targets:
      if target in built:
        state = 'built'
      elif target in failed:
        state = 'failed'
      elif self.stale(target, omit=failed):
        state = 'stale'
      else:
        state = 'up to date'
      rows.append((target, state))
    return rows

def show_rules(rules, out):
  '''Prints rules as rows: the target, its inputs, and its command.'''
  rows = [(target, ' '.join(inputs), command) for target, inputs, command in rules]
  widths = [max([len(row[i]) for row in rows], default=0) for i in range(2)]
  for target, inputs, command in rows:
    out('  %-*s <- %-*s  %s' % (widths[0], target, widths[1], inputs, command))

def show_status(build, built, failed, out):
  out('status:')
  width = max(len(target) for target in build.targets)
  for target, state in build.status(built, failed):
    out('  %-*s  %s' % (width, target, state))

def show_plan(build, out):
  '''Lints, then prints the plan and the waves.  Returns the plan, or None
  when the build must not start: a target that two rules claim, a source
  that is missing, or a cycle in the rules, which leaves the plan without a
  value.'''
  groups = build.ambiguous()
  for target, claims in sorted(groups.items()):
    out('ambiguous: %s has %d rules' % (target, len(claims)))
    show_rules(claims, out)
  lost = build.missing()
  for source, needed in lost:
    out('no rule to make %s, needed by %s' % (source, ' '.join(needed)))
  if groups or lost:
    out('refused: the build does not start')
    return None
  plan = build.plan()
  if plan is None:
    out('plan: no value (the rules have a cycle)')
  elif not plan:
    out('plan: nothing to do')
  else:
    out('plan: %d target%s' % (len(plan), '' if len(plan) == 1 else 's'))
    show_rules(plan, out)
    out('waves: ' + ' '.join('[%s]' % ' '.join(w) for w in build.waves()))
  return plan

def make(builds, dry_run, out):
  '''Prints the plan of every makefile, builds with one of them, and prints
  what was built and the status.  With several makefiles the build takes the
  first whose programs are on the PATH, or the first.  Returns the exit
  status: 2 when a build does not start, a command fails, or a target of the
  plan stays stale, as make does.'''
  plans = []
  for build in builds:
    if build.name:
      out('makefile %s:' % build.name)
    plans.append(show_plan(build, out))
  usable = [(b, p) for b, p in zip(builds, plans) if p is not None]
  if len(usable) < len(builds):
    return 2
  if dry_run:
    return 0
  build, plan = next(
      ((b, p) for b, p in usable if not missing(p)), usable[0]
    )
  if build.name:
    out('build with %s' % build.name)
  built, failed = build.run(plan) if plan else ([], [])
  if built:
    # The pool returns the targets in the order of completion; sort them.
    out('built: ' + ' '.join(sorted(built)))
  if failed:
    out('failed: ' + ' '.join(sorted(failed)))
  show_status(build, built, failed, out)
  # A target of the plan that never ran is one whose inputs never came up
  # to date: a command that wrote no output leaves its dependents stale.
  left = [t for t, inputs, command in plan if t not in built + failed]
  return 2 if failed or left else 0

PAGE = '''<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>make</title></head>
<body>
<h1>make</h1>
<form method="get">
  <button name="build" value="1">build</button>
  touch <select name="touch"><option value=""></option>%(options)s</select>
  <button>touch</button>
  <a href="/status.json">status.json</a>
</form>
<pre>%(report)s</pre>
</body></html>
'''

def status_json(build):
  '''The state of a build as JSON: the targets with their inputs and
  staleness, the plan, and the ready set.'''
  return {
      'targets': [
          { 'name': target
          , 'inputs': build.inputs(target)
          , 'stale': build.stale(target)
          }
          for target in build.targets
        ]
    , 'plan': build.plan()
    , 'ready': build.ready(omit=())
    }

def serve(port, new_builds):
  '''Serves a status page on the local host.  A request can touch a file or
  build; /status.json gives the state of the first makefile as JSON.
  new_builds() reads the makefiles against the current directory.'''
  class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
      url = urllib.parse.urlparse(self.path)
      query = urllib.parse.parse_qs(url.query)
      builds = new_builds()
      first = builds[0]
      if url.path == '/status.json':
        self.reply(json.dumps(status_json(first), indent=1), 'application/json')
        return
      lines = []
      touched = query.get('touch', [''])[0]
      if touched in first.names:
        first.world.touch(touched, first.names)
        lines.append('touched %s' % touched)
        lines.append('affected: ' + ' '.join(first.affected(touched)))
      if query.get('build'):
        make(builds, False, lines.append)
      if not lines:
        show_status(first, [], [], lines.append)
      options = ''.join('<option>%s</option>' % name for name in first.names)
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
      description='Builds a project from a makefile written in Curry.'
    )
  parser.add_argument(
      '-f', '--file', default='Makefile.curry', metavar='FILE'
    , help='the makefile, relative to DIR (default: %(default)s)'
    )
  parser.add_argument(
      '-C', '--directory', default='.', metavar='DIR'
    , help='the project directory (default: the working directory)'
    )
  parser.add_argument(
      '-j', '--jobs', type=int, default=JOBS, metavar='N'
    , help='the width of the thread pool (default: %(default)s)'
    )
  parser.add_argument(
      '-n', '--dry-run', action='store_true'
    , help='print the plan and the waves and stop'
    )
  parser.add_argument(
      '--touch', metavar='FILE'
    , help='give FILE a newer stamp than every other file of the build first'
    )
  parser.add_argument(
      '--affected', metavar='FILE'
    , help='print the targets that read FILE, directly or through another '
           'target, before the plan'
    )
  parser.add_argument(
      '--trace', action='store_true'
    , help='print each ready set and each completion to stderr'
    )
  parser.add_argument(
      '--serve', type=int, metavar='PORT'
    , help='serve a status page on this port of the local host'
    )
  parser.add_argument(
      'goal', nargs='?'
    , help='the target to build (default: goal of the makefile)'
    )
  args = parser.parse_args(argv)
  if args.trace:
    trace = lambda line: print(line, file=sys.stderr, flush=True)
  else:
    trace = lambda line: None
  world = World(os.path.abspath(args.directory))
  module = load_makefile(os.path.join(world.root, args.file))
  goal = args.goal
  if goal is None:
    if not hasattr(module, 'goal'):
      stop('no goal: pass GOAL or define goal in the makefile')
    goal = ask(module.goal)
  new_builds = lambda: [
      Build(name, rule, world, goal, args.jobs, trace)
          for name, rule in makefiles(module)
    ]
  if args.serve is not None:
    serve(args.serve, new_builds)
    return 0
  builds = new_builds()
  first = builds[0]
  if goal not in first.targets:
    if os.path.exists(world.path(goal)):
      print('%s is up to date' % goal)
      return 0
    stop('no rule to make %s' % goal)
  out = lambda line: print(line, flush=True)
  if args.touch:
    if not os.path.exists(world.path(args.touch)):
      stop('no file %s' % args.touch)
    world.touch(args.touch, first.names)
  if args.affected:
    out('affected: ' + ' '.join(first.affected(args.affected)))
  return make(builds, args.dry_run, out)

if __name__ == '__main__':
  sys.exit(main())
