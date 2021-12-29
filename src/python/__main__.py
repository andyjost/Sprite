PROGRAM_NAME = 'sprite-exec'

from . import exceptions
from .tools.utility import handle_program_errors
import argparse, code, cProfile, os, pstats, importlib, logging, sys

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
  ARGUMENTS = 'imgpsn'
  def __init__(self, program_name, module_name=None, default_goal='main'):
    self.program_name = program_name
    self.module_name = module_name
    self.default_goal = default_goal
    self.parser = self.buildParser()

  def description(self):
    return self.DESCRIPTION.format(self.module_name)

  def buildParser(self):
    parser = argparse.ArgumentParser(
        prog=self.program_name
      , description=self.description()
      )
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
    with handle_program_errors(self.program_name, exit_status=1):
      if args.NAME is None:
        code.interact(local={'__package__': curry})
        return
      else:
        module = curry.import_(
            args.NAME, curry.path, is_sourcefile=not args.module
          )
        if args.goal is not None:
          goal = curry.symbol(module.__name__ + '.' + args.goal)
          def doeval():
            logger.info('Evaluating %s', goal.fullname)
            try:
              for value in curry.eval(goal):
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

def main(program_name, argv=None):
  '''Main program for Curry.'''
  argv = sys.argv[1:] if argv is None else argv
  mainobj = Main(program_name)
  mainobj(argv)

def moduleMain(filename, module_name, goal=None):
  '''Main program for a Curry module.'''
  if goal is not None:
    mainobj = Main(filename, module_name, default_goal=goal)
    mainobj(['-m', module_name, '-g', goal])

if __name__ == '__main__':
  main(PROGRAM_NAME)

