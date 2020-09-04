from .exceptions import SymbolLookupError
import argparse
import code
import curry
import importlib
import sys

def main(argv):
  parser = argparse.ArgumentParser(
      prog='python -m ' + __package__
    , description=
        'Runs a Curry program under Sprite.  Set CURRYPATH to control the '
        'search for Curry code.'
    )
  parser.add_argument( '-i', '--interact', action='store_true', help='interact after running the program')
  parser.add_argument( 'curryfile', type=str, help='the Curry program to run')
  args = parser.parse_args(argv[1:])

  if args.curryfile.endswith('.curry'):
    args.curryfile = args.curryfile[:-6]
  module = importlib.import_module('curry.lib.%s' % args.curryfile)
  main = curry.symbol('%s.main' % args.curryfile)
  for value in curry.eval(main):
    print value

  if args.interact:
    code.interact(banner='In Curry module %s.' % args.curryfile, local=module.__dict__)


if __name__ == '__main__':
  main(sys.argv)
