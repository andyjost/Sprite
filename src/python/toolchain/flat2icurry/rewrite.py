'''
Command line: apply the rewrite step of the routes to FlatCurry files in
place.

    python -m curry.toolchain.flat2icurry.rewrite [-q] [-s] M.fcy...

Each file is read, the two passes of the step run over it in order, the
binding optimization of :mod:`bindingopt` (a Boolean equality required to
be True becomes ``constrEq``) and the set0 lift of :mod:`setlift`
(``set0 e`` over the captured variables of ``e`` becomes ``setk L xs``),
and the file is written again in the format of the front end when a pass
changed the program (:func:`curry.toolchain.flat2icurry.rewrite_file`); a
file in which nothing changes is left as it is, with its time.  One line
per file reports the counts, or ``unchanged``.  This is what both routes
from Curry to ICurry do to a FlatCurry file after the front end wrote it;
the command serves a file written before the routes did so, or a file
outside the toolchain.  The ICurry made from the file before is not
touched: ``sprite-make --rewrite-flat`` runs the step of a module again
and makes its products from the rewritten file.
'''

from . import rewrite_file
import argparse, sys

__all__ = ['describe', 'main']

def describe(counts):
  '''The text of a pair of counts of the step, for the report of a file.'''
  n, m = counts
  if not (n or m):
    return 'unchanged'
  parts = []
  if n:
    parts.append('%d equalit%s replaced' % (n, 'y' if n == 1 else 'ies'))
  if m:
    parts.append('%d set0 call%s lifted' % (m, '' if m == 1 else 's'))
  return ', '.join(parts)

def main(argv=None):
  parser = argparse.ArgumentParser(
      prog='python -m curry.toolchain.flat2icurry.rewrite'
    , description='Apply the rewrite step of the routes from Curry to ICurry '
                  'to FlatCurry files in place: the binding optimization of '
                  'PAKCS (a Boolean equality required to be True becomes '
                  'constrEq) and the set0 lift (set0 e over the captured '
                  'variables of e becomes setk L xs).  A file in which '
                  'nothing changes is left as it is.'
    )
  parser.add_argument('fcyfiles', nargs='+', metavar='M.fcy', help='a FlatCurry file')
  parser.add_argument(
      '-q', '--quiet', action='store_true', help='print nothing but errors'
    )
  parser.add_argument(
      '-s', '--strict', action='store_true'
    , help='replace === and /== only, not == and /= (the option -s of '
           'transbooleq); the lift is not affected'
    )
  args = parser.parse_args(argv)
  for fcyfile in args.fcyfiles:
    counts = rewrite_file(fcyfile, equivalence=not args.strict)
    if not args.quiet:
      sys.stdout.write('%s: %s\n' % (fcyfile, describe(counts)))
  return 0

if __name__ == '__main__':
  sys.exit(main())
