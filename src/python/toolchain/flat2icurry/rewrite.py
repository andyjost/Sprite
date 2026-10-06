'''
Command line: apply the binding optimization to FlatCurry files in place.

    python -m curry.toolchain.flat2icurry.rewrite [-q] [-s] M.fcy...

Each file is read, the pass of :mod:`bindingopt` runs over it, and the file
is written again in the format of the front end when the pass replaced an
equality; a file in which nothing is replaced is left as it is, with its
time.  One line per file reports the count, or ``unchanged``.  This is what
both routes from Curry to ICurry do to a FlatCurry file after the front end
wrote it; the command serves a file written before the routes did so, or a
file outside the toolchain.  The ICurry made from the file before is not
touched: ``sprite-make --rewrite-flat`` runs the step of a module again and
makes its products from the rewritten file.
'''

from .bindingopt import optimize_file
import argparse, sys

__all__ = ['main']

def main(argv=None):
  parser = argparse.ArgumentParser(
      prog='python -m curry.toolchain.flat2icurry.rewrite'
    , description='Apply the binding optimization of PAKCS to FlatCurry '
                  'files in place: a Boolean equality required to be True '
                  'becomes constrEq.  A file in which nothing is replaced is '
                  'left as it is.'
    )
  parser.add_argument('fcyfiles', nargs='+', metavar='M.fcy', help='a FlatCurry file')
  parser.add_argument(
      '-q', '--quiet', action='store_true', help='print nothing but errors'
    )
  parser.add_argument(
      '-s', '--strict', action='store_true'
    , help='replace === and /== only, not == and /= (the option -s of '
           'transbooleq)'
    )
  args = parser.parse_args(argv)
  for fcyfile in args.fcyfiles:
    n = optimize_file(fcyfile, equivalence=not args.strict)
    if not args.quiet:
      detail = 'unchanged' if n == 0 else '%d equalit%s replaced' % (
          n, 'y' if n == 1 else 'ies'
        )
      sys.stdout.write('%s: %s\n' % (fcyfile, detail))
  return 0

if __name__ == '__main__':
  sys.exit(main())
