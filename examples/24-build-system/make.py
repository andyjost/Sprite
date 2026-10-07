'''
A driver for a makefile written in Curry.

The makefile is a Curry module beside the sources of a project.  Its
variables are definitions with the uppercase names of make, CC = "cc".  The
relation rule gives a target its inputs and its recipe, one equation per
rule of make.  The relation depends gives a file a header it includes, one
equation per edge.  The definition goal names the default goal.  The library
Make.curry beside this script answers the questions of make over the two
relations.  This driver owns the world: it substitutes the assignments of
its command line into the makefile, reads the variables and the stamps of
the files, runs the recipes, and prints the plan.  Nothing here names a file
of the project or a language.

Usage: python make.py [-f FILE] [-C DIR] [-j N] [-n] [--touch FILE]
                      [--affected FILE] [--trace] [GOAL] [NAME=value ...]
'''
import argparse
import concurrent.futures
import hashlib
import os
import re
import shlex
import subprocess
import sys
import time
import curry

# Find Make.curry, the library, next to this script, whatever the working
# directory is.
HERE = os.path.dirname(os.path.abspath(__file__))
curry.path.insert(0, HERE)
from curry.lib import Make

STRING = ('String', '[Char]')  # the type String, as curry.typeof prints it

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

def literal(value):
  '''A Python string as a Curry string literal.'''
  return '"%s"' % value.replace('\\', '\\\\').replace('"', '\\"')

def override(text, name, value):
  '''The text of a makefile with the assignment of NAME replaced by
  NAME = "value", as make replaces a variable of the file with one from its
  command line.  A line that starts with NAME and = is the assignment.  The
  first is replaced and any other is dropped.  A file without one gets the
  line at its end.'''
  line = '%s = %s' % (name, literal(value))
  pattern = re.compile(r'^%s[ \t]*=' % re.escape(name))
  lines = text.split('\n')
  found = [i for i, text_line in enumerate(lines) if pattern.match(text_line)]
  if not found:
    return text.rstrip('\n') + '\n' + line + '\n'
  lines[found[0]] = line
  return '\n'.join(l for i, l in enumerate(lines) if i not in found[1:])

def load_makefile(path, overrides):
  '''Imports the makefile as a Curry module.  Its directory goes on the Curry
  path first, so the module finds the modules beside it.  With overrides,
  the substituted text goes to .curry/overrides/HASH beside the makefile,
  and the module is imported from there; a second run with the same
  overrides finds the compiled products of the first.'''
  if not os.path.isfile(path):
    stop('no makefile %s' % path)
  directory, filename = os.path.split(os.path.realpath(path))
  stem, suffix = os.path.splitext(filename)
  if suffix != '.curry':
    stop('%s: a makefile is a .curry file' % path)
  curry.path.insert(0, directory)
  if overrides:
    with open(path, encoding='utf-8') as stream:
      text = stream.read()
    for name, value in overrides.items():
      text = override(text, name, value)
    digest = hashlib.sha1(text.encode('utf-8')).hexdigest()[:16]
    cache = os.path.join(directory, '.curry', 'overrides', digest)
    copy = os.path.join(cache, filename)
    if not os.path.exists(copy):
      os.makedirs(cache, exist_ok=True)
      with open(copy + '.%d' % os.getpid(), 'w', encoding='utf-8') as stream:
        stream.write(text)
      os.replace(copy + '.%d' % os.getpid(), copy)
    curry.path.insert(0, cache)
  return curry.import_(stem)

def variables(module):
  '''The table of the variables of a makefile: every definition whose name
  starts with an uppercase letter and whose type is String, with each of
  its values.  A definition with two values gives two rows.'''
  table = []
  for name in sorted(dir(module)):
    if not name[:1].isupper():
      continue
    symbol = getattr(module, name)
    try:
      if curry.typeof(symbol) not in STRING:
        continue
    except Exception:
      continue
    values = curry.eval(symbol, converter='topython')
    table.extend((name, value) for value in values)
  return table

class World:
  '''The files of the project in one directory, and what Python knows about
  them: their stamps.  Curry sees the stamps as a table and never touches a
  file.'''

  def __init__(self, root):
    self.root = root

  def path(self, name):
    return os.path.join(self.root, name)

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

