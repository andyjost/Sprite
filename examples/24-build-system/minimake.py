'''
Make in a few lines of Python over a makefile written in Curry.  Curry
answers the questions of the relations rule and depends; Python reads the
clock and runs the recipes.  make.py beside this script is the full driver.

Usage: python minimake.py [DIR] [GOAL]
'''
import concurrent.futures, os, re, shlex, subprocess, sys

os.environ.setdefault('SPRITE_FRONTEND_WARNINGS', '0')  # the rules overlap by design
import curry

root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.')
os.chdir(root)
curry.path.insert(0, root)
from curry.lib import Makefile

def rules(target):
  '''The prerequisites and the recipe of every rule of a target: the answers
  of rule target prereqs with prereqs free.'''
  prereqs = curry.free('prereqs')
  return [(bindings['prereqs'], recipe)
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

def command(target):
  '''The recipe of a target as a command: $(NAME) is a variable of the
  makefile, $@ the target, $< the first prerequisite and $^ everything the
  target reads.'''
  [(prereqs, recipe)] = rules(target)
  for name in re.findall(r'\$\((\w+)\)', recipe):
    recipe = recipe.replace('$(%s)' % name, next(curry.eval(getattr(Makefile, name))))
  return (recipe.replace('$@', target).replace('$<', prereqs[0])
                .replace('$^', ' '.join(needs(target))))

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
  the pending targets that read no pending target, and its recipes run at
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
  make(sys.argv[2] if len(sys.argv) > 2 else next(curry.eval(Makefile.goal)))
