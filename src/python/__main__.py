PROGRAM_NAME = 'sprite-exec'

from . import exceptions
from .tools.utility import handle_program_errors
import argparse, code, cProfile, os, pstats, importlib, logging, sys, time

curry = importlib.import_module(__package__)
logger = logging.getLogger(__name__)

class Main(object):
  DESCRIPTION = \
  '''
  Run or inspect a Curry program.  If no module is supplied, an
  interactive prompt is started in module %r.  Otherwise, the supplied
  Curry file or module is loaded, and the specified goal (if any) is
  evaluated.  Set CURRYPATH to control the search for Curry code.
  ''' % __package__
  ARGUMENTS = 'bimgpsntS'
  def __init__(
      self, program_name, module_name=None, default_goal='main', goalscheme=None
    ):
    self.program_name = program_name
    self.module_name = module_name
    self.default_goal = default_goal
    # The FlatCurry type of the default goal, as text, from the footer of a
    # saved module (curry.save).  With it the goal needs no interface file
    # at run time; see curry.typecheck.goals.
    self.goalscheme = goalscheme
    self.parser = self.buildParser()

  def description(self):
    return self.DESCRIPTION.format(self.module_name)

  def buildParser(self):
    parser = argparse.ArgumentParser(
        prog=self.program_name
      , description=self.description()
      )
    if 'b' in self.ARGUMENTS:
      parser.add_argument( '-b', '--backend', choices=['py', 'cxx'], default=None
        , help='selects the backend; overrides SPRITE_INTERPRETER_FLAGS '
               '[default: %s]' % curry.flags['backend'])
    if 'i' in self.ARGUMENTS:
      parser.add_argument( '-i', '--interact', action='store_true'
        , help='interact after running the program')
    if 'm' in self.ARGUMENTS:
      parser.add_argument( '-m', '--module', action='store_true'
        , help='interpret the NAME argument as a module name rather than a file name')
    if 'g' in self.ARGUMENTS:
      parser.add_argument( '-g', '--goal', type=str, default=self.default_goal
        , help='specifies the goal to evaluate; supply %r to run nothing '
               '[default: %s]' % ('', self.default_goal))
    if 'p' in self.ARGUMENTS:
      parser.add_argument( '-p', '--profile', action='store_true'
        , help='profile the program with cProfile')
    if 't' in self.ARGUMENTS:
      parser.add_argument( '-t', '--time', action='store_true'
        , help='suppress normal program output; print execution time instead')
    if 'S' in self.ARGUMENTS:
      parser.add_argument( '--stats', action='store_true'
        , help='at exit, print one line of statistics on stderr: wall and '
               'CPU seconds, rewrite steps, forks, collections, peak RSS in '
               'bytes, the seconds spent compiling and collecting, the '
               'functions swapped and compiles failed by tiered execution, '
               'and the counters of the collector (the gc_ fields; see the '
               'documentation)')
    if 's' in self.ARGUMENTS:
      try:
        sort_keys = sorted(pstats.Stats.sort_arg_dict_default.keys())
      except AttributeError:
        sort_keys = 'unknown'
      parser.add_argument('-s', '--psort', type=str, default='tottime'
          , help='sets the profile sort key [default: %r];\n'
                 'allowed values are %s' % ('tottime', sort_keys)
          )
    if 'n' in self.ARGUMENTS:
      parser.add_argument( 'NAME', nargs='?', default=None, type=str
        , help='a Curry file name (default) or module name to run')
    return parser

  def parseArgs(self, argv):
    args = self.parser.parse_args(argv)
    args.goal = args.goal or None
    return args

  def __call__(self, argv):
    args = self.parseArgs(argv)
    try:
      self.run(args)
    finally:
      if getattr(args, 'stats', False):
        # The last line of the program, after its output and after an error.
        # A closed standard output is legal; see cyrtbindings._flush_stdout.
        try:
          sys.stdout.flush()
        except (AttributeError, OSError, ValueError):
          pass
        sys.stderr.write('%s\n' % curry.stats())
        sys.stderr.flush()

  def run(self, args):
    if getattr(args, 'backend', None) is not None:
      # Reload before any Curry code is imported.  Flags passed to reload take
      # precedence over SPRITE_INTERPRETER_FLAGS; the other flags set there
      # are kept.
      curry.reload({'backend': args.backend})
    with handle_program_errors(self.program_name, exit_status=1):
      if args.NAME is None:
        code.interact(local={'__package__': curry})
        return
      else:
        module = curry.import_(
            args.NAME, curry.path, is_sourcefile=not args.module
          )
        if args.goal is not None:
          symbol = curry.symbol(module.__name__ + '.' + args.goal)
          goalscheme = self.goalscheme if args.goal == self.default_goal else None
          def goal():
            # The expression is built when the evaluation starts and is not
            # kept in a variable: a reference to the root of the goal keeps
            # the history of the search reachable while the evaluation runs;
            # see curry.typecheck.goals.Goal.evaluate.
            if goalscheme is None:
              return symbol
            return self.goal_from_scheme(symbol, goalscheme)
          def doeval():
            logger.info('Evaluating %s', symbol.fullname)
            try:
              if args.time:
                t0 = time.time()
                for value in curry.eval(goal()):
                  pass
                t1 = time.time()
                sys.stdout.write('%0.3f' % (t1 - t0))
              else:
                for value in curry.eval(goal()):
                  print(curry.show_value(value))
            except exceptions.EvaluationError as exc:
              sys.stderr.write('** %s **\n' % exc)
              sys.exit(1)
          if args.profile:
            profile = cProfile.Profile()
            profile.runctx('doeval()', globals(), locals())
            profile.print_stats(sort=args.psort)
          else:
            doeval()
    if args.interact:
      code.interact(banner='In Curry module %s.' % module.__name__, local=module.__dict__)

  @staticmethod
  def goal_from_scheme(symbol, goalscheme):
    '''
    The goal expression of a symbol whose scheme the footer of a saved
    module recorded: the symbol applied to the dictionaries of its defaulted
    constraints, or the symbol itself when it has none.
    '''
    from .typecheck import goals
    scheme = goals.scheme_from_flat_text(symbol, goalscheme)
    if not scheme.ndicts:
      return symbol
    return goals.defaulted_goal(curry.getInterpreter(), symbol, scheme)

def main(program_name, argv=None):
  '''Main program for Curry.'''
  argv = sys.argv[1:] if argv is None else argv
  mainobj = Main(program_name)
  mainobj(argv)

def moduleMain(filename, module_name, goal=None, goalscheme=None):
  '''
  Main program for a Curry module saved with ``curry.save``.  Runs the goal
  the module was saved with; ``goalscheme`` is its FlatCurry type as text,
  so that a goal with class constraints runs wherever the module lies.  The
  command line of the saved program is not read.
  '''
  if goal is not None:
    mainobj = Main(filename, module_name, default_goal=goal, goalscheme=goalscheme)
    mainobj(['-m', module_name, '-g', goal])

if __name__ == '__main__':
  main(PROGRAM_NAME)