class Build:
  '''One build: a makefile read from the goal down into one Curry value that
  every question shares.  Curry answers the questions; the build loop runs
  the recipes.'''

  def __init__(self, module, table, world, goal, jobs, trace):
    self.world = world
    self.jobs = jobs
    self.trace = trace
    depends = getattr(module, 'depends', Make.noDepends)
    self.build = curry.expr(Make.build, module.rule, depends, table, goal)
    # The names of the build: the goal, what it reads, and so on.  The
    # targets are the names with a recipe; the rest are sources.
    self.names = ask(Make.names, self.build)
    self.targets = ask(Make.targets, self.build)

  def table(self, omit=()):
    '''The table Curry sees: the stamps of the files of the build that
    exist, without the targets in omit.'''
    return self.world.stamps(n for n in self.names if n not in omit)

  def ambiguous(self):
    '''The targets that two rules claim, each with its rules.'''
    groups = {}
    for row in ask(Make.ambiguous, self.build):
      groups.setdefault(row[0], []).append(row)
    return groups

  def missing(self):
    '''The sources that do not exist, each with the targets that read it.'''
    return ask(Make.missing, self.build, self.table())

  def recipes(self, target):
    '''Every value of the recipe of a target.'''
    return ask(Make.recipes, self.build, target)

  def undefined(self, target):
    '''The variables of the recipe of a target that the makefile does not
    define.'''
    return ask(Make.undefined, self.build, target)

  def plan(self):
    '''The plan, or None on a cycle in the rules.'''
    return ask(Make.plan, self.build, self.table())

  def waves(self):
    return ask(Make.waves, self.build, self.table())

  def ready(self, omit):
    return ask(Make.ready, self.build, self.table(omit))

  def affected(self, name):
    return answers(Make.affected, self.build, name)

  def run(self, plan, env, out):
    '''Builds what is stale.  Curry names the targets that can run now; the
    thread pool runs their recipes; after each completion the loop asks
    again.  Python holds no dependency and no order.  The table it hands to
    Curry omits the targets whose recipes run or failed: a compiler creates
    its output before it finishes, and a target that is missing to Curry is
    stale, so its dependents are not ready.  Each recipe is printed when it
    starts, as make prints it, and its output follows when it completes.
    Returns the targets whose recipe ran and the targets whose recipe
    failed.'''
    recipes = {target: recipe for target, needs, recipe in plan}
    built, failed, running = [], [], {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=self.jobs) as pool:
      while True:
        ready = self.ready(omit=list(running) + failed)
        self.trace('ready: %s' % (' '.join(ready) or '(none)'))
        for target in ready:
          if target in running or target in built or target in failed:
            continue
          out(recipes[target])
          running[target] = pool.submit(self.execute, recipes[target], env)
        if not running:
          break
        done, _ = concurrent.futures.wait(
            running.values(), return_when=concurrent.futures.FIRST_COMPLETED
          )
        for target in [t for t, future in running.items() if future in done]:
          status, stdout, stderr = running.pop(target).result()
          sys.stdout.write(stdout)
          sys.stdout.flush()
          sys.stderr.write(stderr)
          sys.stderr.flush()
          self.trace('done: %s (status %d)' % (target, status))
          (built if status == 0 else failed).append(target)
    return built, failed

  def execute(self, recipe, env):
    '''Runs one recipe in the project directory, as one process without a
    shell, split into words as a shell would split them, with the variables
    of the makefile in its environment.  Its output is captured, so that
    the recipes of one wave do not interleave, and the loop prints it when
    the recipe completes.  Returns the status, the standard output and the
    standard error.  A program that cannot start is the status 127 of the
    shell, with the error of the system as the standard error.'''
    words = shlex.split(recipe)
    try:
      proc = subprocess.run(
          words, cwd=self.world.root, env=env, capture_output=True, text=True
        )
    except OSError as error:
      return 127, '', '%s: %s\n' % (words[0], error.strerror)
    return proc.returncode, proc.stdout, proc.stderr

def show_rows(rows, out):
  '''Prints rules as rows: the target, what it reads, and its recipe.'''
  rows = [(target, ' '.join(needs), recipe) for target, needs, recipe in rows]
  widths = [max([len(row[i]) for row in rows], default=0) for i in range(2)]
  for target, needs, recipe in rows:
    out('  %-*s <- %-*s  %s' % (widths[0], target, widths[1], needs, recipe))

