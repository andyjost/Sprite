'''
Make in a few lines of Python over a makefile written in Curry.  Curry
answers the questions of the relations rule and depends; Python reads the
clock and runs the recipes.  make.py beside this script is the full driver.

Usage: python minimake.py [DIR] [GOAL]
'''
import concurrent.futures, os, re, shlex, subprocess, sys

os.environ.setdefault('SPRITE_FRONTEND_WARNINGS', '0')  # the rules overlap by design
import curry

def load(directory='.'):
  '''Imports Makefile.curry of a project directory and moves there, so that
  the names of the makefile are the files of the current directory.'''
  global Makefile
  os.chdir(directory)
  curry.path.insert(0, os.getcwd())
  Makefile = curry.import_('Makefile')
  return Makefile

def rules(target):
  '''The prerequisites and the recipe of every rule of a target: the answers
  of rule target prereqs with prereqs free.'''
  prereqs = curry.free('prereqs')
  return [(bindings[prereqs], recipe)
          for recipe, bindings in curry.solve(Makefile.rule(target, prereqs))]

def headers(source):
  '''Every header behind a file: the values of depends, and theirs.'''
  found = set(curry.eval(Makefile.depends(source)))
  return found.union(*map(headers, found))

def needs(target):
  '''What a target reads: the prerequisites of its rules and the headers
  behind them.  A source has no rule and reads nothing.'''
  prereqs = [p for ps, recipe in rules(target) for p in ps]
  return prereqs + sorted(set().union(*map(headers, prereqs)))

def interpolate(recipe, target, prereqs, makefile=None):
  '''The recipe with make's automatic variables filled: $@ is the target, $<
  the first prerequisite and $^ all of them.  With the makefile, $(NAME) is
  the value of its definition NAME; without it, $(NAME) stays as written.'''
  if makefile is not None:
    for name in re.findall(r'\$\((\w+)\)', recipe):
      recipe = recipe.replace(f'$({name})', next(curry.eval(getattr(makefile, name))))
  return (recipe.replace('$@', target).replace('$<', ' '.join(prereqs[:1]))
                .replace('$^', ' '.join(prereqs)))

def command(target):
  '''The command of a target: its recipe over everything the target reads.'''
  [(_, recipe)] = rules(target)
  return interpolate(recipe, target, needs(target), Makefile)

def stale(name):
  '''A target is stale when it is missing, when it is older than a file it
  reads or when it reads a stale target.  A source is stale only when it
  is missing.'''
  if not os.path.exists(name):
    return True
  return any(stale(f) or os.path.getmtime(f) > os.path.getmtime(name)
             for f in needs(name))

def names(target):
  '''A target and everything it reads, directly or through another target.'''
  return {target}.union(*map(names, needs(target)))

def make(goal, jobs=4):
  '''Builds the stale targets from the goal down, wave by wave: a wave holds
  the pending targets that read no pending target, and its commands run at
  once in a pool of threads.'''
  pending = [t for t in sorted(names(goal)) if rules(t) and stale(t)]
  if not pending:
    print(goal, 'is up to date')
  with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
    while pending:
      wave = [t for t in pending if not any(f in pending for f in needs(t))]
      if not wave:
        sys.exit('the rules have a cycle')
      lines = [command(t) for t in wave]
      print(*lines, sep='\n', flush=True)
      list(pool.map(lambda line: subprocess.run(shlex.split(line), check=True), lines))
      pending = [t for t in pending if t not in wave]

if __name__ == '__main__':
  load(sys.argv[1] if len(sys.argv) > 1 else '.')
  make(sys.argv[2] if len(sys.argv) > 2 else next(curry.eval(Makefile.goal)))
