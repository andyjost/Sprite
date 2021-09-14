PROGRAM_NAME = 'sprite-exec'

from .exceptions import SymbolLookupError
from .tools.utility import handle_program_errors
from .utility import isLegalModulename
import argparse
import code
import importlib
import sys
curry = importlib.import_module(__package__)

def main(program_name, argv):
  parser = argparse.ArgumentParser(
      prog=program_name
    , description=
        'Runs a Curry program under Sprite.  Set CURRYPATH to control the '
        'search for Curry code.'
    )
  parser.add_argument( '-i', '--interact', action='store_true', help='interact after running the program')
  parser.add_argument( '-m', '--module', action='store_true'
    , help='interpret the argument as a module name rather than a file name')
  parser.add_argument( '-g', '--goal', type=str, default='main'
    , help='specifies the goal to evaluate [default: "main"]')
  parser.add_argument( 'name', nargs='?', default=None, type=str, help='a Curry file name (default) or module name to run')

  with handle_program_errors(PROGRAM_NAME, exit_status=1):
    args = parser.parse_args(argv)

    if args.name is None:
      code.interact(local={'__package__': curry})
      return

    module = curry.import_(args.name, curry.path, is_sourcefile=not args.module)
    goal = curry.symbol(module.__name__ + '.' + args.goal)
    for value in curry.eval(goal):
      print curry.show_value(value)

  if args.interact:
    code.interact(banner='In Curry module %s.' % module.__name__, local=module.__dict__)


if __name__ == '__main__':
  main(PROGRAM_NAME, sys.argv[1:])