def lint(build, out):
  '''Prints what stops a build before its plan: a target that two rules
  claim, a source that is missing, and a target whose recipe has two values
  or none.  Returns True when the build may start.'''
  groups = build.ambiguous()
  for target, claims in sorted(groups.items()):
    out('ambiguous: %s has %d rules' % (target, len(claims)))
    show_rows(claims, out)
  lost = build.missing()
  for source, needed in lost:
    out('no rule to make %s, needed by %s' % (source, ' '.join(needed)))
  faulty = []
  for target in build.targets:
    if target in groups:
      continue
    recipes = build.recipes(target)
    if len(recipes) == 1:
      continue
    faulty.append(target)
    if recipes:
      out('%s has %d recipes' % (target, len(recipes)))
      for recipe in recipes:
        out('  ' + recipe)
    else:
      names = ['$(%s)' % name for name in build.undefined(target)]
      if names:
        out('no recipe for %s: %s %s undefined' % (
            target, ' '.join(names), 'is' if len(names) == 1 else 'are'))
      else:
        out('no recipe for %s' % target)
  return not (groups or lost or faulty)

def show_plan(build, out):
  '''Prints the plan and the waves.  Returns the plan, or None when the
  rules have a cycle, which leaves the plan without a value.'''
  plan = build.plan()
  if plan is None:
    out('plan: no value (the rules have a cycle)')
  elif not plan:
    out('plan: nothing to do')
  else:
    out('plan: %d target%s' % (len(plan), '' if len(plan) == 1 else 's'))
    show_rows(plan, out)
    out('waves: ' + ' '.join('[%s]' % ' '.join(w) for w in build.waves()))
  return plan

def make(build, dry_run, env, out):
  '''Lints, plans, and builds.  Returns the exit status: 2 when the build
  does not start, a recipe fails, or a target of the plan stays stale, as
  make does.'''
  if not lint(build, out):
    out('refused: the build does not start')
    return 2
  plan = show_plan(build, out)
  if plan is None:
    return 2
  if dry_run or not plan:
    return 0
  built, failed = build.run(plan, env, out)
  if failed:
    out('failed: ' + ' '.join(sorted(failed)))
  # A target of the plan that never ran is one whose inputs never came up
  # to date: a recipe that wrote no output leaves its dependents stale.
  left = [t for t, needs, recipe in plan if t not in built + failed]
  return 2 if failed or left else 0

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
      '-j', '--jobs', type=int, default=1, metavar='N'
    , help='the number of recipes that run at once (default: %(default)s)'
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
      'words', nargs='*', metavar='GOAL|NAME=value'
    , help='the target to build (default: goal of the makefile), and '
           'assignments that replace those of the makefile'
    )
  args = parser.parse_args(argv)
  if args.trace:
    trace = lambda line: print(line, file=sys.stderr, flush=True)
  else:
    trace = lambda line: None
  out = lambda line: print(line, flush=True)
  goals = [word for word in args.words if '=' not in word]
  overrides = dict(word.split('=', 1) for word in args.words if '=' in word)
  if len(goals) > 1:
    stop('one goal at a time: %s' % ' '.join(goals))
  world = World(os.path.abspath(args.directory))
  module = load_makefile(os.path.join(world.root, args.file), overrides)
  if not hasattr(module, 'rule'):
    stop('the makefile defines no rule')
  table = variables(module)
  if goals:
    goal = goals[0]
  elif hasattr(module, 'goal'):
    goal = ask(module.goal)
  else:
    stop('no goal: pass GOAL or define goal in the makefile')
  build = Build(module, table, world, goal, args.jobs, trace)
  if goal not in build.targets:
    if os.path.exists(world.path(goal)):
      out('%s is up to date' % goal)
      return 0
    stop('no rule to make %s' % goal)
  if args.touch:
    if not os.path.exists(world.path(args.touch)):
      stop('no file %s' % args.touch)
    world.touch(args.touch, build.names)
  if args.affected:
    out('affected: ' + (' '.join(build.affected(args.affected)) or '(none)'))
  env = dict(os.environ)
  env.update(table)
  return make(build, args.dry_run, env, out)

if __name__ == '__main__':
  sys.exit(main())
